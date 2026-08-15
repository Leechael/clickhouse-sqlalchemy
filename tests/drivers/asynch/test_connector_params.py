import os
from datetime import date, datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import UUID

from asynch.proto.connection import Connection as ProtoConnection
from sqlalchemy import Column, MetaData, bindparam, exc, select, text, update
from sqlalchemy import delete, literal_column
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

    def test_textual_insert_with_line_comment_is_recognized(self):
        compiled = text(
            '-- note\nINSERT INTO events (id) VALUES (:id)'
        ).compile(dialect=ClickHouseDialect_asynch())
        self.assertEqual(compiled.literal_execute_params, frozenset())

    def test_textual_insert_with_block_comment_is_recognized(self):
        compiled = text(
            '/* block */\nINSERT INTO events (id) VALUES (:id)'
        ).compile(dialect=ClickHouseDialect_asynch())
        self.assertEqual(compiled.literal_execute_params, frozenset())

    def test_textual_insert_with_multiple_comments_is_recognized(self):
        compiled = text(
            '-- header\n/* inline */ INSERT INTO events (id) VALUES (:id)'
        ).compile(dialect=ClickHouseDialect_asynch())
        self.assertEqual(compiled.literal_execute_params, frozenset())

    def test_textual_select_with_comment_is_not_misidentified(self):
        compiled = text(
            '-- note\nSELECT :x'
        ).compile(dialect=ClickHouseDialect_asynch())
        # SELECT with comment should still take literal_execute path
        self.assertNotEqual(compiled.literal_execute_params, frozenset())

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

    def test_asynch_compiler_keeps_map_param_for_typed_statement(self):
        table = Table(
            'events', MetaData(),
            Column('m', ch_types.Map(ch_types.String, ch_types.String)),
            engines.Memory()
        )
        compiled = select(table).where(
            table.c.m == {'a': 'b'}
        ).compile(dialect=ClickHouseDialect_asynch())

        self.assertEqual(compiled.literal_execute_params, frozenset())
        self.assertIn('%(m_1)s', compiled.string)

        params = compiled.construct_params(
            {'m_1': {'a': 'b'}}, escape_names=False
        )
        state = compiled._process_parameters_for_postcompile(params)

        self.assertEqual(state.parameters, {'m_1': {'a': 'b'}})
        self.assertIn('%(m_1)s', state.statement)

    def test_asynch_compiler_keeps_json_param_for_typed_statement(self):
        table = Table(
            'events', MetaData(),
            Column('j', ch_types.JSON),
            engines.Memory()
        )
        compiled = select(table).where(
            table.c.j == {'a': 'b'}
        ).compile(dialect=ClickHouseDialect_asynch())

        self.assertEqual(compiled.literal_execute_params, frozenset())
        self.assertIn('%(j_1)s', compiled.string)

        params = compiled.construct_params(
            {'j_1': {'a': 'b'}}, escape_names=False
        )
        state = compiled._process_parameters_for_postcompile(params)

        self.assertEqual(state.parameters, {'j_1': {'a': 'b'}})
        self.assertIn('%(j_1)s', state.statement)

    def test_asynch_compiler_keeps_bytes_param_for_typed_statement(self):
        table = Table(
            'events', MetaData(),
            Column('b', ch_types.String),
            engines.Memory()
        )
        value = b'a\x00b'
        compiled = select(table).where(
            table.c.b == value
        ).compile(dialect=ClickHouseDialect_asynch())

        self.assertEqual(compiled.literal_execute_params, frozenset())
        self.assertIn('%(b_1)s', compiled.string)

        params = compiled.construct_params(
            {'b_1': value}, escape_names=False
        )
        state = compiled._process_parameters_for_postcompile(params)

        self.assertEqual(state.parameters, {'b_1': value})
        self.assertIn('%(b_1)s', state.statement)

    def test_asynch_compiler_keeps_params_for_select_update_delete(self):
        table = Table(
            'events', MetaData(),
            Column('x', ch_types.UInt32),
            Column('s', ch_types.String),
            engines.Memory()
        )
        statements = (
            select(table).where(table.c.x == 1),
            update(table).where(table.c.x == 1).values(s='a'),
            delete(table).where(table.c.x == 1),
        )

        for statement in statements:
            with self.subTest(statement=type(statement).__name__):
                compiled = statement.compile(
                    dialect=ClickHouseDialect_asynch()
                )

                self.assertEqual(compiled.literal_execute_params, frozenset())
                self.assertIn('%(x_1)s', compiled.string)


class AsynchDoExecutePyformatPreservationTestCase(TestCase):
    """do_execute must preserve SQLAlchemy's pyformat placeholders.

    The pinned asynch driver substitutes ordinary query parameters with
    pyformat by default. SQLAlchemy also compiles this dialect with
    pyformat placeholders, so do_execute must pass statements through
    unchanged and let the driver interpolate them.
    """

    def setUp(self):
        self.dialect = ClickHouseDialect_asynch()

    def _make_mock_cursor(self):
        cursor = MagicMock()
        return cursor

    def test_preserves_single_pyformat_placeholder(self):
        cursor = self._make_mock_cursor()
        statement = 'SELECT * FROM events WHERE x = %(x_1)s'
        params = {'x_1': 42}

        self.dialect.do_execute(cursor, statement, params)

        cursor.execute.assert_called_once()
        actual_statement = cursor.execute.call_args[0][0]
        self.assertEqual(actual_statement, statement)

    def test_preserves_multiple_pyformat_placeholders(self):
        cursor = self._make_mock_cursor()
        statement = (
            'SELECT * FROM events '
            'WHERE x = %(x_1)s AND s = %(s_1)s'
        )
        params = {'x_1': 42, 's_1': 'hello'}

        self.dialect.do_execute(cursor, statement, params)

        cursor.execute.assert_called_once()
        actual_statement = cursor.execute.call_args[0][0]
        self.assertEqual(actual_statement, statement)

    def test_passes_params_unchanged(self):
        cursor = self._make_mock_cursor()
        statement = 'SELECT * FROM events WHERE x = %(x_1)s'
        params = {'x_1': 42}

        self.dialect.do_execute(cursor, statement, params)

        actual_params = cursor.execute.call_args[0][1]
        self.assertEqual(actual_params, {'x_1': 42})

    def test_no_params_passes_statement_unchanged(self):
        cursor = self._make_mock_cursor()
        statement = 'SELECT 1'

        self.dialect.do_execute(cursor, statement, None)

        cursor.execute.assert_called_once()
        actual_statement = cursor.execute.call_args[0][0]
        self.assertEqual(actual_statement, statement)

    def test_empty_params_passes_statement_unchanged(self):
        cursor = self._make_mock_cursor()
        statement = 'SELECT 1'

        self.dialect.do_execute(cursor, statement, {})

        cursor.execute.assert_called_once()
        actual_statement = cursor.execute.call_args[0][0]
        self.assertEqual(actual_statement, statement)

    def test_preserves_update_pyformat_placeholders(self):
        cursor = self._make_mock_cursor()
        statement = 'ALTER TABLE events UPDATE s = %(s_1)s WHERE x = %(x_1)s'
        params = {'s_1': 'new', 'x_1': 42}

        self.dialect.do_execute(cursor, statement, params)

        cursor.execute.assert_called_once()
        actual_statement = cursor.execute.call_args[0][0]
        self.assertEqual(actual_statement, statement)

    def test_preserves_compiled_select_pyformat(self):
        table = Table(
            'events', MetaData(),
            Column('x', ch_types.UInt32),
            Column('s', ch_types.String),
            engines.Memory()
        )
        compiled = select(table).where(
            table.c.x == 42, table.c.s == 'hello'
        ).compile(dialect=self.dialect)

        cursor = self._make_mock_cursor()
        params = compiled.construct_params(
            {'x_1': 42, 's_1': 'hello'}, escape_names=False
        )
        state = compiled._process_parameters_for_postcompile(params)

        self.dialect.do_execute(cursor, state.statement, state.parameters)

        cursor.execute.assert_called_once()
        actual_statement = cursor.execute.call_args[0][0]
        self.assertIn('%(x_1)s', actual_statement)
        self.assertIn('%(s_1)s', actual_statement)


class AsynchSubstitutionFidelityTestCase(TestCase):
    """Statements sent to the asynch cursor must survive the driver's
    substitution step.

    asynch applies pyformat substitution to every ordinary (non-INSERT)
    query whenever ``args`` is not None — including an empty dict.  The
    statement that ``do_execute`` hands to the cursor therefore must keep
    SQLAlchemy's pyformat placeholders, literal braces, and doubled ``%%``
    percent literals intact for the driver to process.
    """

    def setUp(self):
        self.dialect = ClickHouseDialect_asynch()
        self.table = Table(
            'events', MetaData(),
            Column('x', ch_types.UInt32),
            Column('s', ch_types.String),
            engines.Memory()
        )

    def _do_execute(self, statement, extra_params=None):
        compiled = statement.compile(dialect=self.dialect)
        params = compiled.construct_params(
            extra_params or {}, escape_names=False
        )
        state = compiled._process_parameters_for_postcompile(params)
        cursor = MagicMock()
        self.dialect.do_execute(
            cursor, state.statement, dict(state.parameters)
        )
        return cursor.execute.call_args[0][0], cursor.execute.call_args[0][1]

    @staticmethod
    def _driver_substitute(statement, params):
        """Replicate asynch's process_ordinary_query substitution.

        See asynch.proto.connection.Connection.substitute_params: the
        driver uses pyformat by default whenever params is not None.
        """
        if params is None:
            return statement
        with patch.dict(
            os.environ, {'ASYNCH_SUBSTITUTE_PARAMS_STYLE': 'pyformat'}
        ):
            return ProtoConnection.substitute_params(statement, params)

    def test_literal_braces_survive_driver_substitution(self):
        # A JSON string literal in the SQL text is a plain ClickHouse
        # idiom (e.g. comparing a String column against a JSON payload).
        statement = select(self.table.c.x).where(
            self.table.c.x == 5,
            literal_column('payload = \'{"k":1}\''),
        )
        sent_statement, sent_params = self._do_execute(statement)

        final = self._driver_substitute(sent_statement, sent_params)

        self.assertIn('\'{"k":1}\'', final)
        self.assertIn('5', final)

    def test_percent_literal_reaches_server_undoubled(self):
        # SQLAlchemy escapes literal % as %% for the pyformat paramstyle.
        # The native driver undoes that via `query % params`; asynch's
        # default pyformat substitution must do the same.
        statement = select(
            literal_column("'100%'").label('pct'), self.table.c.x
        ).where(self.table.c.x == 5)
        sent_statement, sent_params = self._do_execute(statement)

        final = self._driver_substitute(sent_statement, sent_params)

        self.assertIn("'100%'", final)
        self.assertNotIn("'100%%'", final)

    def test_text_select_brace_value_with_empty_params(self):
        # text() binds are rendered inline via literal_execute, leaving
        # an empty params dict.  asynch still applies pyformat for an
        # empty dict, so braces from the rendered literal must pass through.
        statement = text('SELECT count(*) FROM events WHERE payload = :j')
        sent_statement, sent_params = self._do_execute(
            statement, {'j': '{"k":1}'}
        )

        final = self._driver_substitute(sent_statement, sent_params)

        self.assertIn('\'{"k":1}\'', final)
