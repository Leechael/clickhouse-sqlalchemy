from unittest import TestCase

from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy.exc import CompileError
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from clickhouse_sqlalchemy.drivers.base import clickhouse_dialect


class NullCompilationTestCase(TestCase):
    table = Table(
        'test', MetaData(),
        Column('x', types.Null),
        engines.Memory()
    )

    def test_create_table_rejects_null_column(self):
        with self.assertRaises(CompileError):
            CreateTable(self.table).compile(dialect=clickhouse_dialect)
