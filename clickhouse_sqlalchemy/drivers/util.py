import re


_insert_prefix_re = re.compile(r'\A\s*INSERT\b', re.IGNORECASE)
_pyformat_placeholder_re = re.compile(r'%\([^)]+\)s')
_values_word_re = re.compile(r'\bVALUES\b', re.IGNORECASE)
_values_suffix_re = re.compile(r'\bVALUES\s*\Z', re.IGNORECASE)


def _mask_sql_literals_and_comments(statement):
    chars = list(statement)
    i = 0
    quote = None
    line_comment = False
    block_comment = False

    while i < len(chars):
        ch = chars[i]
        next_ch = chars[i + 1] if i + 1 < len(chars) else ''

        if line_comment:
            if ch == '\n':
                line_comment = False
            else:
                chars[i] = ' '
            i += 1
            continue

        if block_comment:
            chars[i] = ' '
            if ch == '*' and next_ch == '/':
                chars[i + 1] = ' '
                block_comment = False
                i += 2
            else:
                i += 1
            continue

        if quote:
            chars[i] = ' '
            if ch == '\\' and next_ch:
                chars[i + 1] = ' '
                i += 2
                continue
            if ch == quote:
                if quote in ("'", '"') and next_ch == quote:
                    chars[i + 1] = ' '
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if ch == '-' and next_ch == '-':
            chars[i] = chars[i + 1] = ' '
            line_comment = True
            i += 2
        elif ch == '/' and next_ch == '*':
            chars[i] = chars[i + 1] = ' '
            block_comment = True
            i += 2
        elif ch in ("'", '"', '`'):
            chars[i] = ' '
            quote = ch
            i += 1
        else:
            i += 1

    return ''.join(chars)


def get_pyformat_insert_values_template(statement):
    """Return the terminal pyformat INSERT values tuple, if present."""
    if not isinstance(statement, str):
        return None

    masked = _mask_sql_literals_and_comments(statement)
    if _insert_prefix_re.search(masked) is None:
        return None

    values_matches = tuple(_values_word_re.finditer(masked))
    if not values_matches:
        return None

    values_end = values_matches[-1].end()
    template_start = values_end
    while (
        template_start < len(masked)
        and masked[template_start].isspace()
    ):
        template_start += 1

    if template_start >= len(masked) or masked[template_start] != '(':
        return None

    depth = 0
    template_end = None
    for index in range(template_start, len(masked)):
        char = masked[index]
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                template_end = index + 1
                break

    if template_end is None:
        return None
    if masked[template_end:].strip():
        return None

    template = statement[template_start:template_end]
    if _pyformat_placeholder_re.search(template) is None:
        return None
    return template


def strip_pyformat_insert_values_template(statement, values_template=None):
    """Remove an exact terminal pyformat values tuple from an INSERT."""
    if not isinstance(statement, str):
        return statement

    if values_template is None:
        values_template = get_pyformat_insert_values_template(statement)
    if not values_template:
        return statement

    stripped_statement = statement.rstrip()
    if not stripped_statement.endswith(values_template):
        return statement

    template_start = len(stripped_statement) - len(values_template)
    template_end = len(stripped_statement)
    masked = _mask_sql_literals_and_comments(stripped_statement)
    if masked[template_start:template_end] != values_template:
        return statement

    prefix = stripped_statement[:-len(values_template)].rstrip()
    if _values_suffix_re.search(prefix) is None:
        return statement
    return prefix


def _scan_type_expression(value):
    """Yield every character of *value* with its bracket depth and quote state.

    Tracks how deeply nested we are inside ``(...)`` pairs and whether
    we are inside a quoted string literal, so callers can safely split
    on commas or match closing parentheses without getting confused by
    nested type definitions or string contents.
    """
    brackets = 0
    quote = None
    escaped = False

    for i, ch in enumerate(value):
        if escaped:
            escaped = False
            yield i, ch, brackets, quote
            continue

        if quote:
            if ch == '\\':
                escaped = True
            elif (
                ch == quote
                and quote in ("'", '"')
                and i + 1 < len(value)
                and value[i + 1] == quote
            ):
                escaped = True
            elif ch == quote:
                quote = None
            yield i, ch, brackets, quote
            continue

        if ch in ("'", '"', '`'):
            quote = ch
        elif ch == '(':
            brackets += 1
        elif ch == ')':
            brackets -= 1

        yield i, ch, brackets, quote


def get_inner_spec(spec):
    offset = spec.find('(')
    if offset == -1:
        return ''

    for i, ch, bracket_level, quote in _scan_type_expression(spec[offset:]):
        if ch == ')' and bracket_level == 0 and quote is None:
            return spec[offset + 1:offset + i]

    return spec[offset + 1:]


def parse_arguments(param_string):
    """
    Given a string of type/function arguments, parse them into a tuple.
    """
    params = []
    current_param = ''

    for _, char, bracket_level, quote in _scan_type_expression(param_string):
        if char == ',' and bracket_level == 0 and quote is None:
            params.append(current_param.strip())
            current_param = ''
            continue

        current_param += char

    if current_param:
        params.append(current_param.strip())

    return tuple(params)


def parse_named_type_argument(argument):
    """Split a ClickHouse named argument such as ```name` String``.

    Returns ``(name, type_spec)`` when the argument contains an
    unquoted space separating the identifier from the type;
    otherwise returns ``(None, argument)`` for unnamed arguments.
    """
    argument = argument.strip()

    for i, ch, bracket_level, quote in _scan_type_expression(argument):
        if ch.isspace() and bracket_level == 0 and quote is None:
            arg_name = argument[:i].strip().strip('`"')
            type_spec = argument[i + 1:].strip()
            if arg_name and type_spec:
                return arg_name, type_spec
            break

    return None, argument


def parse_string_literal(value):
    """Remove surrounding quotes from a SQL string literal and unescape it.

    If *value* is not quoted, returns it unchanged.
    """
    value = value.strip()
    if len(value) < 2 or value[0] != value[-1] or value[0] not in "'\"":
        return value

    result = []
    escaped = False
    inner = value[1:-1]
    quote = value[0]
    i = 0
    while i < len(inner):
        ch = inner[i]
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == '\\':
            escaped = True
        elif (
            ch == quote
            and quote in ("'", '"')
            and i + 1 < len(inner)
            and inner[i + 1] == quote
        ):
            result.append(ch)
            i += 1
        else:
            result.append(ch)
        i += 1

    if escaped:
        result.append('\\')
    return ''.join(result)
