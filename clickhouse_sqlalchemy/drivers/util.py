
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
    argument = argument.strip()

    for i, ch, bracket_level, quote in _scan_type_expression(argument):
        if ch.isspace() and bracket_level == 0 and quote is None:
            arg_name = argument[:i].strip().strip('`"')
            type_spec = argument[i + 1:].strip()
            if arg_name and type_spec:
                return arg_name, type_spec
            break

    return None, argument
