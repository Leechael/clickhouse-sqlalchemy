from alembic.autogenerate.api import render_python_code
from alembic.operations import ops
from alembic.operations.ops import CreateTableOp
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Column, MetaData

import clickhouse_sqlalchemy.alembic.dialect  # noqa: F401
from clickhouse_sqlalchemy import Table, engines


def render_ops(*operations):
    context = MigrationContext.configure(dialect_name='clickhouse')
    return render_python_code(
        ops.UpgradeOps(list(operations)),
        migration_context=context,
        user_module_prefix=None
    )


def render_table(table):
    return render_ops(CreateTableOp.from_table(table))


def table_with_type(type_):
    metadata = MetaData()
    return Table(
        'events',
        metadata,
        Column('value', type_),
        engines.Memory()
    )


def assert_migration_python_compiles(rendered):
    compile('def upgrade():\n' + rendered, '<alembic-rendered>', 'exec')
