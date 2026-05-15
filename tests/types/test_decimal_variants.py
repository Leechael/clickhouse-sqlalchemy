from unittest import TestCase

from sqlalchemy import Column
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import types, engines, Table
from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect
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


class DecimalVariantReflectionTestCase(TestCase):
    def setUp(self):
        self.dialect = ClickHouseDialect()

    def _assert_reflects_canonical_decimal(self, spec, expected_precision, expected_scale):
        coltype = self.dialect._get_column_type('x', spec)

        self.assertIsInstance(coltype, types.Decimal)
        self.assertNotIsInstance(coltype, (
            types.Decimal32,
            types.Decimal64,
            types.Decimal128,
            types.Decimal256,
        ))
        self.assertEqual(coltype.precision, expected_precision)
        self.assertEqual(coltype.scale, expected_scale)

    def test_reflect_decimal32_as_clickhouse_canonical_precision(self):
        self._assert_reflects_canonical_decimal('Decimal(9, 2)', 9, 2)

    def test_reflect_decimal64_as_clickhouse_canonical_precision(self):
        self._assert_reflects_canonical_decimal('Decimal(18, 4)', 18, 4)

    def test_reflect_decimal128_as_clickhouse_canonical_precision(self):
        self._assert_reflects_canonical_decimal('Decimal(38, 6)', 38, 6)

    def test_reflect_decimal256_as_clickhouse_canonical_precision(self):
        self._assert_reflects_canonical_decimal('Decimal(76, 8)', 76, 8)
