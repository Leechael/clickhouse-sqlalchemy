from unittest import TestCase

from clickhouse_sqlalchemy.drivers.util import (
    get_inner_spec, parse_arguments, parse_named_type_argument
)


class GetInnerSpecTestCase(TestCase):
    def test_get_inner_spec(self):
        self.assertEqual(
            get_inner_spec("DateTime('Europe/Paris')"), "'Europe/Paris'"
        )
        self.assertEqual(get_inner_spec('Decimal(18, 2)'), "18, 2")
        self.assertEqual(get_inner_spec('DateTime64(3)'), "3")


class ParseArgumentsTestCase(TestCase):
    def test_parse_arguments(self):
        self.assertEqual(
            parse_arguments('uniq, UInt64'), ('uniq', 'UInt64')
        )
        self.assertEqual(
            parse_arguments('anyIf, String, UInt8'),
            ('anyIf', 'String', 'UInt8')
        )
        self.assertEqual(
            parse_arguments('quantiles(0.5, 0.9), UInt64'),
            ('quantiles(0.5, 0.9)', 'UInt64')
        )
        self.assertEqual(
            parse_arguments('sum, Int64, Int64'), ('sum', 'Int64', 'Int64')
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
        self.assertEqual(
            parse_arguments('quantiles(0.5, 0.9), UInt64'),
            ('quantiles(0.5, 0.9)', 'UInt64')
        )
        self.assertEqual(
            parse_arguments("sumIf(total, status = 'accepted'), Float32"),
            ("sumIf(total, status = 'accepted')", "Float32")
        )
        self.assertEqual(
            parse_arguments(
                "Enum8('hello, world' = 1, 'plain' = 2), String"
            ),
            ("Enum8('hello, world' = 1, 'plain' = 2)", "String")
        )
        self.assertEqual(
            parse_arguments(
                "Enum8('O''Brien, Jr.' = 1, 'plain' = 2), String"
            ),
            ("Enum8('O''Brien, Jr.' = 1, 'plain' = 2)", "String")
        )
        self.assertEqual(
            parse_arguments(
                "DateTime64(3, 'America/New_York'), Nullable(String)"
            ),
            ("DateTime64(3, 'America/New_York')", "Nullable(String)")
        )
        self.assertEqual(
            parse_arguments("Tuple(`full name` String, value Float32)"),
            ("Tuple(`full name` String, value Float32)",)
        )


class ParseNamedTypeArgumentTestCase(TestCase):
    def test_parse_named_type_argument(self):
        self.assertEqual(
            parse_named_type_argument('name String'),
            ('name', 'String')
        )
        self.assertEqual(
            parse_named_type_argument('value Map(String, Nullable(String))'),
            ('value', 'Map(String, Nullable(String))')
        )
        self.assertEqual(
            parse_named_type_argument('Tuple(String, UInt32)'),
            (None, 'Tuple(String, UInt32)')
        )
        self.assertEqual(
            parse_named_type_argument('`full name` String'),
            ('full name', 'String')
        )
