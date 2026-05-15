from unittest import TestCase

import re

from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect
from clickhouse_sqlalchemy.drivers.base import clickhouse_dialect


class FixedStringCompilationTestCase(TestCase):
    table = Table(
        'test_fixedstring', MetaData(),
        Column('x', types.FixedString(10)),
        engines.Memory()
    )

    def compile(self, clause):
        return re.sub(
            r'\s+', ' ', str(clause.compile(dialect=clickhouse_dialect))
        ).strip()

    def test_create_table(self):
        ddl = self.compile(CreateTable(self.table))

        self.assertIn('x FixedString(10)', ddl)
        self.assertIn('ENGINE = Memory', ddl)

    def test_reflect_fixedstring(self):
        coltype = ClickHouseDialect()._get_column_type('x', 'FixedString(10)')

        self.assertIsInstance(coltype, types.FixedString)
        self.assertEqual(coltype.length, 10)
