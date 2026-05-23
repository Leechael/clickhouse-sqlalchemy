from datetime import date, datetime
from unittest import TestCase
from uuid import UUID

from sqlalchemy import Column, MetaData, bindparam, exc, text
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.types import TypeDecorator

from clickhouse_sqlalchemy import Table, engines, types as ch_types
from clickhouse_sqlalchemy.drivers.asynch.base import ClickHouseDialect_asynch
from clickhouse_sqlalchemy.drivers.asynch.connector import (
    _strip_pyformat_values_template,
)


class WrappedString(TypeDecorator):
    impl = ch_types.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return "wrapped:%s" % value


class AsynchConnectorParamTestCase(TestCase):
    def _postcompile(self, statement, params):
        compiled = statement.compile(dialect=ClickHouseDialect_asynch())
        compiled_params = compiled.construct_params(
            params, escape_names=False
        )
        return compiled._process_parameters_for_postcompile(compiled_params)

    def test_asynch_compiler_renders_execute_literals_with_sqlalchemy(self):
        state = self._postcompile(
            text(
                'SELECT * FROM events WHERE name = :name AND ts = :ts '
                'AND day = :day AND id = :id'
            ),
            {
                'name': "O'Brien",
                'ts': datetime(2026, 1, 2, 3, 4, 5, 678),
                'day': date(2026, 1, 2),
                'id': UUID(int=1),
            }
        )

        self.assertEqual(
            state.statement,
            "SELECT * FROM events WHERE name = 'O''Brien' "
            "AND ts = '2026-01-02 03:04:05.000678' "
            "AND day = '2026-01-02' "
            "AND id = '00000000-0000-0000-0000-000000000001'"
        )
        self.assertEqual(state.parameters, {})

    def test_asynch_compiler_renders_null_literals(self):
        state = self._postcompile(
            text('SELECT :value'),
            {'value': None}
        )

        self.assertEqual(state.statement, 'SELECT NULL')
        self.assertEqual(state.parameters, {})

    def test_asynch_compiler_renders_string_subclass_literals(self):
        state = self._postcompile(
            text('SELECT :database'),
            {'database': quoted_name('system', quote=True)}
        )

        self.assertEqual(state.statement, "SELECT 'system'")
        self.assertEqual(state.parameters, {})

    def test_asynch_compiler_renders_nested_container_literals(self):
        state = self._postcompile(
            text('SELECT :empty_array, :empty_tuple, :payload'),
            {
                'empty_array': [],
                'empty_tuple': (),
                'payload': [
                    ["O'Brien", None],
                    (UUID(int=1), 7),
                    [date(2026, 1, 2), datetime(2026, 1, 2, 3, 4, 5)],
                ],
            }
        )

        self.assertEqual(
            state.statement,
            "SELECT [], (), "
            "[['O''Brien', NULL], "
            "('00000000-0000-0000-0000-000000000001', 7), "
            "['2026-01-02', '2026-01-02 03:04:05']]"
        )
        self.assertEqual(state.parameters, {})

    def test_asynch_compiler_uses_type_decorator_processors(self):
        state = self._postcompile(
            text('SELECT :payload').bindparams(
                bindparam('payload', type_=WrappedString())
            ),
            {'payload': "O'Brien"}
        )

        self.assertEqual(state.statement, "SELECT 'wrapped:O''Brien'")
        self.assertEqual(state.parameters, {})

    def test_asynch_compiler_rejects_unknown_literal_types(self):
        class UnsafeValue(object):
            def __str__(self):
                return "1); DROP TABLE events; --"

        with self.assertRaises(exc.CompileError):
            self._postcompile(
                text('SELECT :value'),
                {'value': UnsafeValue()}
            )

    def test_asynch_compiler_keeps_insert_binds_for_executemany(self):
        table = Table(
            'events', MetaData(),
            Column('id', ch_types.UInt32),
            engines.Memory()
        )
        compiled = table.insert().values(
            id=bindparam('id')
        ).compile(dialect=ClickHouseDialect_asynch())

        self.assertEqual(
            compiled.string,
            'INSERT INTO events (id) VALUES (%(id)s)'
        )
        self.assertEqual(compiled.literal_execute_params, frozenset())

    def test_asynch_compiler_keeps_textual_insert_binds_for_executemany(self):
        compiled = text(
            'INSERT INTO events (id, payload) VALUES (:id, :payload)'
        ).compile(dialect=ClickHouseDialect_asynch())

        self.assertEqual(
            compiled.string,
            'INSERT INTO events (id, payload) VALUES (%(id)s, %(payload)s)'
        )
        self.assertEqual(compiled.literal_execute_params, frozenset())

    def test_strip_pyformat_values_template_for_executemany(self):
        rows = [{'id': 1, 'payload': ['a']}]

        statement, params = _strip_pyformat_values_template(
            'INSERT INTO events (id, payload) '
            'VALUES (%(id)s, %(payload)s)',
            rows
        )

        self.assertEqual(statement, 'INSERT INTO events (id, payload) VALUES')
        self.assertIs(params, rows)
