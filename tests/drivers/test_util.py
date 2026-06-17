from unittest import TestCase

from clickhouse_sqlalchemy.drivers.util import (
    _scan_type_expression,
    get_inner_spec, parse_arguments, parse_named_type_argument,
    parse_string_literal
)


class ScanTypeExpressionTestCase(TestCase):

    def _quotes(self, value):
        return [q for _, _, _, q in _scan_type_expression(value)]

    def _depths(self, value):
        return [d for _, _, d, _ in _scan_type_expression(value)]

    def test_empty(self):
        self.assertEqual(list(_scan_type_expression('')), [])

    def test_bracket_depth_tracking(self):
        self.assertEqual(self._depths('A(B(C))'), [0, 1, 1, 2, 2, 1, 0])

    def test_unbalanced_close_paren(self):
        self.assertEqual(self._depths(')x('), [-1, -1, 0])

    def test_single_quote_boundaries(self):
        self.assertEqual(self._quotes("'ab'"), ["'", "'", "'", None])

    def test_double_quote_boundaries(self):
        self.assertEqual(self._quotes('"ab"'), ['"', '"', '"', None])

    def test_backslash_escape_keeps_quote_open(self):
        self.assertEqual(
            self._quotes("'a\\'b'"),
            ["'", "'", "'", "'", "'", None]
        )

    def test_doubled_quote_keeps_quote_open(self):
        self.assertEqual(
            self._quotes("'a''b'"),
            ["'", "'", "'", "'", "'", None]
        )

    def test_backtick_ignores_doubled_escape(self):
        # `a``b` is two backtick-quoted segments, not one with an escape.
        self.assertEqual(
            self._quotes('`a``b`'),
            ['`', '`', None, '`', '`', None]
        )

    def test_unclosed_quote(self):
        self.assertTrue(all(q == "'" for q in self._quotes("'hello")))

    def test_parens_inside_quotes_ignored(self):
        self.assertEqual(self._depths("'()'"), [0, 0, 0, 0])

    def test_quotes_inside_parens(self):
        self.assertEqual(self._depths("('a b')"), [1, 1, 1, 1, 1, 1, 0])


class GetInnerSpecTestCase(TestCase):
    def test_basic(self):
        self.assertEqual(
            get_inner_spec("DateTime('Europe/Paris')"), "'Europe/Paris'"
        )
        self.assertEqual(get_inner_spec('Decimal(18, 2)'), '18, 2')
        self.assertEqual(get_inner_spec('DateTime64(3)'), '3')

    def test_no_parens(self):
        self.assertEqual(get_inner_spec('String'), '')

    def test_empty_parens(self):
        self.assertEqual(get_inner_spec('Tuple()'), '')

    def test_nested_parens(self):
        self.assertEqual(
            get_inner_spec('Map(String, Nullable(UInt32))'),
            'String, Nullable(UInt32)'
        )

    def test_deep_nesting(self):
        self.assertEqual(
            get_inner_spec('Array(Tuple(String, Map(K, V)))'),
            'Tuple(String, Map(K, V))'
        )

    def test_parens_inside_string_literal(self):
        self.assertEqual(
            get_inner_spec("Enum8('val()' = 1)"),
            "'val()' = 1"
        )

    def test_unclosed_paren(self):
        self.assertEqual(get_inner_spec('Tuple(String'), 'String')


class ParseArgumentsTestCase(TestCase):
    def test_basic(self):
        self.assertEqual(
            parse_arguments('uniq, UInt64'), ('uniq', 'UInt64')
        )
        self.assertEqual(
            parse_arguments('anyIf, String, UInt8'),
            ('anyIf', 'String', 'UInt8')
        )
        self.assertEqual(
            parse_arguments('sum, Int64, Int64'),
            ('sum', 'Int64', 'Int64')
        )

    def test_nested_parens(self):
        self.assertEqual(
            parse_arguments('quantiles(0.5, 0.9), UInt64'),
            ('quantiles(0.5, 0.9)', 'UInt64')
        )
        self.assertEqual(
            parse_arguments('sum, Nullable(Int64), Int64'),
            ('sum', 'Nullable(Int64)', 'Int64')
        )
        self.assertEqual(
            parse_arguments('Float32, Decimal(18, 2)'),
            ('Float32', 'Decimal(18, 2)')
        )
        self.assertEqual(
            parse_arguments('sum, Float32, Decimal(18, 2)'),
            ('sum', 'Float32', 'Decimal(18, 2)')
        )

    def test_string_literals_with_commas(self):
        self.assertEqual(
            parse_arguments("sumIf(total, status = 'accepted'), Float32"),
            ("sumIf(total, status = 'accepted')", 'Float32')
        )
        self.assertEqual(
            parse_arguments(
                "Enum8('hello, world' = 1, 'plain' = 2), String"
            ),
            ("Enum8('hello, world' = 1, 'plain' = 2)", 'String')
        )
        self.assertEqual(
            parse_arguments(
                "Enum8('O''Brien, Jr.' = 1, 'plain' = 2), String"
            ),
            ("Enum8('O''Brien, Jr.' = 1, 'plain' = 2)", 'String')
        )

    def test_mixed_nesting_and_literals(self):
        self.assertEqual(
            parse_arguments(
                "DateTime64(3, 'America/New_York'), Nullable(String)"
            ),
            ("DateTime64(3, 'America/New_York')", 'Nullable(String)')
        )

    def test_backtick_identifiers(self):
        self.assertEqual(
            parse_arguments('Tuple(`full name` String, value Float32)'),
            ('Tuple(`full name` String, value Float32)',)
        )

    def test_empty(self):
        self.assertEqual(parse_arguments(''), ())

    def test_single_argument(self):
        self.assertEqual(parse_arguments('String'), ('String',))

    def test_trailing_comma(self):
        self.assertEqual(parse_arguments('a, b,'), ('a', 'b'))

    def test_consecutive_commas(self):
        self.assertEqual(parse_arguments('a,,b'), ('a', '', 'b'))


class ParseNamedTypeArgumentTestCase(TestCase):

    # --- basic named ---

    def test_simple_name(self):
        self.assertEqual(
            parse_named_type_argument('name String'),
            ('name', 'String')
        )

    def test_nested_type(self):
        self.assertEqual(
            parse_named_type_argument('value Map(String, Nullable(String))'),
            ('value', 'Map(String, Nullable(String))')
        )

    def test_backtick_name(self):
        self.assertEqual(
            parse_named_type_argument('`full name` String'),
            ('full name', 'String')
        )

    def test_double_quoted_name(self):
        self.assertEqual(
            parse_named_type_argument('"name" String'),
            ('name', 'String')
        )

    def test_double_quoted_name_with_spaces(self):
        self.assertEqual(
            parse_named_type_argument('"full name" String'),
            ('full name', 'String')
        )

    def test_name_with_special_chars(self):
        self.assertEqual(
            parse_named_type_argument('`name-with-dashes` UInt32'),
            ('name-with-dashes', 'UInt32')
        )

    # --- complex types ---

    def test_deep_nested_type(self):
        self.assertEqual(
            parse_named_type_argument(
                'x Array(Tuple(String, Map(String, UInt32)))'
            ),
            ('x', 'Array(Tuple(String, Map(String, UInt32)))')
        )

    def test_enum_with_space_in_literal(self):
        self.assertEqual(
            parse_named_type_argument(
                "status Enum8('hello world' = 1, 'plain' = 2)"
            ),
            ('status', "Enum8('hello world' = 1, 'plain' = 2)")
        )

    def test_enum_with_comma_in_literal(self):
        self.assertEqual(
            parse_named_type_argument("x Enum8('a,b' = 1)"),
            ('x', "Enum8('a,b' = 1)")
        )

    def test_type_containing_named_fields(self):
        self.assertEqual(
            parse_named_type_argument('x Tuple(a String, b UInt32)'),
            ('x', 'Tuple(a String, b UInt32)')
        )

    # --- unnamed (no split) ---

    def test_unnamed_tuple(self):
        self.assertEqual(
            parse_named_type_argument('Tuple(String, UInt32)'),
            (None, 'Tuple(String, UInt32)')
        )

    def test_unnamed_nullable(self):
        self.assertEqual(
            parse_named_type_argument('Nullable(String)'),
            (None, 'Nullable(String)')
        )

    def test_unnamed_enum_with_spaces(self):
        self.assertEqual(
            parse_named_type_argument("Enum8('hello world' = 1)"),
            (None, "Enum8('hello world' = 1)")
        )

    def test_unnamed_simple_type(self):
        self.assertEqual(
            parse_named_type_argument('String'),
            (None, 'String')
        )

    # --- whitespace variations ---

    def test_multiple_spaces(self):
        self.assertEqual(
            parse_named_type_argument('name   String'),
            ('name', 'String')
        )

    def test_tab_separator(self):
        self.assertEqual(
            parse_named_type_argument('name\tString'),
            ('name', 'String')
        )

    def test_leading_trailing_whitespace(self):
        self.assertEqual(
            parse_named_type_argument('  name String  '),
            ('name', 'String')
        )

    # --- edge cases ---

    def test_empty_string(self):
        self.assertEqual(parse_named_type_argument(''), (None, ''))

    def test_whitespace_only(self):
        self.assertEqual(parse_named_type_argument('   '), (None, ''))

    def test_name_only_no_type(self):
        self.assertEqual(parse_named_type_argument('name'), (None, 'name'))

    def test_empty_backtick_name(self):
        self.assertEqual(
            parse_named_type_argument('`` String'),
            (None, '`` String')
        )


class ParseStringLiteralTestCase(TestCase):

    # --- unquoted passthrough ---

    def test_unquoted_number(self):
        self.assertEqual(parse_string_literal('0'), '0')

    def test_unquoted_word(self):
        self.assertEqual(parse_string_literal('hello'), 'hello')

    def test_backtick_passes_through(self):
        self.assertEqual(parse_string_literal('`tz`'), '`tz`')

    def test_mismatched_quotes(self):
        self.assertEqual(parse_string_literal("'foo\""), "'foo\"")

    # --- basic quoting ---

    def test_single_quoted(self):
        self.assertEqual(parse_string_literal("'0'"), '0')

    def test_double_quoted(self):
        self.assertEqual(parse_string_literal('"0"'), '0')

    def test_single_quoted_word(self):
        self.assertEqual(parse_string_literal("'hello'"), 'hello')

    # --- empty and minimal ---

    def test_empty_python_string(self):
        self.assertEqual(parse_string_literal(''), '')

    def test_single_char(self):
        self.assertEqual(parse_string_literal("'"), "'")

    def test_empty_single_quoted(self):
        self.assertEqual(parse_string_literal("''"), '')

    def test_empty_double_quoted(self):
        self.assertEqual(parse_string_literal('""'), '')

    # --- whitespace ---

    def test_surrounding_whitespace(self):
        self.assertEqual(parse_string_literal("  '0'  "), '0')

    def test_internal_whitespace_preserved(self):
        self.assertEqual(parse_string_literal("'  hello  '"), '  hello  ')

    # --- backslash escapes ---

    def test_backslash_quote(self):
        self.assertEqual(parse_string_literal(r"'O\\'Brien'"), r"O\'Brien")

    def test_escaped_backslash(self):
        self.assertEqual(parse_string_literal("'\\\\'"), '\\')

    def test_backslash_normal_char(self):
        self.assertEqual(parse_string_literal("'\\n'"), 'n')

    def test_trailing_backslash(self):
        self.assertEqual(parse_string_literal("'abc\\'"), 'abc\\')

    # --- doubled-quote escapes ---

    def test_doubled_single_quote(self):
        self.assertEqual(parse_string_literal("'O''Brien'"), "O'Brien")

    def test_doubled_double_quote(self):
        self.assertEqual(
            parse_string_literal('"a ""quoted"" value"'),
            'a "quoted" value'
        )

    # --- mixed escapes ---

    def test_backslash_and_doubled_in_same_string(self):
        self.assertEqual(
            parse_string_literal("'O\\'Brien''s'"),
            "O'Brien's"
        )

    # --- cross-quote content ---

    def test_double_quote_inside_single(self):
        self.assertEqual(
            parse_string_literal("'\"hello\"'"),
            '"hello"'
        )

    def test_single_quote_inside_double(self):
        self.assertEqual(
            parse_string_literal("\"it's\""),
            "it's"
        )


class ParsingPipelineTestCase(TestCase):

    def test_nested_with_named_enum_fields(self):
        spec = (
            "Nested(status Enum8('active' = 1, 'deleted' = 2),"
            " count UInt32)"
        )
        inner = get_inner_spec(spec)
        args = parse_arguments(inner)
        self.assertEqual(len(args), 2)

        name0, type0 = parse_named_type_argument(args[0])
        self.assertEqual(name0, 'status')
        self.assertEqual(type0, "Enum8('active' = 1, 'deleted' = 2)")

        name1, type1 = parse_named_type_argument(args[1])
        self.assertEqual(name1, 'count')
        self.assertEqual(type1, 'UInt32')

    def test_named_tuple_with_subtuple(self):
        spec = 'Tuple(x Tuple(a String, b UInt32), y Float64)'
        inner = get_inner_spec(spec)
        args = parse_arguments(inner)
        self.assertEqual(len(args), 2)

        name0, type0 = parse_named_type_argument(args[0])
        self.assertEqual(name0, 'x')
        self.assertEqual(type0, 'Tuple(a String, b UInt32)')

        name1, type1 = parse_named_type_argument(args[1])
        self.assertEqual(name1, 'y')
        self.assertEqual(type1, 'Float64')

    def test_datetime64_timezone_extraction(self):
        spec = "DateTime64(3, 'America/New_York')"
        inner = get_inner_spec(spec)
        args = parse_arguments(inner)
        self.assertEqual(args, ('3', "'America/New_York'"))
        self.assertEqual(parse_string_literal(args[1]), 'America/New_York')

    def test_enum_option_parsing(self):
        inner = get_inner_spec("Enum8('O''Brien' = 1, 'plain' = 2)")
        options = parse_arguments(inner)

        name0, _ = options[0].split('=', 1)
        self.assertEqual(parse_string_literal(name0), "O'Brien")

        name1, _ = options[1].split('=', 1)
        self.assertEqual(parse_string_literal(name1), 'plain')
