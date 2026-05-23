from datetime import date, datetime
from enum import Enum
from unittest import TestCase
from uuid import UUID

from clickhouse_sqlalchemy.drivers.asynch.connector import (
    _escape_param, _strip_pyformat_values_template,
    _substitute_pyformat_params,
)


class AsynchConnectorParamTestCase(TestCase):
    def test_escape_param_formats_driver_literals(self):
        class Color(Enum):
            red = 'red'

        self.assertEqual(_escape_param(None), 'NULL')
        self.assertEqual(_escape_param(date(2026, 1, 2)), "'2026-01-02'")
        self.assertEqual(
            _escape_param(datetime(2026, 1, 2, 3, 4, 5, 678)),
            "'2026-01-02 03:04:05.000678'"
        )
        self.assertEqual(_escape_param(['a', 2]), "['a', 2]")
        self.assertEqual(_escape_param((Color.red, UUID(int=1))),
                         "('red', '00000000-0000-0000-0000-000000000001')")

    def test_escape_param_formats_nested_container_literals(self):
        class Color(Enum):
            red = 'red'

        self.assertEqual(_escape_param([]), '[]')
        self.assertEqual(_escape_param(()), '()')
        self.assertEqual(
            _escape_param([
                ["O'Brien", None],
                (Color.red, UUID(int=1)),
                [date(2026, 1, 2), datetime(2026, 1, 2, 3, 4, 5)],
            ]),
            "[['O\\'Brien', NULL], "
            "('red', '00000000-0000-0000-0000-000000000001'), "
            "['2026-01-02', '2026-01-02 03:04:05']]"
        )

    def test_escape_param_formats_flattened_nested_child_arrays(self):
        self.assertEqual(_escape_param(['alice', 'bob']),
                         "['alice', 'bob']")
        self.assertEqual(_escape_param([34, 29]), '[34, 29]')

    def test_escape_param_formats_unflattened_nested_tuple_array_literal(self):
        self.assertEqual(
            _escape_param([('alice', 34), ('bob', 29)]),
            "[('alice', 34), ('bob', 29)]"
        )

    def test_substitute_pyformat_params_rewrites_mapping(self):
        statement, params = _substitute_pyformat_params(
            'SELECT * FROM events WHERE name = %(name)s AND ts = %(ts)s',
            {'name': "O'Brien", 'ts': datetime(2026, 1, 2, 3, 4, 5)}
        )

        self.assertEqual(
            statement,
            "SELECT * FROM events WHERE name = 'O\\'Brien' "
            "AND ts = '2026-01-02 03:04:05'"
        )
        self.assertIsNone(params)

    def test_strip_pyformat_values_template_for_executemany(self):
        rows = [{'id': 1, 'payload': ['a']}]

        statement, params = _strip_pyformat_values_template(
            'INSERT INTO events (id, payload) '
            'VALUES (%(id)s, %(payload)s)',
            rows
        )

        self.assertEqual(statement, 'INSERT INTO events (id, payload) VALUES')
        self.assertIs(params, rows)
