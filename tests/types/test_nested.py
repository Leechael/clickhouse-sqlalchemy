import ast

from sqlalchemy import Column, inspect, select, text

from clickhouse_sqlalchemy import Table, engines, types
from tests.testcase import BaseTestCase
from tests.util import with_native_and_http_sessions


@with_native_and_http_sessions
class NestedTypeTestCase(BaseTestCase):
    def _flatten_nested_connection(self):
        connection = self.session.bind.connect()
        if connection.dialect.driver == 'http':
            transport = connection.connection.driver_connection.transport
            transport.ch_settings['flatten_nested'] = '1'
        else:
            connection.execute(text('SET flatten_nested = 1'))
        return connection

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

        with self._flatten_nested_connection() as connection:
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

        with self._flatten_nested_connection() as connection:
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
