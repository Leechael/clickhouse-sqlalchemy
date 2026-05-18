import enum
from unittest import TestCase
from unittest.mock import MagicMock, patch

from sqlalchemy import Column, MetaData, create_engine, literal, select
from sqlalchemy.sql import type_api
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import Table, engines, types
from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect
from clickhouse_sqlalchemy.drivers.http import connector
from clickhouse_sqlalchemy.drivers.http.base import ClickHouseDialect_http
from clickhouse_sqlalchemy.drivers.native import connector as native_connector
from clickhouse_sqlalchemy.drivers.native.base import ClickHouseDialect_native


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

    def test_reflect_map_with_doubled_quote_enum_key(self):
        coltype = self._get_type(
            "Map(Enum8('O''Brien, Jr.' = 1, 'plain' = 2), String)"
        )

        self.assertIsInstance(coltype, types.Map)

        key_type = type_api.to_instance(coltype.key_type)
        self.assertIsInstance(key_type, types.Enum8)
        self.assertEqual(
            {option.name: option.value for option in key_type.enum_class},
            {"O'Brien, Jr.": 1, 'plain': 2}
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

    def test_nested_type_adapt_preserves_columns_for_subclasses(self):
        class CustomNested(types.Nested):
            pass

        adapted = self.table.c.members.type.adapt(CustomNested)

        self.assertIsInstance(adapted, CustomNested)
        self.assertEqual(
            [column.name for column in adapted.columns],
            ['name', 'age']
        )

    def test_nested_type_adapt_rejects_unrelated_type(self):
        with self.assertRaisesRegex(
            NotImplementedError,
            'Nested type adaptation to String is not supported'
        ):
            self.table.c.members.type.adapt(types.String)


class FlattenedNestedInsertExecutionTestCase(TestCase):
    class StopExecution(Exception):
        pass

    class FakeContext:
        # Used to exercise _prepare_flattened_nested_insert directly when the
        # dialect-layer validation cannot be reached through the public
        # SQLAlchemy execution path because SA Core's bind check pre-empts it.
        isinsert = True
        execution_options = {}

        def __init__(self, table):
            class Compiled:
                compiled_parameters = None
                insert_single_values_expr = None

                def __init__(self, table):
                    self.statement = table.insert()

            self.compiled = Compiled(table)
            self.parameters = None
            self.compiled_parameters = None

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
        self.multi_nested_table = Table(
            'family_multi',
            MetaData(),
            Column('id', types.UInt32),
            Column(
                'members',
                types.Nested(
                    Column('name', types.String),
                    Column('age', types.UInt8),
                )
            ),
            Column(
                'pets',
                types.Nested(
                    Column('name', types.String),
                    Column('kind', types.String),
                )
            ),
            engines.Memory()
        )

    def _execute_with_http_cursor_patch(
        self, cursor_method, rows, insert_stmt=None
    ):
        mocked = MagicMock(side_effect=self.StopExecution)

        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ), patch.object(
            connector.Cursor, cursor_method, mocked
        ):
            engine = create_engine('clickhouse://localhost/default')
            statement = (
                insert_stmt if insert_stmt is not None
                else self.table.insert()
            )
            with self.assertRaises(self.StopExecution):
                with engine.connect() as connection:
                    connection.execute(statement, rows)

        operation, parameters = mocked.call_args.args[:2]
        return operation, parameters

    def _execute_with_native_cursor_patch(
        self, cursor_method, rows, insert_stmt=None
    ):
        mocked = MagicMock(side_effect=self.StopExecution)

        with patch.object(
            ClickHouseDialect_native, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_native, '_get_default_schema_name',
            return_value='default'
        ), patch.object(
            native_connector.Cursor, cursor_method, mocked
        ):
            engine = create_engine('clickhouse+native://localhost/default')
            statement = (
                insert_stmt if insert_stmt is not None
                else self.table.insert()
            )
            with self.assertRaises(self.StopExecution):
                with engine.connect() as connection:
                    connection.execute(statement, rows)

        operation, parameters = mocked.call_args.args[:2]
        return operation, parameters

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
        # SQLAlchemy Core drops dotted keys that are not Table columns before
        # the dialect hook sees parameters; stage one documents this behavior.
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

    def test_flatten_nested_insert_select_not_expanded(self):
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
            connector.Cursor, 'execute', fake_cursor_method
        ):
            engine = create_engine('clickhouse://localhost/default')
            statement = self.table.insert().from_select(
                ['id'],
                select(literal(1))
            )
            with self.assertRaises(self.StopExecution):
                with engine.connect() as connection:
                    connection.execute(statement)

        self.assertEqual(
            captured[0][0],
            'INSERT INTO family (id) SELECT %(param_1)s AS anon_1'
        )

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
                ValueError,
                "Nested column 'members' is missing child keys \\['age'\\]"
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

    def test_flatten_nested_extra_child_rejected(self):
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                ValueError,
                "Nested column 'members' got unknown child keys \\['typo'\\]"
            ):
                with engine.connect() as connection:
                    connection.execute(
                        self.table.insert(),
                        {
                            'id': 1,
                            'members': {
                                'name': ['alice'],
                                'age': [34],
                                'typo': ['bad'],
                            },
                        }
                    )

    def test_flatten_nested_batch_rows_must_use_same_columns(self):
        # Defense-in-depth on the dialect helper. SA Core's bind check
        # normally rejects sparse rows before this validation runs, so the
        # public-path UX is covered by test_flatten_nested_batch_sparse_rows_
        # error_is_actionable instead.
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                ValueError,
                'Batch INSERT rows must use the same columns after '
                'Nested expansion'
            ):
                engine.dialect._prepare_flattened_nested_insert(
                    'INSERT',
                    [
                        {
                            'id': 1,
                            'members': {
                                'name': ['alice'],
                                'age': [34],
                            },
                        },
                        {'id': 2},
                    ],
                    self.FakeContext(self.table)
                )

    def test_flatten_nested_multiple_columns_must_use_same_columns(self):
        # Defense-in-depth on the dialect helper. See sibling test.
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with self.assertRaisesRegex(
                ValueError,
                'Batch INSERT rows must use the same columns after '
                'Nested expansion'
            ):
                engine.dialect._prepare_flattened_nested_insert(
                    'INSERT',
                    [
                        {
                            'id': 1,
                            'members': {
                                'name': ['alice'],
                                'age': [34],
                            },
                        },
                        {
                            'id': 2,
                            'pets': {
                                'name': ['fido'],
                                'kind': ['dog'],
                            },
                        },
                    ],
                    self.FakeContext(self.multi_nested_table)
                )

    def test_flatten_nested_batch_sparse_rows_error_is_actionable(self):
        # When a Nested column is present in some rows and missing in others,
        # the user-visible error must guide them to a fix (e.g. tell them to
        # provide the Nested column in every row), not only report the diff.
        # SA Core's bind check currently fires first with a generic
        # "A value is required for bind parameter 'members'..." which does
        # not mention how to satisfy the constraint.
        with patch.object(
            ClickHouseDialect_http, '_get_server_version_info',
            return_value=(24, 8, 1)
        ), patch.object(
            ClickHouseDialect_http, '_get_default_schema_name',
            return_value='default'
        ):
            engine = create_engine('clickhouse://localhost/default')
            with engine.connect() as connection:
                with self.assertRaises(Exception) as cm:
                    connection.execute(
                        self.table.insert(),
                        [
                            {
                                'id': 1,
                                'members': {
                                    'name': ['alice'],
                                    'age': [34],
                                },
                            },
                            {'id': 2},
                        ]
                    )

        message = str(cm.exception).lower()
        self.assertTrue(
            any(
                hint in message
                for hint in (
                    'every row', 'each row', 'all rows',
                    'in every', 'in each', 'use {}',
                )
            ),
            'sparse-row error message is not actionable: %s' % message,
        )

    def test_flatten_nested_insert_preserves_prefix_with(self):
        # _render_flattened_nested_insert rebuilds the INSERT from table
        # metadata and currently drops any modifiers attached to the compiled
        # statement (prefix_with, with_hint, future SETTINGS clauses, etc.).
        # Stage 4 must forward these so users do not silently lose them.
        statement, _ = self._execute_with_http_cursor_patch(
            'execute',
            {
                'id': 1,
                'members': {
                    'name': ['alice'],
                    'age': [34],
                },
            },
            insert_stmt=self.table.insert().prefix_with('IGNORE'),
        )

        self.assertIn('IGNORE', statement)

    def test_flatten_nested_native_insert_preserves_prefix_with(self):
        statement, parameters = self._execute_with_native_cursor_patch(
            'executemany',
            {
                'id': 1,
                'members': {
                    'name': ['alice'],
                    'age': [34],
                },
            },
            insert_stmt=self.table.insert().prefix_with('IGNORE'),
        )

        self.assertEqual(
            statement,
            'INSERT IGNORE INTO family (id, members.name, members.age) VALUES'
        )
        self.assertEqual(
            parameters,
            [
                {
                    'id': 1,
                    'members.name': ['alice'],
                    'members.age': [34],
                }
            ]
        )

    def test_flatten_nested_schema_qualified_insert_rendering(self):
        table = Table(
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
            engines.Memory(),
            schema='analytics'
        )
        self.table = table

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
            'INSERT INTO analytics.family '
            '(id, members.name, members.age) '
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
