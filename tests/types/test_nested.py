import ast
from contextlib import contextmanager

from sqlalchemy import Column, inspect, select, text

from clickhouse_sqlalchemy import Table, engines, types
from tests.testcase import BaseTestCase
from tests.util import with_native_and_http_sessions


@with_native_and_http_sessions
class NestedTypeTestCase(BaseTestCase):
    @contextmanager
    def _nested_connection(self, flatten_nested):
        connection = self.session.bind.connect()
        if connection.dialect.driver == 'http':
            transport = connection.connection.driver_connection.transport
            old_setting = transport.ch_settings.get('flatten_nested')
            transport.ch_settings['flatten_nested'] = str(flatten_nested)
        else:
            old_setting = None
            settings = dict(
                connection.get_execution_options().get('settings') or {}
            )
            settings['flatten_nested'] = flatten_nested
            connection = connection.execution_options(settings=settings)

        try:
            yield connection
        finally:
            if connection.dialect.driver == 'http':
                if old_setting is None:
                    transport.ch_settings.pop('flatten_nested', None)
                else:
                    transport.ch_settings['flatten_nested'] = old_setting
            connection.close()

    def _nested_table(self):
        return Table(
            'test_nested',
            self.metadata(),
            Column('id', types.UInt32),
            Column(
                'members',
                types.Nested(
                    Column('name', types.String),
                    Column('age', types.UInt8),
                )
            ),
            engines.Memory()
        )

    def _unflattened_nested_table(self):
        return Table(
            'test_nested_unflattened',
            self.metadata(),
            Column(
                'n',
                types.Nested(
                    Column('a', types.UInt32),
                    Column(
                        'b',
                        types.Nested(
                            Column('c', types.String),
                            Column(
                                'd',
                                types.Nested(Column('e', types.Date))
                            ),
                        )
                    ),
                )
            ),
            engines.Memory()
        )

    def _effective_flatten_nested(self, connection):
        value = connection.execute(
            text("SELECT getSetting('flatten_nested')")
        ).fetchall()[0][0]
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true')
        return bool(value)

    def _normalize_array_result(self, rows):
        if self.session.bind.dialect.driver != 'http':
            return rows

        return [
            (
                row[0],
                ast.literal_eval(row[1]),
                ast.literal_eval(row[2]),
            )
            for row in rows
        ]

    def test_flatten_nested_one_level_batch_insert_mapping_round_trip(self):
        table = self._nested_table()
        rows = [
            {
                'id': 1,
                'members': {
                    'name': ['alice', 'bob'],
                    'age': [34, 29],
                },
            },
            {
                'id': 2,
                'members': {
                    'name': ['carol'],
                    'age': [41],
                },
            },
        ]

        with self._nested_connection(1) as connection:
            table.drop(bind=connection, if_exists=True)
            table.create(bind=connection)
            try:
                connection.execute(table.insert(), rows)

                result = connection.execute(
                    select(
                        table.c.id,
                        table.c.members.name_,
                        table.c.members.age
                    ).order_by(table.c.id)
                ).fetchall()
            finally:
                table.drop(bind=connection)

        self.assertEqual(
            self._normalize_array_result(result),
            [
                (1, ['alice', 'bob'], [34, 29]),
                (2, ['carol'], [41]),
            ]
        )

    def test_flatten_nested_reflection_returns_array_subcolumns(self):
        table = self._nested_table()

        with self._nested_connection(1) as connection:
            table.drop(bind=connection, if_exists=True)
            table.create(bind=connection)
            try:
                columns = inspect(connection).get_columns(table.name)
            finally:
                table.drop(bind=connection)

        reflected = {column['name']: column['type'] for column in columns}

        self.assertNotIn('members', reflected)
        self.assertIsInstance(reflected['members.name'], types.Array)
        self.assertEqual(reflected['members.name'].item_type, types.String)
        self.assertIsInstance(reflected['members.age'], types.Array)
        self.assertEqual(reflected['members.age'].item_type, types.UInt8)

    def test_probe_unflattened_nested_describe_shape(self):
        if self.server_version < (24, 6, 0):
            self.skipTest(
                'Unflattened Nested DESCRIBE shape is asserted from 24.6'
            )

        table = self._unflattened_nested_table()

        with self._nested_connection(0) as connection:
            table.drop(bind=connection, if_exists=True)
            table.create(bind=connection)
            try:
                server_version = connection.execute(
                    text('SELECT version()')
                ).fetchall()[0][0]
                flatten_nested = self._effective_flatten_nested(connection)
                described = connection.execute(text(
                    'DESCRIBE TABLE {}'.format(table.name)
                )).fetchall()
            finally:
                table.drop(bind=connection)

        self.assertRegex(server_version, r'^\d+\.\d+\.\d+')
        self.assertFalse(flatten_nested)
        self.assertEqual(
            [(row[0], row[1]) for row in described],
            [(
                'n',
                'Nested(a UInt32, b Nested(c String, d Nested(e Date)))',
            )]
        )

    def test_unflattened_nested_describe_returns_nested_type(self):
        if self.server_version < (24, 6, 0):
            self.skipTest(
                'Unflattened Nested DESCRIBE shape is asserted from 24.6'
            )

        table = self._unflattened_nested_table()

        with self._nested_connection(0) as connection:
            table.drop(bind=connection, if_exists=True)
            table.create(bind=connection)
            try:
                columns = inspect(connection).get_columns(table.name)
            finally:
                table.drop(bind=connection)

        reflected = columns[0]['type']
        self.assertIsInstance(reflected, types.Nested)
        self.assertEqual([column.name for column in reflected.columns],
                         ['a', 'b'])

        nested_b = reflected.columns[1].type
        self.assertIsInstance(nested_b, types.Nested)
        self.assertEqual([column.name for column in nested_b.columns],
                         ['c', 'd'])

        nested_d = nested_b.columns[1].type
        self.assertIsInstance(nested_d, types.Nested)
        self.assertEqual([column.name for column in nested_d.columns], ['e'])
        self.assertIsInstance(nested_d.columns[0].type, types.Date)
