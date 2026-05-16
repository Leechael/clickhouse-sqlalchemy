from alembic.autogenerate.api import compare_metadata
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Column, MetaData, inspect, text
from sqlalchemy.sql.ddl import CreateTable

import clickhouse_sqlalchemy
from clickhouse_sqlalchemy import Table, engines, types
from tests.config import database
from tests.session import native_engine, system_native_session
from tests.testcase import quote_identifier
from ._helpers import render_table


def _reset_database():
    quoted = quote_identifier(database)
    system_native_session.execute(
        text('DROP DATABASE IF EXISTS {}'.format(quoted))
    )
    system_native_session.execute(text('CREATE DATABASE {}'.format(quoted)))


def _compare(metadata, **opts):
    with native_engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={'target_metadata': metadata, **opts}
        )
        return compare_metadata(context, metadata)


def _create(table):
    with native_engine.begin() as connection:
        connection.execute(CreateTable(table))


def test_autogenerate_detects_new_clickhouse_table():
    _reset_database()
    metadata = MetaData()
    table = Table(
        'auto_events',
        metadata,
        Column('id', types.UInt64, nullable=False),
        engines.MergeTree(order_by='id'),
        clickhouse_cluster='cluster1'
    )

    diffs = _compare(metadata)
    rendered = render_table(table)

    assert len(diffs) == 1
    assert diffs[0][0] == 'add_table'
    assert diffs[0][1].name == 'auto_events'
    assert 'clickhouse_sqlalchemy.types.UInt64()' in rendered
    assert "clickhouse_sqlalchemy.engines.MergeTree(order_by='id')" in rendered
    assert "clickhouse_cluster='cluster1'" in rendered


def test_autogenerate_has_no_diff_for_matching_table():
    _reset_database()
    metadata = MetaData()
    table = Table(
        'auto_events',
        metadata,
        Column('id', types.UInt64, nullable=False),
        engines.Memory()
    )
    _create(table)

    assert _compare(metadata) == []


def test_autogenerate_detects_added_clickhouse_column():
    _reset_database()
    existing = MetaData()
    Table(
        'auto_events',
        existing,
        Column('id', types.UInt64, nullable=False),
        engines.Memory()
    )
    _create(existing.tables['auto_events'])

    target = MetaData()
    Table(
        'auto_events',
        target,
        Column('id', types.UInt64, nullable=False),
        Column('name', types.String, nullable=False),
        engines.Memory()
    )

    diffs = _compare(target)

    assert len(diffs) == 1
    assert diffs[0][0] == 'add_column'
    assert diffs[0][3].name == 'name'
    assert isinstance(diffs[0][3].type, types.String)


def test_autogenerate_detects_type_change_when_compare_type_enabled():
    _reset_database()
    existing = MetaData()
    Table(
        'auto_events',
        existing,
        Column('id', types.UInt64, nullable=False),
        engines.Memory()
    )
    _create(existing.tables['auto_events'])

    target = MetaData()
    Table(
        'auto_events',
        target,
        Column('id', types.String, nullable=False),
        engines.Memory()
    )

    diffs = _compare(target, compare_type=True)

    assert len(diffs) == 1
    assert diffs[0][0][0] == 'modify_type'
    assert diffs[0][0][3] == 'id'
    assert isinstance(diffs[0][0][5], types.UInt64)
    assert isinstance(diffs[0][0][6], types.String)


def test_rendered_create_table_migration_executes_and_reflects():
    _reset_database()
    metadata = MetaData()
    table = Table(
        'smoke_events',
        metadata,
        Column('id', types.UInt64, nullable=False),
        Column('created_at', types.DateTime64(3), nullable=False),
        Column('name', types.LowCardinality(types.Nullable(types.String))),
        Column('scores', types.Array(types.UInt32)),
        Column('props', types.Map(types.String, types.UInt64)),
        engines.MergeTree(
            partition_by=text('toYYYYMM(created_at)'),
            order_by='id',
            index_granularity=8192
        )
    )
    rendered = render_table(table)

    with native_engine.begin() as connection:
        context = MigrationContext.configure(connection)
        namespace = {
            'op': Operations(context),
            'sa': __import__('sqlalchemy'),
            'clickhouse_sqlalchemy': clickhouse_sqlalchemy,
        }
        exec('def upgrade():\n' + rendered, namespace)
        namespace['upgrade']()

        reflected = Table(
            'smoke_events',
            MetaData(),
            autoload_with=connection
        )

        assert 'smoke_events' in inspect(connection).get_table_names()
        assert set(reflected.c.keys()) == {
            'id', 'created_at', 'name', 'scores', 'props'
        }
        assert isinstance(reflected.c.id.type, types.UInt64)
        assert isinstance(reflected.engine, engines.MergeTree)
