from sqlalchemy import Column
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from tests.testcase import CompilationTestCase


class IntervalCompilationTestCase(CompilationTestCase):
    def test_interval_day(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalDay),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalDay) ENGINE = Memory'
        )

    def test_interval_week(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalWeek),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalWeek) ENGINE = Memory'
        )

    def test_interval_month(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalMonth),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalMonth) ENGINE = Memory'
        )

    def test_interval_year(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalYear),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalYear) ENGINE = Memory'
        )

    def test_interval_hour(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalHour),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalHour) ENGINE = Memory'
        )

    def test_interval_minute(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalMinute),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalMinute) ENGINE = Memory'
        )

    def test_interval_second(self):
        table = Table(
            'test', CompilationTestCase.metadata(),
            Column('x', types.IntervalSecond),
            engines.Memory()
        )
        self.assertEqual(
            self.compile(CreateTable(table)),
            'CREATE TABLE test (x IntervalSecond) ENGINE = Memory'
        )
