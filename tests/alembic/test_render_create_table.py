import pytest
from sqlalchemy import Column, MetaData, func, text
from sqlalchemy.sql.ddl import CreateTable
from alembic.operations.ops import CreateTableOp

from clickhouse_sqlalchemy import Table, engines, types
from clickhouse_sqlalchemy.drivers.base import clickhouse_dialect
from ._helpers import assert_migration_python_compiles, render_ops, render_table


def _table(engine, *columns, **kwargs):
    metadata = MetaData()
    base_columns = [
        Column('id', types.UInt64),
        Column('dt', types.DateTime),
        Column('sign', types.Int8),
        Column('version', types.UInt64),
        Column('value', types.UInt64),
    ]
    return Table(
        'events',
        metadata,
        *(base_columns + list(columns) + [engine]),
        **kwargs
    )


ENGINE_CASES = [
    (engines.Memory(), 'clickhouse_sqlalchemy.engines.Memory()'),
    (engines.Log(), 'clickhouse_sqlalchemy.engines.Log()'),
    (engines.TinyLog(), 'clickhouse_sqlalchemy.engines.TinyLog()'),
    (engines.MergeTree(order_by='id'),
     "clickhouse_sqlalchemy.engines.MergeTree(order_by='id')"),
    (engines.MergeTree(
        partition_by=text('toYYYYMM(dt)'),
        order_by=('id', 'dt'),
        primary_key='id',
        sample_by='id',
        ttl=text('dt + INTERVAL 1 DAY'),
        index_granularity=8192
    ),
     "clickhouse_sqlalchemy.engines.MergeTree("
     "partition_by=sa.text('toYYYYMM(dt)'), "
     "order_by=('id', 'dt',), primary_key='id', sample_by='id', "
     "ttl=sa.text('dt + INTERVAL 1 DAY'), index_granularity=8192)"),
    (engines.ReplacingMergeTree(version='version', order_by='id'),
     "clickhouse_sqlalchemy.engines.ReplacingMergeTree("
     "version='version', order_by='id')"),
    (engines.SummingMergeTree(columns=('value',), order_by='id'),
     "clickhouse_sqlalchemy.engines.SummingMergeTree("
     "columns='value', order_by='id')"),
    (engines.AggregatingMergeTree(order_by='id'),
     "clickhouse_sqlalchemy.engines.AggregatingMergeTree(order_by='id')"),
    (engines.CollapsingMergeTree('sign', order_by='id'),
     "clickhouse_sqlalchemy.engines.CollapsingMergeTree("
     "'sign', order_by='id')"),
    (engines.VersionedCollapsingMergeTree('sign', 'version', order_by='id'),
     "clickhouse_sqlalchemy.engines.VersionedCollapsingMergeTree("
     "'sign', 'version', order_by='id')"),
    (engines.ReplicatedMergeTree('/clickhouse/{shard}', '{replica}',
                                 order_by='id'),
     "clickhouse_sqlalchemy.engines.ReplicatedMergeTree("
     "'/clickhouse/{shard}', '{replica}', order_by='id')"),
    (engines.Distributed('cluster', 'db', 'events', 'rand()'),
     "clickhouse_sqlalchemy.engines.Distributed("
     "'cluster', 'db', 'events', 'rand()')"),
    (engines.Buffer('db', 'events', 1, 2, 3, 4, 5, 6, 7),
     "clickhouse_sqlalchemy.engines.Buffer("
     "'db', 'events', 1, 2, 3, 4, 5, 6, 7)"),
]


@pytest.mark.parametrize(
    'engine,expected',
    ENGINE_CASES,
    ids=[case[0].__class__.__name__ for case in ENGINE_CASES]
)
def test_create_table_renders_clickhouse_engines(engine, expected):
    rendered = render_table(_table(engine))

    assert expected in rendered
    assert '{}()'.format(engine.__class__.__name__) not in rendered or (
        expected.endswith('{}()'.format(engine.__class__.__name__))
    )
    assert_migration_python_compiles(rendered)


def test_create_table_renders_column_attributes_and_table_options():
    table = _table(
        engines.MergeTree(order_by='id'),
        Column(
            'materialized_at',
            types.DateTime,
            clickhouse_materialized=func.now(),
            clickhouse_codec=('DoubleDelta', 'ZSTD'),
            comment='materialized timestamp'
        ),
        Column(
            'alias_id',
            types.UInt64,
            clickhouse_alias=text('id'),
            clickhouse_after=text('id')
        ),
        clickhouse_cluster='cluster1',
        schema='analytics',
        comment='events table',
        info={'owner': 'tests'}
    )

    rendered = render_table(table)
    ddl = str(CreateTable(table).compile(dialect=clickhouse_dialect))

    assert "schema='analytics'" in rendered
    assert "comment='events table'" in rendered
    assert "info={'owner': 'tests'}" in rendered
    assert "clickhouse_cluster='cluster1'" in rendered
    assert "clickhouse_materialized=sa.text('now()')" in rendered
    assert "clickhouse_alias=sa.text('id')" in rendered
    assert "clickhouse_after=sa.text('id')" in rendered
    assert "clickhouse_codec=('DoubleDelta', 'ZSTD')" in rendered
    assert 'ON CLUSTER cluster1' in ddl
    assert 'ENGINE = MergeTree()' in ddl
    assert_migration_python_compiles(rendered)


def test_create_table_renders_type_engine_and_cluster_together():
    table = _table(
        engines.MergeTree(order_by='id'),
        Column('payload', types.Nullable(types.LowCardinality(types.String))),
        clickhouse_cluster='cluster1'
    )

    rendered = render_table(table)

    assert (
        'clickhouse_sqlalchemy.types.Nullable('
        'clickhouse_sqlalchemy.types.LowCardinality('
        'clickhouse_sqlalchemy.types.String()))'
    ) in rendered
    assert "clickhouse_sqlalchemy.engines.MergeTree(order_by='id')" in rendered
    assert "clickhouse_cluster='cluster1'" in rendered
    assert (
        rendered.index('clickhouse_sqlalchemy.types.Nullable')
        < rendered.index('clickhouse_sqlalchemy.engines.MergeTree')
        < rendered.index('clickhouse_cluster')
    )
    assert_migration_python_compiles(rendered)


def test_create_table_renders_if_not_exists():
    table = _table(engines.Memory())
    op = CreateTableOp.from_table(table)
    op.if_not_exists = True

    rendered = render_ops(op)

    assert 'if_not_exists=True' in rendered
    assert_migration_python_compiles(rendered)
