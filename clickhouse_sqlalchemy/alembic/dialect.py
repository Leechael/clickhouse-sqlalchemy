from sqlalchemy import func, Column, MetaData, Table, types as sqltypes
from sqlalchemy.sql.type_api import to_instance

try:
    from alembic.ddl import impl
    from alembic.ddl.base import (
        compiles, ColumnComment, format_table_name, format_column_name
    )
except ImportError:
    raise RuntimeError('alembic must be installed')

from clickhouse_sqlalchemy import types, engines
from clickhouse_sqlalchemy.sql.ddl import DropTable
from .comparators import compare_mat_view
from .renderers import (
    render_attach_mat_view, render_detach_mat_view,
    render_create_mat_view, render_drop_mat_view
)
from .toimpl import (
    create_mat_view, attach_mat_view
)


class ClickHouseDialectImpl(impl.DefaultImpl):
    __dialect__ = 'clickhouse'
    transactional_ddl = False

    type_prefix = 'clickhouse_sqlalchemy.types.'

    def version_table_impl(
            self, *, version_table, version_table_schema, version_table_pk,
            **kwargs
    ):
        dt = Column('dt', types.DateTime, server_default=func.now())
        version = Table(
            version_table,
            MetaData(),
            dt,
            Column(
                'version_num', types.String, primary_key=version_table_pk
            ),
            schema=version_table_schema
        )
        version.engine = engines.ReplacingMergeTree(
            version=dt, order_by=func.tuple()
        )
        return version

    def render_type(self, type_obj, autogen_context):
        rendered = self._render_clickhouse_type(type_obj)
        if rendered is None:
            return False
        return rendered

    def _render_clickhouse_type(self, type_obj):
        type_obj = to_instance(type_obj)
        cls = type_obj.__class__
        name = cls.__name__

        if isinstance(type_obj, types.Array):
            return '{}Array({})'.format(
                self.type_prefix,
                self._render_clickhouse_type(type_obj.item_type_impl)
            )

        if isinstance(type_obj, types.Nullable):
            return '{}Nullable({})'.format(
                self.type_prefix,
                self._render_clickhouse_type(type_obj.nested_type)
            )

        if isinstance(type_obj, types.LowCardinality):
            return '{}LowCardinality({})'.format(
                self.type_prefix,
                self._render_clickhouse_type(type_obj.nested_type)
            )

        if isinstance(type_obj, types.Tuple):
            rendered = []
            for nested_type in type_obj.nested_types:
                if isinstance(nested_type, tuple) and len(nested_type) == 2:
                    rendered.append(
                        '({!r}, {})'.format(
                            nested_type[0],
                            self._render_clickhouse_type(nested_type[1])
                        )
                    )
                else:
                    rendered.append(self._render_clickhouse_type(nested_type))
            return '{}Tuple({})'.format(self.type_prefix, ', '.join(rendered))

        if isinstance(type_obj, types.Map):
            return '{}Map({}, {})'.format(
                self.type_prefix,
                self._render_clickhouse_type(type_obj.key_type),
                self._render_clickhouse_type(type_obj.value_type)
            )

        if isinstance(type_obj, types.AggregateFunction):
            return self._render_aggregate_function_type(
                'AggregateFunction', type_obj
            )

        if isinstance(type_obj, types.SimpleAggregateFunction):
            return self._render_aggregate_function_type(
                'SimpleAggregateFunction', type_obj
            )

        if isinstance(type_obj, types.Nested):
            columns = [
                'sa.Column({!r}, {})'.format(
                    column.name,
                    self._render_clickhouse_type(column.type)
                )
                for column in type_obj.columns
            ]
            return '{}Nested({})'.format(self.type_prefix, ', '.join(columns))

        if isinstance(type_obj, types.DateTime64):
            args = [repr(type_obj.precision)]
            if type_obj.timezone is not None:
                args.append('timezone={!r}'.format(type_obj.timezone))
            return '{}DateTime64({})'.format(
                self.type_prefix, ', '.join(args)
            )

        if isinstance(type_obj, types.DateTime):
            args = []
            if type_obj.timezone is not None:
                args.append('timezone={!r}'.format(type_obj.timezone))
            return '{}DateTime({})'.format(self.type_prefix, ', '.join(args))

        if isinstance(type_obj, types.FixedString):
            return '{}FixedString({!r})'.format(
                self.type_prefix, type_obj.length
            )

        if cls is types.Decimal:
            return '{}Decimal({!r}, {!r})'.format(
                self.type_prefix, type_obj.precision, type_obj.scale
            )

        if isinstance(type_obj, (
                types.Decimal32, types.Decimal64,
                types.Decimal128, types.Decimal256
        )):
            return '{}{}({!r})'.format(
                self.type_prefix, name, type_obj.scale
            )

        if isinstance(type_obj, (types.Enum8, types.Enum16, types.Enum)):
            if type_obj.enum_class is not None:
                return '{}{}({})'.format(
                    self.type_prefix,
                    name,
                    '{}.{}'.format(
                        type_obj.enum_class.__module__,
                        type_obj.enum_class.__name__
                    )
                )
            return '{}{}({})'.format(
                self.type_prefix,
                name,
                ', '.join(repr(enum) for enum in type_obj.enums)
            )

        simple_types = (
            types.String, types.Int, types.Float, types.Boolean, types.JSON,
            types.UUID, types.Int8, types.UInt8, types.Int16, types.UInt16,
            types.Int32, types.UInt32, types.Int64, types.UInt64,
            types.Int128, types.UInt128, types.Int256, types.UInt256,
            types.Float32, types.Float64, types.Date, types.Date32,
            types.IPv4, types.IPv6, types.IntervalDay, types.IntervalWeek,
            types.IntervalMonth, types.IntervalYear, types.IntervalHour,
            types.IntervalMinute, types.IntervalSecond,
            types.IntervalNanosecond, types.IntervalMicrosecond,
            types.IntervalMillisecond, types.IntervalQuarter, types.Nothing,
            types.Null
        )
        if isinstance(type_obj, simple_types):
            return '{}{}()'.format(self.type_prefix, name)

        return None

    def _render_aggregate_function_type(self, name, type_obj):
        nested = ', '.join(
            self._render_clickhouse_type(nested_type)
            for nested_type in type_obj.nested_types
        )
        args = [repr(type_obj.agg_func)]
        if nested:
            args.append(nested)
        return '{}{}({})'.format(self.type_prefix, name, ', '.join(args))

    def drop_table(self, table):
        table.dispatch.before_drop(
            table, self.connection, checkfirst=False, _ddl_runner=self
        )

        self._exec(DropTable(table))

        table.dispatch.after_drop(
            table, self.connection, checkfirst=False, _ddl_runner=self
        )


def patch_alembic_version(context, **kwargs):
    migration_context = context._proxy._migration_context
    version = migration_context._version

    dt = Column('dt', types.DateTime, server_default=func.now())
    version_num = Column('version_num', types.String, primary_key=True)
    version.append_column(dt)
    version.append_column(version_num, replace_existing=True)

    if 'cluster' in kwargs:
        cluster = kwargs['cluster']
        version.engine = engines.ReplicatedReplacingMergeTree(
            kwargs['table_path'], kwargs['replica_name'],
            version=dt, order_by=func.tuple()
        )
        version.kwargs['clickhouse_cluster'] = cluster
    else:
        version.engine = engines.ReplacingMergeTree(
            version=dt, order_by=func.tuple()
        )


def include_object(object, name, type_, reflected, compare_to):
    # skip inner matview tables in autogeneration.
    if type_ == 'table' and object.info.get('mv_storage'):
        return False

    return True


@compiles(ColumnComment, 'clickhouse')
def visit_column_comment(element, compiler, **kw):
    ddl = "ALTER TABLE {table_name} COMMENT COLUMN {column_name} {comment}"
    comment = (
        compiler.sql_compiler.render_literal_value(
            element.comment or '', sqltypes.String()
        )
    )

    return ddl.format(
        table_name=format_table_name(
            compiler, element.table_name, element.schema
        ),
        column_name=format_column_name(compiler, element.column_name),
        comment=comment,
    )


__all__ = (
    'ClickHouseDialectImpl', 'compare_mat_view',
    'render_attach_mat_view', 'render_detach_mat_view',
    'render_create_mat_view', 'render_drop_mat_view',
    'create_mat_view', 'attach_mat_view'
)
