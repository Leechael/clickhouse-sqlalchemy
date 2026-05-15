from sqlalchemy import Column
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from tests.testcase import CompilationTestCase


class NothingCompilationTestCase(CompilationTestCase):
    table = Table(
        'test', CompilationTestCase.metadata(),
        Column('x', types.Nothing),
        engines.Memory()
    )

    def test_create_table(self):
        self.assertEqual(
            self.compile(CreateTable(self.table)),
            'CREATE TABLE test (x Nothing) ENGINE = Memory'
        )
