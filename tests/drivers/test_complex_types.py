import enum
from unittest import TestCase
from unittest.mock import patch

from sqlalchemy import Column, MetaData, create_engine
from sqlalchemy.sql import type_api
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import Table, engines, types
from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect
from clickhouse_sqlalchemy.drivers.http import connector
from clickhouse_sqlalchemy.drivers.http.base import ClickHouseDialect_http


class ComplexTypeReflectionTestCase(TestCase):
    def setUp(self):
        self.dialect = ClickHouseDialect()

    def _get_type(self, spec, name='x'):
        return self.dialect._get_column_type(name, spec)

    def test_reflect_map_of_map_nullable_value(self):
        coltype = self._get_type(
            'Map(String, Map(String, Nullable(String)))'
        )

        self.assertIsInstance(coltype, types.Map)
        self.assertEqual(coltype.key_type, types.String)

        value_type = coltype.value_type
        self.assertIsInstance(value_type, types.Map)
        self.assertEqual(value_type.key_type, types.String)
        self.assertIsInstance(value_type.value_type, types.Nullable)
        self.assertIsInstance(value_type.value_type.nested_type, types.String)

    def test_reflect_map_with_enum_key(self):
        coltype = self._get_type(
            "Map(Enum8('hello, world' = 1, 'plain' = 2), String)"
        )

        self.assertIsInstance(coltype, types.Map)

        key_type = type_api.to_instance(coltype.key_type)
        self.assertIsInstance(key_type, types.Enum8)
        self.assertEqual(
            {option.name: option.value for option in key_type.enum_class},
            {'hello, world': 1, 'plain': 2}
        )
        self.assertEqual(coltype.value_type, types.String)

    def test_reflect_tuple_with_nested_tuple_and_map(self):
        coltype = self._get_type(
            'Tuple(Tuple(String, UInt32), Map(String, Nullable(Int64)))'
        )

        self.assertIsInstance(coltype, types.Tuple)
        self.assertEqual(len(coltype.nested_types), 2)
        self.assertIsInstance(coltype.nested_types[0], types.Tuple)
        self.assertIsInstance(coltype.nested_types[1], types.Map)

        tuple_type = coltype.nested_types[0]
        self.assertEqual(tuple_type.nested_types[0], types.String)
        self.assertEqual(tuple_type.nested_types[1], types.UInt32)

    def test_reflect_named_tuple(self):
        coltype = self._get_type('Tuple(name String, value Float32)')

        self.assertIsInstance(coltype, types.Tuple)
        self.assertEqual(coltype.nested_types[0][0], 'name')
        self.assertEqual(coltype.nested_types[0][1], types.String)
        self.assertEqual(coltype.nested_types[1][0], 'value')
        self.assertEqual(coltype.nested_types[1][1], types.Float32)

    def test_reflect_datetime64_timezone_argument(self):
        coltype = self._get_type("DateTime64(3, 'America/New_York')")

        self.assertIsInstance(coltype, types.DateTime64)
        self.assertEqual(coltype.precision, 3)
        self.assertEqual(coltype.timezone, 'America/New_York')

    def test_reflect_datetime_timezone_argument(self):
        coltype = self._get_type("DateTime('America/New_York')")

        self.assertIsInstance(coltype, types.DateTime)
        self.assertEqual(coltype.timezone, 'America/New_York')

    def test_reflect_aggregate_function_with_parameterized_function(self):
        coltype = self._get_type(
            'AggregateFunction(quantiles(0.5, 0.9), UInt64)'
        )

        self.assertIsInstance(coltype, types.AggregateFunction)
        self.assertEqual(coltype.agg_func, 'quantiles(0.5, 0.9)')
        self.assertEqual(len(coltype.nested_types), 1)
        self.assertIsInstance(coltype.nested_types[0], types.UInt64)

    def test_reflect_simple_aggregate_function_with_tuple_argument(self):
        coltype = self._get_type(
            'SimpleAggregateFunction('
            'maxMap, Tuple(Array(UInt32), Array(UInt32)))'
        )

        self.assertIsInstance(coltype, types.SimpleAggregateFunction)
        self.assertEqual(coltype.agg_func, 'maxMap')
        self.assertEqual(len(coltype.nested_types), 1)
        self.assertIsInstance(coltype.nested_types[0], types.Tuple)

    def test_reflect_nested_type(self):
        coltype = self._get_type(
            'Nested(colors Map(String, String), '
            "state Enum8('ready' = 1, 'done' = 2))"
        )

        self.assertIsInstance(coltype, types.Nested)
        self.assertEqual([c.name for c in coltype.columns],
                         ['colors', 'state'])
        self.assertIsInstance(coltype.columns[0].type, types.Map)
        self.assertIsInstance(type_api.to_instance(coltype.columns[1].type),
                              types.Enum8)

    def test_reflect_depth_three_nested_type_for_unflattened_future(self):
        coltype = self._get_type(
            'Nested(a UInt32, b Nested(c String, d Nested(e Date)))'
        )

        self.assertIsInstance(coltype, types.Nested)
        self.assertEqual([column.name for column in coltype.columns],
                         ['a', 'b'])

        nested_b = coltype.columns[1].type
        self.assertIsInstance(nested_b, types.Nested)
        self.assertEqual([column.name for column in nested_b.columns],
                         ['c', 'd'])

        nested_d = nested_b.columns[1].type
        self.assertIsInstance(nested_d, types.Nested)
        self.assertEqual([column.name for column in nested_d.columns], ['e'])
        self.assertIsInstance(nested_d.columns[0].type, types.Date)


class ComplexTypeCompilationTestCase(TestCase):
    def setUp(self):
        self.dialect = ClickHouseDialect()

    def _compile_column(self, column):
        table = Table('t', MetaData(), Column('id', types.UInt32), column,
                      engines.Memory())
        return str(CreateTable(table).compile(dialect=self.dialect))

    def test_compile_map_with_enum_key(self):
        class Color(enum.Enum):
            hello = 1
            world = 2

        statement = self._compile_column(
            Column('colors', types.Map(types.Enum8(Color), types.String))
        )

        self.assertIn(
            "colors Map(Enum8('hello' = 1, 'world' = 2), String)",
            statement
        )

    def test_compile_nested_tuple_and_map(self):
        statement = self._compile_column(
            Column(
                'payload',
                types.Tuple(
                    types.Tuple(types.String, types.UInt32),
                    types.Map(types.String, types.Nullable(types.Int64))
                )
            )
        )

        self.assertIn(
            'payload Tuple(Tuple(String, UInt32), '
            'Map(String, Nullable(Int64)))',
            statement
        )

    def test_compile_map_of_map_nullable_value(self):
        statement = self._compile_column(
            Column(
                'metadata',
                types.Map(
                    types.String,
                    types.Map(types.String, types.Nullable(types.String))
                )
            )
        )

        self.assertIn(
            'metadata Map(String, Map(String, Nullable(String)))',
            statement
        )


class NestedTypeLifecycleTestCase(TestCase):
    def setUp(self):
        self.dialect = ClickHouseDialect()
        self.table = Table(
            'family',
            MetaData(),
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

    def test_nested_type_compiles_for_create_table(self):
        statement = str(CreateTable(self.table).compile(dialect=self.dialect))

        self.assertIn(
            'members Nested(name String, age UInt8)',
            statement
        )

    def test_nested_type_compiles_for_insert_statement(self):
        compiled = self.table.insert().compile(dialect=self.dialect)

        self.assertEqual(
            str(compiled),
            'INSERT INTO family (id, members) VALUES (%(id)s, %(members)s)'
        )

    def test_nested_empty_columns_rejected(self):
        with self.assertRaisesRegex(
            ValueError, 'columns must be specified for nested type'
        ):
            types.Nested()


class FlattenedNestedInsertExecutionTestCase(TestCase):
    class StopExecution(Exception):
        pass

    def setUp(self):
        self.table = Table(
            'family',
            MetaData(),
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

    def _execute_with_http_cursor_patch(self, cursor_method, rows):
        captured = []

        def fake_cursor_method(cursor, operation, parameters=None,
                               context=None):
            captured.append((operation, parameters))
            raise self.StopExecution

        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ), patch.object(
            connector.Cursor, cursor_method, fake_cursor_method
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaises(self.StopExecution):
                with engine.connect() as connection:
                    connection.execute(self.table.insert(), rows)

        return captured[0]

    def test_flatten_nested_one_level_batch_insert_mapping_execution(self):
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

        statement, parameters = self._execute_with_http_cursor_patch(
            'executemany', rows
        )

        self.assertEqual(
            statement,
            'INSERT INTO family (id, members.name, members.age) '
            'VALUES (%(id)s, %(members.name)s, %(members.age)s)'
        )
        self.assertEqual(
            parameters,
            [
                {
                    'id': 1,
                    'members.name': ['alice', 'bob'],
                    'members.age': [34, 29],
                },
                {
                    'id': 2,
                    'members.name': ['carol'],
                    'members.age': [41],
                },
            ]
        )

    def test_flatten_nested_one_level_single_insert_mapping_execution(self):
        statement, parameters = self._execute_with_http_cursor_patch(
            'execute',
            {
                'id': 1,
                'members': {
                    'name': ['alice'],
                    'age': [34],
                },
            }
        )

        self.assertEqual(
            statement,
            'INSERT INTO family (id, members.name, members.age) '
            'VALUES (%(id)s, %(members.name)s, %(members.age)s)'
        )
        self.assertEqual(
            parameters,
            {
                'id': 1,
                'members.name': ['alice'],
                'members.age': [34],
            }
        )

    def test_flatten_nested_direct_dotted_keys_documented_unsupported(self):
        statement, parameters = self._execute_with_http_cursor_patch(
            'execute',
            {
                'id': 1,
                'members.name': ['alice'],
                'members.age': [34],
            }
        )

        self.assertEqual(
            statement,
            'INSERT INTO family (id) VALUES (%(id)s)'
        )
        self.assertEqual(parameters, {'id': 1})

    def test_flatten_nested_row_oriented_payload_rejected(self):
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                NotImplementedError,
                'Row-oriented Nested payloads are not supported'
            ):
                with engine.connect() as connection:
                    connection.execute(
                        self.table.insert(),
                        {
                            'id': 1,
                            'members': [
                                {'name': 'alice', 'age': 34},
                            ],
                        }
                    )

    def test_unflattened_nested_insert_payload_rejected_with_clear_error(self):
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                NotImplementedError,
                'flatten_nested=0 insert support is not implemented'
            ):
                with engine.connect() as connection:
                    connection.execution_options(
                        settings={'flatten_nested': 0}
                    ).execute(
                        self.table.insert(),
                        {
                            'id': 1,
                            'members': [
                                {'name': 'alice', 'age': 34},
                            ],
                        }
                    )

    def test_unflattened_nested_mapping_payload_rejected_with_clear_error(self):
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                NotImplementedError,
                'flatten_nested=0 insert support is not implemented'
            ):
                with engine.connect() as connection:
                    connection.execution_options(
                        settings={'flatten_nested': 0}
                    ).execute(
                        self.table.insert(),
                        {
                            'id': 1,
                            'members': {
                                'name': ['alice'],
                                'age': [34],
                            },
                        }
                    )

    def test_flatten_nested_missing_child_rejected(self):
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                KeyError,
                "Nested column 'members' is missing child 'age'"
            ):
                with engine.connect() as connection:
                    connection.execute(
                        self.table.insert(),
                        {
                            'id': 1,
                            'members': {
                                'name': ['alice'],
                            },
                        }
                    )
