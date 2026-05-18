import enum
import re
import weakref
from collections.abc import Mapping

from sqlalchemy import schema, types as sqltypes, util as sa_util, text
from sqlalchemy.engine import default, reflection
from sqlalchemy.sql import (
    compiler, elements, type_api
)
from sqlalchemy.util import (
    warn,
)

from .compilers.ddlcompiler import ClickHouseDDLCompiler
from .compilers.sqlcompiler import ClickHouseSQLCompiler
from .compilers.typecompiler import ClickHouseTypeCompiler
from .reflection import ClickHouseInspector
from .util import (
    get_inner_spec, parse_arguments, parse_named_type_argument,
    parse_string_literal,
)
from .. import types

# Column specifications
colspecs = {}


_flatten_nested_set_re = re.compile(
    r'^\s*SET\s+(.+?)\s*;?\s*$',
    re.IGNORECASE,
)


# Type converters
ischema_names = {
    'Int256': types.Int256,
    'Int128': types.Int128,
    'Int64': types.Int64,
    'Int32': types.Int32,
    'Int16': types.Int16,
    'Int8': types.Int8,
    'UInt256': types.UInt256,
    'UInt128': types.UInt128,
    'UInt64': types.UInt64,
    'UInt32': types.UInt32,
    'UInt16': types.UInt16,
    'UInt8': types.UInt8,
    'Date': types.Date,
    'Date32': types.Date32,
    'DateTime': types.DateTime,
    'DateTime64': types.DateTime64,
    'Float64': types.Float64,
    'Float32': types.Float32,
    'Decimal': types.Decimal,
    'Decimal32': types.Decimal32,
    'Decimal64': types.Decimal64,
    'Decimal128': types.Decimal128,
    'Decimal256': types.Decimal256,
    'String': types.String,
    'FixedString': types.FixedString,
    'Bool': types.Boolean,
    'Boolean': types.Boolean,
    'UUID': types.UUID,
    'IPv4': types.IPv4,
    'IPv6': types.IPv6,
    'Enum8': types.Enum8,
    'Enum16': types.Enum16,
    'IntervalDay': types.IntervalDay,
    'IntervalWeek': types.IntervalWeek,
    'IntervalMonth': types.IntervalMonth,
    'IntervalYear': types.IntervalYear,
    'IntervalHour': types.IntervalHour,
    'IntervalMinute': types.IntervalMinute,
    'IntervalSecond': types.IntervalSecond,
    'IntervalNanosecond': types.IntervalNanosecond,
    'IntervalMicrosecond': types.IntervalMicrosecond,
    'IntervalMillisecond': types.IntervalMillisecond,
    'IntervalQuarter': types.IntervalQuarter,
    'Nothing': types.Nothing,
    'Null': types.Null,
    'Object(\'json\')': types.JSON,
    '_array': types.Array,
    '_nullable': types.Nullable,
    '_lowcardinality': types.LowCardinality,
    '_tuple': types.Tuple,
    '_map': types.Map,
    '_nested': types.Nested,
    '_aggregatefunction': types.AggregateFunction,
    '_simpleaggregatefunction': types.SimpleAggregateFunction,
}


class ClickHouseIdentifierPreparer(compiler.IdentifierPreparer):

    reserved_words = compiler.IdentifierPreparer.reserved_words | set((
        'index',  # reserved in the 'create table' syntax, at least.
    ))
    # Alternatively, use `_requires_quotes = lambda self, value: True`

    def _escape_identifier(self, value):
        value = value.replace(self.escape_quote, self.escape_to_quote)
        return value.replace('%', '%%')


class ClickHouseExecutionContextBase(default.DefaultExecutionContext):
    @sa_util.memoized_property
    def should_autocommit(self):
        return False  # No DML supported, never autocommit


class ClickHouseDialect(default.DefaultDialect):
    name = 'clickhouse'
    supports_cast = True
    supports_unicode_statements = True
    supports_unicode_binds = True
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False
    supports_native_decimal = True
    supports_native_boolean = True
    non_native_boolean_check_constraint = False
    supports_alter = True
    supports_sequences = False
    supports_native_enum = True  # Do not render check constraints on enums.
    supports_multivalues_insert = True
    supports_statement_cache = True

    supports_comments = True
    inline_comments = True
    renders_insert_values_template = False

    # Dialect related-features
    supports_delete = True
    supports_update = True
    supports_engine_reflection = True
    supports_table_comment_reflection = True

    engine_reflection = True  # Disables engine reflection from URL.

    max_identifier_length = 127
    default_paramstyle = 'pyformat'
    colspecs = colspecs
    ischema_names = ischema_names
    convert_unicode = True
    returns_unicode_strings = True
    description_encoding = None
    postfetch_lastrowid = False
    forced_server_version_string = None

    preparer = ClickHouseIdentifierPreparer
    type_compiler = ClickHouseTypeCompiler
    statement_compiler = ClickHouseSQLCompiler
    ddl_compiler = ClickHouseDDLCompiler

    construct_arguments = [
        (schema.Table, {
            'data': [],
            'cluster': None,
        }),
        (schema.Column, {
            'codec': None,
            'materialized': None,
            'alias': None,
            'after': None,
        }),
    ]

    inspector = ClickHouseInspector

    def __init__(
        self,
        json_serializer=None,
        json_deserializer=None,
        **kwargs,
    ):
        default.DefaultDialect.__init__(self, **kwargs)
        self._json_deserializer = json_deserializer
        self._json_serializer = json_serializer
        self._flatten_nested_settings = weakref.WeakKeyDictionary()
        self._warned_flatten_nested_tracking_unavailable = False

    def initialize(self, connection):
        super(ClickHouseDialect, self).initialize(connection)

        version = self.server_version_info

        self.supports_delete = version >= (1, 1, 54388)
        self.supports_update = version >= (18, 12, 14)
        self.supports_engine_reflection = version >= (18, 16)
        self.supports_table_comment_reflection = version >= (21, 6)

    def _execute(self, connection, sql, scalar=False, **kwargs):
        raise NotImplementedError

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        query = text(
            "SELECT name FROM system.tables WHERE engine LIKE '%View' "
            "AND database = :database"
        )

        database = schema or connection.engine.url.database
        rows = self._execute(connection, query, database=database)
        return [row.name for row in rows]

    def has_table(self, connection, table_name, schema=None, **kw):
        quote = self._quote_table_name
        if schema:
            qualified_name = quote(schema) + '.' + quote(table_name)
        else:
            qualified_name = quote(table_name)
        query = text('EXISTS TABLE {}'.format(qualified_name))
        for r in self._execute(connection, query):
            if r.result == 1:
                return True
        return False

    def _quote_table_name(self, table_name):
        # Use case: `describe table (select ...)`, over a TextClause.
        if isinstance(table_name, elements.TextClause):
            return str(table_name)
        return self.identifier_preparer.quote_identifier(table_name)

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        quote = self._quote_table_name
        if schema:
            qualified_name = quote(schema) + '.' + quote(table_name)
        else:
            qualified_name = quote(table_name)
        query = 'DESCRIBE TABLE {}'.format(qualified_name)
        rows = self._execute(connection, query)

        return [
            self._get_column_info(
                r.name, r.type, r.default_type, r.default_expression,
                getattr(r, 'comment', None)
            ) for r in rows
        ]

    def _get_column_info(self, name, format_type, default_type,
                         default_expression, comment):
        col_type = self._get_column_type(name, format_type)
        col_default = self._get_column_default(default_type,
                                               default_expression)
        result = {
            'name': name,
            'type': col_type,
            'nullable': format_type.startswith('Nullable('),
            'default': col_default,
            'comment': comment or None
        }
        return result

    def _get_column_default(self, default_type, default_expression):
        if default_type == 'DEFAULT':
            return default_expression
        return None

    def _get_column_type(self, name, spec):
        if spec.startswith('Array'):
            inner = get_inner_spec(spec)
            coltype = self.ischema_names['_array']
            return coltype(self._get_column_type(name, inner))

        elif spec.startswith('FixedString'):
            length = int(spec[12:-1])
            return self.ischema_names['FixedString'](length)

        elif spec.startswith('Nullable'):
            inner = get_inner_spec(spec)
            coltype = self.ischema_names['_nullable']
            return coltype(self._get_column_type(name, inner))

        elif spec.startswith('LowCardinality'):
            inner = get_inner_spec(spec)
            coltype = self.ischema_names['_lowcardinality']
            return coltype(self._get_column_type(name, inner))

        elif spec.startswith('AggregateFunction'):
            params = get_inner_spec(spec)

            arguments = parse_arguments(params)
            agg_func, inner = arguments[0], arguments[1:]

            inner_types = [
                self._get_column_type(name, param)
                for param in inner
            ]
            coltype = self.ischema_names['_aggregatefunction']
            return coltype(agg_func, *inner_types)

        elif spec.startswith('SimpleAggregateFunction'):
            params = get_inner_spec(spec)

            arguments = parse_arguments(params)
            agg_func, inner = arguments[0], arguments[1:]

            inner_types = [
                self._get_column_type(name, param)
                for param in inner
            ]
            coltype = self.ischema_names['_simpleaggregatefunction']
            return coltype(agg_func, *inner_types)

        elif spec.startswith('Tuple'):
            inner = get_inner_spec(spec)
            coltype = self.ischema_names['_tuple']
            inner_types = []
            for arg in parse_arguments(inner):
                arg_name, type_spec = parse_named_type_argument(arg)
                col_type = self._get_column_type(name, type_spec)
                if arg_name:
                    inner_types.append((arg_name, col_type))
                else:
                    inner_types.append(col_type)
            return coltype(*inner_types)

        elif spec.startswith('Map'):
            inner = get_inner_spec(spec)
            coltype = self.ischema_names['_map']
            inner_types = [
                self._get_column_type(name, t)
                for t in parse_arguments(inner)
            ]
            return coltype(*inner_types)

        elif spec.startswith('Nested'):
            inner = get_inner_spec(spec)
            columns = []
            for arg in parse_arguments(inner):
                arg_name, type_spec = parse_named_type_argument(arg)
                if not arg_name:
                    warn("Did not recognize nested column '%s' of column '%s'"
                         % (arg, name))
                    return sqltypes.NullType
                columns.append(
                    schema.Column(
                        arg_name,
                        type_api.to_instance(
                            self._get_column_type(arg_name, type_spec)
                        )
                    )
                )

            coltype = self.ischema_names['_nested']
            return coltype(*columns)

        elif spec.startswith('Enum'):
            pos = spec.find('(')
            type = spec[:pos]
            coltype = self.ischema_names[type]

            options = dict()
            if pos >= 0:
                options = self._parse_options(
                    spec[pos + 1: spec.rfind(')')]
                )
            if not options:
                return sqltypes.NullType

            type_enum = enum.Enum('%s_enum' % name, options)
            return lambda: coltype(type_enum)

        elif spec.startswith('Decimal'):
            if spec.startswith('Decimal32'):
                coltype = self.ischema_names['Decimal32']
                return coltype(self._parse_decimal_scale(spec))
            elif spec.startswith('Decimal64'):
                coltype = self.ischema_names['Decimal64']
                return coltype(self._parse_decimal_scale(spec))
            elif spec.startswith('Decimal128'):
                coltype = self.ischema_names['Decimal128']
                return coltype(self._parse_decimal_scale(spec))
            elif spec.startswith('Decimal256'):
                coltype = self.ischema_names['Decimal256']
                return coltype(self._parse_decimal_scale(spec))
            else:
                coltype = self.ischema_names['Decimal']
                return coltype(*self._parse_decimal_params(spec))
        elif spec.startswith('Interval'):
            try:
                return self.ischema_names[spec]
            except KeyError:
                warn("Did not recognize type '%s' of column '%s'" %
                     (spec, name))
                return sqltypes.NullType
        elif spec.startswith('DateTime64'):
            coltype = self.ischema_names['DateTime64']
            return coltype(*self._parse_detetime64_params(spec))
        elif spec.startswith('DateTime'):
            coltype = self.ischema_names['DateTime']
            return coltype(*self._parse_detetime_params(spec))
        else:
            try:
                return self.ischema_names[spec]
            except KeyError:
                warn("Did not recognize type '%s' of column '%s'" %
                     (spec, name))
                return sqltypes.NullType

    @staticmethod
    def _parse_decimal_params(spec):
        inner_spec = get_inner_spec(spec)
        precision, scale = inner_spec.split(',')
        return int(precision.strip()), int(scale.strip())

    @staticmethod
    def _parse_decimal_scale(spec):
        inner_spec = get_inner_spec(spec)
        return int(inner_spec.strip())

    @staticmethod
    def _parse_detetime64_params(spec):
        inner_spec = get_inner_spec(spec)
        if not inner_spec:
            return []
        params = list(parse_arguments(inner_spec))
        params[0] = int(params[0])
        if len(params) > 1:
            params[1] = parse_string_literal(params[1])
        return params

    @staticmethod
    def _parse_detetime_params(spec):
        inner_spec = get_inner_spec(spec)
        if not inner_spec:
            return []
        return [parse_string_literal(inner_spec)]

    @staticmethod
    def _parse_options(option_string):
        options = dict()
        for option in parse_arguments(option_string):
            if not option:
                continue

            name, value = option.split('=', 1)
            name = parse_string_literal(name)
            options[name] = int(value.strip())

        return options

    @reflection.cache
    def get_schema_names(self, connection, **kw):
        rows = self._execute(connection, 'SHOW DATABASES')
        return [row.name for row in rows]

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        # No support for foreign keys.
        return []

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        if not self.supports_engine_reflection:
            return {}

        if schema:
            query = (("SELECT primary_key FROM system.tables "
                     "WHERE database='{}' AND name='{}'")
                     .format(schema, table_name))
        else:
            query = (
                "SELECT primary_key FROM system.tables WHERE name='{}'"
            ).format(table_name)

        rows = self._execute(connection, query)
        for r in rows:
            primary_keys = r.primary_key
            if primary_keys:
                return {
                    "constrained_columns": tuple(primary_keys.split(", ")),
                }
        return {}

    @reflection.cache
    def get_indexes(self, connection, table_name, schema=None, **kw):
        # No support for indexes.
        return []

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        query = text(
            "SELECT name FROM system.tables "
            "WHERE engine NOT LIKE '%View' "
            "AND name NOT LIKE '.inner%' "
            "AND database = :database"
        )

        database = schema or connection.engine.url.database
        rows = self._execute(connection, query, database=database)
        return [row.name for row in rows]

    @reflection.cache
    def get_engine(self, connection, table_name, schema=None, **kw):
        columns = [
            'name', 'engine_full', 'engine', 'partition_key', 'sorting_key',
            'primary_key', 'sampling_key'
        ]

        database = schema if schema else connection.engine.url.database

        query = text(
            'SELECT {} FROM system.tables '
            'WHERE database = :database AND name = :name'
            .format(', '.join(columns))
        )

        rows = self._execute(
            connection, query, database=database, name=table_name
        )

        row = next(rows, None)

        if row:
            return {x: getattr(row, x, None) for x in columns}

    @reflection.cache
    def get_table_comment(self, connection, table_name, schema=None, **kw):
        if not self.supports_table_comment_reflection:
            raise NotImplementedError()

        database = schema if schema else connection.engine.url.database

        query = text(
            'SELECT comment FROM system.tables '
            'WHERE database = :database AND name = :name'
        )
        comment = self._execute(
            connection, query, database=database, name=table_name, scalar=True
        )
        return {'text': comment or None}

    def get_isolation_level_values(self, dbapi_connection):
        return ['AUTOCOMMIT']

    def get_default_isolation_level(self, dbapi_connection):
        return 'AUTOCOMMIT'

    def get_isolation_level(self, dbapi_connection):
        return 'AUTOCOMMIT'

    def set_isolation_level(self, dbapi_connection, level):
        # ClickHouse has no regular transactional isolation levels.
        pass

    def detect_autocommit_setting(self, dbapi_connection):
        return True

    def do_begin(self, dbapi_connection):
        # SQLAlchemy keeps a transaction lifecycle even in autocommit mode.
        pass

    def do_commit(self, dbapi_connection):
        # ClickHouse statements are committed by the server as they execute.
        pass

    def do_rollback(self, dbapi_connection):
        # No support for transactions.
        pass

    def do_savepoint(self, connection, name):
        raise NotImplementedError('ClickHouse does not support SAVEPOINT')

    def do_rollback_to_savepoint(self, connection, name):
        raise NotImplementedError('ClickHouse does not support SAVEPOINT')

    def do_release_savepoint(self, connection, name):
        raise NotImplementedError('ClickHouse does not support SAVEPOINT')

    def do_executemany(self, cursor, statement, parameters, context=None):
        # render single insert inplace
        if (
            context
            and context.isinsert
            and context.compiled.insert_single_values_expr
            and not len(context.compiled_parameters[0])
        ):
            parameters = None

        statement, parameters = self._prepare_flattened_nested_insert(
            statement, parameters, context, cursor
        )
        cursor.executemany(statement, parameters, context=context)

    def do_execute(self, cursor, statement, parameters, context=None):
        self._remember_flatten_nested_setting(statement, cursor)
        statement, parameters = self._prepare_flattened_nested_insert(
            statement, parameters, context, cursor
        )
        cursor.execute(statement, parameters, context=context)

    def _prepare_flattened_nested_insert(
        self, statement, parameters, context=None, cursor=None
    ):
        if not (context and context.isinsert and parameters):
            return statement, parameters

        compiled = getattr(context, 'compiled', None)
        insert_stmt = getattr(compiled, 'statement', None)
        if insert_stmt is None:
            return statement, parameters

        if (
            getattr(insert_stmt, 'select', None) is not None or
            getattr(insert_stmt, '_values', None)
        ):
            return statement, parameters

        table = getattr(insert_stmt, 'table', None)
        if table is None:
            return statement, parameters

        nested_columns = self._get_nested_insert_columns(table)
        if not nested_columns:
            return statement, parameters

        is_many = isinstance(parameters, (list, tuple))
        rows = parameters if is_many else [parameters]
        if not all(isinstance(row, Mapping) for row in rows):
            return statement, parameters

        if self._flatten_nested_disabled(context, cursor):
            if any(
                column.name in row
                for row in rows
                for column in nested_columns
            ):
                raise NotImplementedError(
                    "flatten_nested=0 insert support is not implemented. "
                    "Use flatten_nested=1 with {'nested': {'child': [...]}} "
                    "or issue raw ClickHouse SQL for unflattened Nested "
                    "payloads."
                )
            return statement, parameters

        expanded = []
        changed = False
        for row in rows:
            expanded_row, row_changed = self._expand_nested_insert_row(
                row, nested_columns
            )
            changed = changed or row_changed
            expanded.append(expanded_row)

        if not changed:
            return statement, parameters

        self._validate_expanded_nested_rows(expanded)
        statement = self._render_flattened_nested_insert(
            table, expanded[0],
            include_values_template=self.renders_insert_values_template
        )
        parameters = expanded if is_many else expanded[0]

        if hasattr(context, 'parameters'):
            context.parameters = parameters
        if hasattr(context, 'compiled_parameters'):
            context.compiled_parameters = expanded

        return statement, parameters

    @staticmethod
    def _get_nested_insert_columns(table):
        cache_key = '_clickhouse_sqlalchemy_nested_insert_columns'
        nested_columns = getattr(table, cache_key, None)
        if nested_columns is None:
            nested_columns = tuple(
                c for c in table.columns if isinstance(c.type, types.Nested)
            )
            setattr(table, cache_key, nested_columns)
        return nested_columns

    @staticmethod
    def _validate_expanded_nested_rows(rows):
        expected = set(rows[0])
        for index, row in enumerate(rows[1:], 2):
            current = set(row)
            if current != expected:
                raise ValueError(
                    "Batch INSERT rows must use the same columns after "
                    "Nested expansion. Row 1 has columns %s, but row %s "
                    "has columns %s."
                    % (
                        sorted(expected),
                        index,
                        sorted(current),
                    )
                )

    def _flatten_nested_disabled(self, context, cursor=None):
        execution_options = getattr(context, 'execution_options', {}) or {}
        settings = execution_options.get('settings') or {}
        option_setting = settings.get('flatten_nested')
        if self._is_false_setting(option_setting):
            return True
        if self._is_true_setting(option_setting):
            return False

        transport_settings = self._get_cursor_ch_settings(cursor)
        transport_setting = transport_settings.get('flatten_nested')
        if self._is_false_setting(transport_setting):
            return True
        if self._is_true_setting(transport_setting):
            return False

        return self._is_false_setting(
            self._get_remembered_flatten_nested_setting(cursor)
        )

    def _remember_flatten_nested_setting(self, statement, cursor):
        if not isinstance(statement, str):
            return

        match = _flatten_nested_set_re.match(statement)
        if match is None:
            return

        connection = self._get_cursor_connection(cursor)
        if connection is None:
            return

        setting = self._find_flatten_nested_set_value(match.group(1))
        if setting is None:
            return

        self._remember_connection_flatten_nested(connection, setting)

    @staticmethod
    def _find_flatten_nested_set_value(settings):
        # This splitter is only used to locate a scalar flatten_nested
        # assignment in a SET list. It is not a full ClickHouse SET parser.
        for item in parse_arguments(settings):
            if '=' not in item:
                continue

            key, value = item.split('=', 1)
            key = key.strip().strip('`"').lower()
            if key == 'flatten_nested':
                return parse_string_literal(value)
        return None

    def _remember_connection_flatten_nested(self, connection, setting):
        try:
            self._flatten_nested_settings[connection] = setting
        except TypeError:
            if not self._warned_flatten_nested_tracking_unavailable:
                warn(
                    "flatten_nested SET tracking is unavailable for this "
                    "driver connection because it cannot be weak-referenced"
                )
                self._warned_flatten_nested_tracking_unavailable = True

    @staticmethod
    def _get_cursor_ch_settings(cursor):
        # HTTP transport stores query settings here. Native/asynch do not;
        # their explicit SET flatten_nested guard is tracked separately.
        connection = ClickHouseDialect._get_cursor_connection(cursor)
        transport = getattr(connection, 'transport', None)
        return getattr(transport, 'ch_settings', {}) or {}

    def _get_remembered_flatten_nested_setting(self, cursor):
        connection = ClickHouseDialect._get_cursor_connection(cursor)
        if connection is None:
            return None

        try:
            setting = self._flatten_nested_settings[connection]
        except (KeyError, TypeError):
            return None
        else:
            return setting

    @staticmethod
    def _get_cursor_connection(cursor):
        return getattr(cursor, '_connection', None)

    @staticmethod
    def _is_false_setting(value):
        # Accept scalar settings with or without SQL string-literal quotes.
        if value is None:
            return False
        if isinstance(value, bool):
            return not value
        if isinstance(value, int):
            return value == 0
        if isinstance(value, str):
            return parse_string_literal(value).strip().lower() in (
                '0', 'false'
            )
        return False

    @staticmethod
    def _is_true_setting(value):
        # Accept scalar settings with or without SQL string-literal quotes.
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return parse_string_literal(value).strip().lower() in (
                '1', 'true'
            )
        return False

    @staticmethod
    def _expand_nested_insert_row(row, nested_columns):
        expanded = dict(row)
        changed = False

        for column in nested_columns:
            if column.name not in expanded:
                continue

            nested_value = expanded[column.name]
            if isinstance(nested_value, (list, tuple)):
                raise NotImplementedError(
                    "Row-oriented Nested payloads are not supported. For "
                    "flatten_nested=1, use {'%s': {'child': [...]}} "
                    "instead. flatten_nested=0 insert support is not "
                    "implemented."
                    % column.name
                )
            if not isinstance(nested_value, Mapping):
                raise TypeError(
                    "Nested column '%s' expects a mapping of child names to "
                    "arrays for flatten_nested=1" % column.name
                )

            changed = True
            expanded.pop(column.name)
            child_names = {child.name for child in column.type.columns}
            provided_names = set(nested_value)
            extra_names = provided_names - child_names
            if extra_names:
                raise ValueError(
                    "Nested column '%s' got unknown child keys %s. "
                    "Expected child keys are %s."
                    % (
                        column.name,
                        sorted(extra_names),
                        sorted(child_names),
                    )
                )
            missing_names = child_names - provided_names
            if missing_names:
                raise ValueError(
                    "Nested column '%s' is missing child keys %s. "
                    "Provided child keys are %s."
                    % (
                        column.name,
                        sorted(missing_names),
                        sorted(provided_names),
                    )
                )
            for child in column.type.columns:
                expanded['%s.%s' % (column.name, child.name)] = (
                    nested_value[child.name]
                )

        return expanded, changed

    def _render_flattened_nested_insert(
        self, table, row, include_values_template
    ):
        # Caller must validate every expanded row has this same key set before
        # using the first row to render the structured INSERT column list.
        # Future ClickHouse-specific INSERT modifiers must be forwarded here.
        preparer = self.identifier_preparer
        columns = []
        binds = []

        for column in table.columns:
            if isinstance(column.type, types.Nested):
                child_keys = [
                    '%s.%s' % (column.name, child.name)
                    for child in column.type.columns
                ]
                if not all(key in row for key in child_keys):
                    continue

                for child in column.type.columns:
                    bind_name = '%s.%s' % (column.name, child.name)
                    columns.append(
                        '%s.%s' % (
                            preparer.quote(column.name),
                            preparer.quote(child.name)
                        )
                    )
                    binds.append('%%(%s)s' % bind_name)
                continue

            if column.name in row:
                columns.append(preparer.format_column(column))
                binds.append('%%(%s)s' % column.name)

        text = 'INSERT INTO %s (%s) VALUES' % (
            preparer.format_table(table), ', '.join(columns)
        )
        if include_values_template:
            text += ' (%s)' % ', '.join(binds)
        return text

    def _check_unicode_returns(self, connection, additional_tests=None):
        return True

    def _check_unicode_description(self, connection):
        return True

    def _get_server_version_info(self, connection):
        version = self.forced_server_version_string

        if version is None:
            version = self._execute(
                connection, 'select version()', scalar=True
            )

        # The first three are numeric, but the last is an alphanumeric build.
        return tuple(int(p) if p.isdigit() else p for p in version.split('.'))

    def _get_default_schema_name(self, connection):
        return self._execute(
            connection, 'select currentDatabase()', scalar=True
        )

    def connect(self, *cargs, **cparams):
        self.forced_server_version_string = cparams.pop(
            'server_version', self.forced_server_version_string)
        return super(ClickHouseDialect, self).connect(*cargs, **cparams)


clickhouse_dialect = ClickHouseDialect()
