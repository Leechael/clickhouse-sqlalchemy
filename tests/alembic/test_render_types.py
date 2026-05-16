import enum

import pytest
from sqlalchemy import Column, MetaData
from sqlalchemy.sql.ddl import CreateTable

from clickhouse_sqlalchemy import engines, types
from clickhouse_sqlalchemy.drivers.base import clickhouse_dialect
from clickhouse_sqlalchemy.sql.schema import Table
from ._helpers import (
    assert_migration_python_compiles,
    render_table,
    table_with_type,
)


class RenderEnum(enum.IntEnum):
    first = 1
    second = 2


TYPE_CASES = [
    ('String', types.String(), 'clickhouse_sqlalchemy.types.String()'),
    ('FixedString', types.FixedString(16),
     'clickhouse_sqlalchemy.types.FixedString(16)'),
    ('Int', types.Int(), 'clickhouse_sqlalchemy.types.Int()'),
    ('Float', types.Float(), 'clickhouse_sqlalchemy.types.Float()'),
    ('Boolean', types.Boolean(), 'clickhouse_sqlalchemy.types.Boolean()'),
    ('JSON', types.JSON(), 'clickhouse_sqlalchemy.types.JSON()'),
    ('UUID', types.UUID(), 'clickhouse_sqlalchemy.types.UUID()'),
    ('Int8', types.Int8(), 'clickhouse_sqlalchemy.types.Int8()'),
    ('UInt8', types.UInt8(), 'clickhouse_sqlalchemy.types.UInt8()'),
    ('Int16', types.Int16(), 'clickhouse_sqlalchemy.types.Int16()'),
    ('UInt16', types.UInt16(), 'clickhouse_sqlalchemy.types.UInt16()'),
    ('Int32', types.Int32(), 'clickhouse_sqlalchemy.types.Int32()'),
    ('UInt32', types.UInt32(), 'clickhouse_sqlalchemy.types.UInt32()'),
    ('Int64', types.Int64(), 'clickhouse_sqlalchemy.types.Int64()'),
    ('UInt64', types.UInt64(), 'clickhouse_sqlalchemy.types.UInt64()'),
    ('Int128', types.Int128(), 'clickhouse_sqlalchemy.types.Int128()'),
    ('UInt128', types.UInt128(), 'clickhouse_sqlalchemy.types.UInt128()'),
    ('Int256', types.Int256(), 'clickhouse_sqlalchemy.types.Int256()'),
    ('UInt256', types.UInt256(), 'clickhouse_sqlalchemy.types.UInt256()'),
    ('Float32', types.Float32(), 'clickhouse_sqlalchemy.types.Float32()'),
    ('Float64', types.Float64(), 'clickhouse_sqlalchemy.types.Float64()'),
    ('Date', types.Date(), 'clickhouse_sqlalchemy.types.Date()'),
    ('Date32', types.Date32(), 'clickhouse_sqlalchemy.types.Date32()'),
    ('DateTime', types.DateTime(),
     'clickhouse_sqlalchemy.types.DateTime()'),
    ('DateTimeTZ', types.DateTime(timezone='UTC'),
     "clickhouse_sqlalchemy.types.DateTime(timezone='UTC')"),
    ('DateTime64', types.DateTime64(3),
     'clickhouse_sqlalchemy.types.DateTime64(3)'),
    ('DateTime64TZ', types.DateTime64(6, timezone='UTC'),
     "clickhouse_sqlalchemy.types.DateTime64(6, timezone='UTC')"),
    ('Decimal', types.Decimal(10, 2),
     'clickhouse_sqlalchemy.types.Decimal(10, 2)'),
    ('Decimal32', types.Decimal32(2),
     'clickhouse_sqlalchemy.types.Decimal32(2)'),
    ('Decimal64', types.Decimal64(4),
     'clickhouse_sqlalchemy.types.Decimal64(4)'),
    ('Decimal128', types.Decimal128(8),
     'clickhouse_sqlalchemy.types.Decimal128(8)'),
    ('Decimal256', types.Decimal256(12),
     'clickhouse_sqlalchemy.types.Decimal256(12)'),
    ('Enum', types.Enum('a', 'b'),
     "clickhouse_sqlalchemy.types.Enum('a', 'b')"),
    ('Enum8', types.Enum8('a', 'b'),
     "clickhouse_sqlalchemy.types.Enum8('a', 'b')"),
    ('Enum16', types.Enum16('a', 'b'),
     "clickhouse_sqlalchemy.types.Enum16('a', 'b')"),
    ('Enum8Class', types.Enum8(RenderEnum),
     'clickhouse_sqlalchemy.types.Enum8('
     'tests.alembic.test_render_types.RenderEnum)'),
    ('IPv4', types.IPv4(), 'clickhouse_sqlalchemy.types.IPv4()'),
    ('IPv6', types.IPv6(), 'clickhouse_sqlalchemy.types.IPv6()'),
    ('Array', types.Array(types.UInt64),
     'clickhouse_sqlalchemy.types.Array('
     'clickhouse_sqlalchemy.types.UInt64())'),
    ('Nullable', types.Nullable(types.String),
     'clickhouse_sqlalchemy.types.Nullable('
     'clickhouse_sqlalchemy.types.String())'),
    ('LowCardinality', types.LowCardinality(types.String),
     'clickhouse_sqlalchemy.types.LowCardinality('
     'clickhouse_sqlalchemy.types.String())'),
    ('Tuple', types.Tuple(types.String, types.UInt64),
     'clickhouse_sqlalchemy.types.Tuple('
     'clickhouse_sqlalchemy.types.String(), '
     'clickhouse_sqlalchemy.types.UInt64())'),
    ('NamedTuple',
     types.Tuple(('name', types.String), ('value', types.UInt64)),
     "clickhouse_sqlalchemy.types.Tuple("
     "('name', clickhouse_sqlalchemy.types.String()), "
     "('value', clickhouse_sqlalchemy.types.UInt64()))"),
    ('Map', types.Map(types.String, types.UInt64),
     'clickhouse_sqlalchemy.types.Map('
     'clickhouse_sqlalchemy.types.String(), '
     'clickhouse_sqlalchemy.types.UInt64())'),
    ('DeepComposite',
     types.Array(types.Nullable(types.LowCardinality(types.String))),
     'clickhouse_sqlalchemy.types.Array('
     'clickhouse_sqlalchemy.types.Nullable('
     'clickhouse_sqlalchemy.types.LowCardinality('
     'clickhouse_sqlalchemy.types.String())))'),
    ('AggregateFunction', types.AggregateFunction('sum', types.UInt64),
     "clickhouse_sqlalchemy.types.AggregateFunction("
     "'sum', clickhouse_sqlalchemy.types.UInt64())"),
    ('SimpleAggregateFunction',
     types.SimpleAggregateFunction('sum', types.UInt64),
     "clickhouse_sqlalchemy.types.SimpleAggregateFunction("
     "'sum', clickhouse_sqlalchemy.types.UInt64())"),
    ('Nested',
     types.Nested(Column('x', types.UInt64), Column('y', types.String)),
     "clickhouse_sqlalchemy.types.Nested("
     "sa.Column('x', clickhouse_sqlalchemy.types.UInt64()), "
     "sa.Column('y', clickhouse_sqlalchemy.types.String()))"),
    ('IntervalDay', types.IntervalDay(),
     'clickhouse_sqlalchemy.types.IntervalDay()'),
    ('IntervalWeek', types.IntervalWeek(),
     'clickhouse_sqlalchemy.types.IntervalWeek()'),
    ('IntervalMonth', types.IntervalMonth(),
     'clickhouse_sqlalchemy.types.IntervalMonth()'),
    ('IntervalYear', types.IntervalYear(),
     'clickhouse_sqlalchemy.types.IntervalYear()'),
    ('IntervalHour', types.IntervalHour(),
     'clickhouse_sqlalchemy.types.IntervalHour()'),
    ('IntervalMinute', types.IntervalMinute(),
     'clickhouse_sqlalchemy.types.IntervalMinute()'),
    ('IntervalSecond', types.IntervalSecond(),
     'clickhouse_sqlalchemy.types.IntervalSecond()'),
    ('IntervalNanosecond', types.IntervalNanosecond(),
     'clickhouse_sqlalchemy.types.IntervalNanosecond()'),
    ('IntervalMicrosecond', types.IntervalMicrosecond(),
     'clickhouse_sqlalchemy.types.IntervalMicrosecond()'),
    ('IntervalMillisecond', types.IntervalMillisecond(),
     'clickhouse_sqlalchemy.types.IntervalMillisecond()'),
    ('IntervalQuarter', types.IntervalQuarter(),
     'clickhouse_sqlalchemy.types.IntervalQuarter()'),
    ('Nothing', types.Nothing(), 'clickhouse_sqlalchemy.types.Nothing()'),
    ('Null', types.Null(), 'clickhouse_sqlalchemy.types.Null()'),
]


@pytest.mark.parametrize(
    'name,type_,expected',
    TYPE_CASES,
    ids=[case[0] for case in TYPE_CASES]
)
def test_clickhouse_column_type_renders_as_public_type(name, type_, expected):
    rendered = render_table(table_with_type(type_))

    assert expected in rendered
    assert 'clickhouse_sqlalchemy.types.common' not in rendered
    assert 'clickhouse_sqlalchemy.types.ip' not in rendered
    assert_migration_python_compiles(rendered)


def test_all_public_clickhouse_types_are_covered_by_render_tests():
    covered = {name for name, _type, _expected in TYPE_CASES}
    public_types = {
        name for name in types.__all__
        if isinstance(getattr(types, name), type)
    }

    assert public_types <= covered


def test_string_enum_rendering_is_documented_as_compile_unsupported():
    table = Table(
        'events',
        MetaData(),
        Column('status', types.Enum8('new', 'done')),
        engines.Memory()
    )

    with pytest.raises(TypeError):
        CreateTable(table).compile(dialect=clickhouse_dialect)
