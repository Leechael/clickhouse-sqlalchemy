from unittest import TestCase

import re

from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect
from clickhouse_sqlalchemy.drivers.base import clickhouse_dialect


INTERVAL_TYPE_NAMES = [
    'IntervalNanosecond',
    'IntervalMicrosecond',
    'IntervalMillisecond',
    'IntervalSecond',
    'IntervalMinute',
    'IntervalHour',
    'IntervalDay',
    'IntervalWeek',
    'IntervalMonth',
    'IntervalQuarter',
    'IntervalYear',
]


class IntervalCompilationTestCase(TestCase):
    def compile(self, clause):
        return re.sub(
            r'\s+', ' ', str(clause.compile(dialect=clickhouse_dialect))
        ).strip()

    def test_create_table_for_all_clickhouse_interval_types(self):
        for type_name in INTERVAL_TYPE_NAMES:
            with self.subTest(type_name=type_name):
                interval_type = getattr(types, type_name)
                table = Table(
                    'test', MetaData(),
                    Column('x', interval_type),
                    engines.Memory()
                )

                ddl = self.compile(CreateTable(table))

                self.assertIn('x %s' % type_name, ddl)
                self.assertIn('ENGINE = Memory', ddl)


class IntervalReflectionTestCase(TestCase):
    def setUp(self):
        self.dialect = ClickHouseDialect()

    def test_reflect_all_clickhouse_interval_types(self):
        for type_name in INTERVAL_TYPE_NAMES:
            with self.subTest(type_name=type_name):
                coltype = self.dialect._get_column_type('x', type_name)

                self.assertIs(coltype, getattr(types, type_name))
