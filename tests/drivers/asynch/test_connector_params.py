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

    def _context_with_values_template(self, values_template):
        class Compiled:
            _clickhouse_insert_values_template = values_template

        class Context:
            compiled = Compiled()

        return Context()

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
        context = self._context_with_values_template(
            '(%(id)s, %(payload)s)'
        )

        statement, params = _strip_pyformat_values_template(
            'INSERT INTO events (id, payload) '
            'VALUES (%(id)s, %(payload)s)',
            rows,
            context=context,
        )

        self.assertEqual(statement, 'INSERT INTO events (id, payload) VALUES')
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_requires_context(self):
        rows = [{'id': 1, 'payload': ['a']}]
        original = (
            'INSERT INTO events (id, payload) '
            'VALUES (%(id)s, %(payload)s)'
        )

        statement, params = _strip_pyformat_values_template(original, rows)

        self.assertEqual(statement, original)
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_handles_multiline_insert(self):
        rows = [{'id': 1, 'payload': ['a']}]
        context = self._context_with_values_template(
            '(\n'
            '    %(id)s,\n'
            '    %(payload)s\n'
            ')'
        )

        statement, params = _strip_pyformat_values_template(
            'INSERT INTO events (\n'
            '    id,\n'
            '    payload\n'
            ')\n'
            'VALUES (\n'
            '    %(id)s,\n'
            '    %(payload)s\n'
            ')',
            rows,
            context=context,
        )

        self.assertEqual(
            statement,
            'INSERT INTO events (\n'
            '    id,\n'
            '    payload\n'
            ')\n'
            'VALUES'
        )
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_ignores_trailing_comment(self):
        rows = [{'id': 1}]
        context = self._context_with_values_template('(%(id)s)')
        original = (
            'INSERT INTO events (id) VALUES (%(id)s) '
            '-- VALUES (%(id)s) appears after the insert template'
        )

        statement, params = _strip_pyformat_values_template(
            original, rows, context=context
        )

        self.assertEqual(statement, original)
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_ignores_trailing_string(self):
        rows = [{'id': 1}]
        context = self._context_with_values_template('(%(id)s)')
        original = (
            "INSERT INTO events (id) VALUES (%(id)s) "
            "SETTINGS note='VALUES appears after the insert template'"
        )

        statement, params = _strip_pyformat_values_template(
            original, rows, context=context
        )

        self.assertEqual(statement, original)
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_ignores_non_insert_statement(self):
        rows = [{'id': 1}]
        context = self._context_with_values_template('(%(id)s)')
        original = "SELECT (%(id)s)"

        statement, params = _strip_pyformat_values_template(
            original, rows, context=context
        )

        self.assertEqual(statement, original)
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_uses_compiled_template(self):
        table = Table(
            'events', MetaData(),
            Column('id', ch_types.UInt32),
            Column('payload', ch_types.String),
            engines.Memory()
        )
        compiled = table.insert().values(
            id=bindparam('id'), payload=bindparam('payload')
        ).compile(dialect=ClickHouseDialect_asynch())
        context = type('Context', (), {'compiled': compiled})()
        rows = [{'id': 1, 'payload': 'a'}]

        statement, params = _strip_pyformat_values_template(
            compiled.string, rows, context=context
        )

        self.assertEqual(statement, 'INSERT INTO events (id, payload) VALUES')
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_handles_bind_expression(self):
        table = Table(
            'events', MetaData(),
            Column('address', ch_types.IPv6),
            engines.Memory()
        )
        compiled = table.insert().compile(dialect=ClickHouseDialect_asynch())
        context = type('Context', (), {'compiled': compiled})()
        rows = [{'address': '2001:db8::1'}]

        statement, params = _strip_pyformat_values_template(
            compiled.string, rows, context=context
        )

        self.assertEqual(statement, 'INSERT INTO events (address) VALUES')
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_requires_compiled_match(self):
        table = Table(
            'events', MetaData(),
            Column('id', ch_types.UInt32),
            Column('payload', ch_types.String),
            engines.Memory()
        )
        compiled = table.insert().values(
            id=bindparam('id'), payload=bindparam('payload')
        ).compile(dialect=ClickHouseDialect_asynch())
        context = type('Context', (), {'compiled': compiled})()
        original = 'INSERT INTO events (id) VALUES (%(id)s)'
        rows = [{'id': 1}]

        statement, params = _strip_pyformat_values_template(
            original, rows, context=context
        )

        self.assertEqual(statement, original)
        self.assertIs(params, rows)

    def test_strip_pyformat_values_template_rejects_comment_match(self):
        table = Table(
            'events', MetaData(),
            Column('id', ch_types.UInt32),
            engines.Memory()
        )
        compiled = table.insert().values(
            id=bindparam('id')
        ).compile(dialect=ClickHouseDialect_asynch())
        context = type('Context', (), {'compiled': compiled})()
        original = (
            'INSERT INTO events (id) VALUES (%(id)s) '
            '-- VALUES (%(id)s)'
        )
        rows = [{'id': 1}]

        statement, params = _strip_pyformat_values_template(
            original, rows, context=context
        )

        self.assertEqual(statement, original)
        self.assertIs(params, rows)
