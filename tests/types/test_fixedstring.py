from sqlalchemy import Column
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from tests.testcase import CompilationTestCase


class FixedStringCompilationTestCase(CompilationTestCase):
    table = Table(
        'test_fixedstring', CompilationTestCase.metadata(),
        Column('x', types.FixedString(10)),
        engines.Memory()
    )

    def test_create_table(self):
        self.assertEqual(
            self.compile(CreateTable(self.table)),
            'CREATE TABLE test_fixedstring '
            '(x FixedString(10)) ENGINE = Memory'
        )
