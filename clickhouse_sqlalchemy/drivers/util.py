
def _scan_type_expression(value):
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
    brackets = 0
    quote = None
    escaped = False
    offset = spec.find('(')
    if offset == -1:
        return ''

    for i, ch in enumerate(spec[offset:], offset):
        if escaped:
            escaped = False
            continue

        if quote:
            if ch == '\\':
                escaped = True
            elif ch == quote:
                quote = None
            continue

        if ch in ("'", '"', '`'):
            quote = ch
        elif ch == '(':
            brackets += 1
        elif ch == ')':
            brackets -= 1

        if brackets == 0:
            return spec[offset + 1:i]

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
    argument = argument.strip()

    for i, ch, bracket_level, quote in _scan_type_expression(argument):
        if ch.isspace() and bracket_level == 0 and quote is None:
            arg_name = argument[:i].strip().strip('`"')
            type_spec = argument[i + 1:].strip()
            if arg_name and type_spec:
                return arg_name, type_spec
            break

    return None, argument
