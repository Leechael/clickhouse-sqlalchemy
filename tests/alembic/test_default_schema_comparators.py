from alembic.autogenerate.api import AutogenContext, render_python_code
from alembic.autogenerate import comparators
from alembic.operations import ops
from alembic.operations.ops import CreateTableOp
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Column, MetaData

import clickhouse_sqlalchemy.alembic.dialect
from clickhouse_sqlalchemy import Table, engines, types
from clickhouse_sqlalchemy.alembic.comparators import compare_mat_view


def _registry_functions(dispatcher, target, qualifier):
    functions = []
    for key, registered in dispatcher._registry.items():
        if key[0] != target or key[1] != qualifier:
            continue
        for item in registered:
            if isinstance(item, tuple):
                fn, _subgroup = item
            else:
                fn = item
            functions.append(fn)
    return functions


def test_clickhouse_alembic_impl_imports_with_current_alembic():
    context = MigrationContext.configure(dialect_name='clickhouse')

    assert (
        context.impl.__class__
        is clickhouse_sqlalchemy.alembic.dialect.ClickHouseDialectImpl
    )


def test_clickhouse_schema_comparator_keeps_default_table_comparator():
    context = MigrationContext.configure(
        dialect_name='clickhouse',
        opts={'target_metadata': MetaData()}
    )
    autogen_context = AutogenContext(context, metadata=MetaData())

    dispatcher = getattr(autogen_context, 'comparators', comparators)
    default_schema = _registry_functions(dispatcher, 'schema', 'default')
    clickhouse_schema = _registry_functions(dispatcher, 'schema', 'clickhouse')

    assert default_schema
    assert compare_mat_view in clickhouse_schema


def test_version_table_uses_clickhouse_engine():
    context = MigrationContext.configure(dialect_name='clickhouse')
    version = context._version

    assert 'version_num' in version.c
    assert 'dt' in version.c
    assert isinstance(version.engine, engines.ReplacingMergeTree)


def test_create_table_autogenerate_renders_clickhouse_engine():
    metadata = MetaData()
    table = Table(
        'events',
        metadata,
        Column('id', types.UInt64),
        engines.MergeTree(order_by='id'),
        clickhouse_cluster='cluster1'
    )
    operation = CreateTableOp.from_table(table)
    context = MigrationContext.configure(dialect_name='clickhouse')

    rendered = render_python_code(
        ops.UpgradeOps([operation]),
        migration_context=context,
        user_module_prefix=None
    )

    assert "clickhouse_sqlalchemy.engines.MergeTree(order_by='id')" in rendered
    assert "clickhouse_cluster='cluster1'" in rendered
    assert (
        rendered.index("clickhouse_sqlalchemy.engines.MergeTree")
        < rendered.index("clickhouse_cluster")
    )
