from sqlalchemy import Column

from clickhouse_sqlalchemy import types
from clickhouse_sqlalchemy.alembic import operations
from ._helpers import assert_migration_python_compiles, render_ops


def test_create_materialized_view_renders_clickhouse_columns():
    op = operations.CreateMatViewOp(
        'events_mv',
        'SELECT id FROM events',
        'Memory',
        Column('id', types.UInt64),
        if_not_exists=True,
        on_cluster='cluster1',
        populate=True
    )

    rendered = render_ops(op)

    assert "op.create_mat_view(" in rendered
    assert "'events_mv'" in rendered
    assert "sa.Column('id', clickhouse_sqlalchemy.types.UInt64()" in rendered
    assert_migration_python_compiles(rendered)


def test_attach_materialized_view_renders_clickhouse_columns():
    op = operations.AttachMatViewOp(
        'events_mv',
        'SELECT id FROM events',
        'Memory',
        Column('id', types.UInt64)
    )

    rendered = render_ops(op)

    assert "op.attach_mat_view(" in rendered
    assert "sa.Column('id', clickhouse_sqlalchemy.types.UInt64()" in rendered
    assert_migration_python_compiles(rendered)


def test_materialized_view_storage_table_is_marked_for_exclusion():
    table = type('Model', (), {})()
    table.__table__ = type('TableLike', (), {
        'metadata': type('MetadataLike', (), {'info': {}})(),
        'name': 'events',
        'info': {},
    })()
    mv = type('SelectableLike', (), {})()

    # This covers the marker consumed by include_object() and the schema
    # comparator so autogenerate does not emit storage tables twice.
    from clickhouse_sqlalchemy.sql.schema import MaterializedView
    MaterializedView(table, mv, use_to=True)

    assert table.__table__.info['mv_storage'] is True
