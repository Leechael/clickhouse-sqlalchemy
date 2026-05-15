from sqlalchemy import Column
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from tests.testcase import CompilationTestCase


class Decimal32CompilationTestCase(CompilationTestCase):
    table = Table(
        'test_decimal32', CompilationTestCase.metadata(),
        Column('x', types.Decimal32(2)),
        engines.Memory()
    )

    def test_create_table(self):
        self.assertEqual(
            self.compile(CreateTable(self.table)),
            'CREATE TABLE test_decimal32 '
            '(x Decimal32(2)) ENGINE = Memory'
        )


class Decimal64CompilationTestCase(CompilationTestCase):
    table = Table(
        'test_decimal64', CompilationTestCase.metadata(),
        Column('x', types.Decimal64(4)),
        engines.Memory()
    )

    def test_create_table(self):
        self.assertEqual(
            self.compile(CreateTable(self.table)),
            'CREATE TABLE test_decimal64 '
            '(x Decimal64(4)) ENGINE = Memory'
        )


class Decimal128CompilationTestCase(CompilationTestCase):
    table = Table(
        'test_decimal128', CompilationTestCase.metadata(),
        Column('x', types.Decimal128(6)),
        engines.Memory()
    )

    def test_create_table(self):
        self.assertEqual(
            self.compile(CreateTable(self.table)),
            'CREATE TABLE test_decimal128 '
            '(x Decimal128(6)) ENGINE = Memory'
        )


class Decimal256CompilationTestCase(CompilationTestCase):
    table = Table(
        'test_decimal256', CompilationTestCase.metadata(),
        Column('x', types.Decimal256(8)),
        engines.Memory()
    )

    def test_create_table(self):
        self.assertEqual(
            self.compile(CreateTable(self.table)),
            'CREATE TABLE test_decimal256 '
            '(x Decimal256(8)) ENGINE = Memory'
        )
