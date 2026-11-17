import os
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from clickhouse_sqlalchemy import Table
from clickhouse_sqlalchemy import engines
from clickhouse_sqlalchemy import types as ch_types


def _load_dotenv_test():
    candidates = []
    explicit = os.environ.get("TEST_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        parent / ".env.test" for parent in (Path.cwd(), *Path.cwd().parents)
    )
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _clickhouse_url():
    _load_dotenv_test()
    return os.environ.get(
        "TEST_CLICKHOUSE_URL",
        "clickhouse+asynch://default:@127.0.0.1:9000/default",
    )


def _engine():
    return create_async_engine(
        _clickhouse_url(),
        connect_args={
            "settings": {
                "async_insert": 1,
                "wait_for_async_insert": 1,
            },
        },
    )


def _table_name(prefix):
    return f"test_ch_compat_{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_datetime64_textual_insert_preserves_millisecond_precision():
    """DateTime64(3) values bound via text() keep sub-second precision."""
    table = _table_name("dt64_precision")
    engine = _engine()
    value = datetime(2026, 1, 1, 0, 0, 0, 123000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        ts DateTime64(3)
                    )
                    ENGINE = MergeTree
                    ORDER BY id
                    """
                )
            )
            await conn.execute(
                text(f"INSERT INTO {table} (id, ts) VALUES (:id, :ts)"),
                {"id": 1, "ts": value},
            )

            result = await conn.execute(
                text(f"SELECT ts FROM {table} WHERE id = :id"),
                {"id": 1},
            )
            row = result.one()
            assert row.ts.microsecond == 123000
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()


@pytest.mark.asyncio
async def test_datetime_textual_insert_does_not_append_zero_fraction():
    """Plain DateTime bound via text() stays at second precision."""
    table = _table_name("dt_precision")
    engine = _engine()
    value = datetime(2026, 1, 1, 0, 0, 0)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        ts DateTime
                    )
                    ENGINE = MergeTree
                    ORDER BY id
                    """
                )
            )
            await conn.execute(
                text(f"INSERT INTO {table} (id, ts) VALUES (:id, :ts)"),
                {"id": 1, "ts": value},
            )

            result = await conn.execute(
                text(f"SELECT ts FROM {table} WHERE id = :id"),
                {"id": 1},
            )
            row = result.one()
            assert row.ts.microsecond == 0
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()


UTC = timezone.utc
SECOND = datetime(2026, 1, 1, tzinfo=UTC)
MILLIS = datetime(2026, 1, 1, 0, 0, 0, 123000, tzinfo=UTC)

# ``aware`` is what a column without a zone of its own should hand back:
# aware UTC when the setting is on, naive server wall time when it is off.
ENGINE_CASES = pytest.mark.parametrize(
    "settings,query,aware",
    [
        pytest.param({"datetime_as_utc": True}, None, True,
                     id="connect_args_true"),
        pytest.param(None, {"datetime_as_utc": "true"}, True, id="dsn_true"),
        pytest.param(None, None, False, id="default_off"),
        pytest.param({"datetime_as_utc": False}, None, False,
                     id="connect_args_false"),
        pytest.param(None, {"datetime_as_utc": "false"}, False,
                     id="dsn_false"),
    ],
)


def _engine_with(settings=None, query=None):
    url = make_url(_clickhouse_url())
    if query:
        url = url.update_query_dict(query)

    connect_settings = {"async_insert": 1, "wait_for_async_insert": 1}
    connect_settings.update(settings or {})
    connect_args = {"settings": connect_settings}
    return create_async_engine(url, connect_args=connect_args)


def _proto_connection(conn):
    driver_connection = conn.sync_connection.connection.driver_connection
    return driver_connection._connection._connection


async def _server_zone(conn):
    zone = (await conn.execute(text("SELECT timezone()"))).scalar_one()
    return ZoneInfo(zone)


async def _count(conn, table, where, value):
    selected = text(f"SELECT count() FROM {table} WHERE {where}")
    return (await conn.execute(selected, {"v": value})).scalar_one()


async def _server_setting(conn, name):
    selected = text("SELECT value FROM system.settings WHERE name = :name")
    return (await conn.execute(selected, {"name": name})).scalar()


def _expected(instant, zone, aware):
    if aware:
        return instant.astimezone(UTC)
    return instant.astimezone(zone).replace(tzinfo=None)


def _assert_matches(value, expected, aware):
    assert value == expected
    if aware:
        assert value.utcoffset() == timedelta(0)
    else:
        assert value.tzinfo is None


@pytest.mark.asyncio
@ENGINE_CASES
async def test_datetime_as_utc_decides_read_awareness(settings, query, aware):
    table = _table_name("dt_aware")
    engine = _engine_with(settings, query)
    typed = Table(
        table,
        MetaData(),
        Column("dt", ch_types.DateTime),
        Column("dt64", ch_types.DateTime64(3)),
        Column("arr", ch_types.Array(ch_types.DateTime64(3))),
        Column("tup", ch_types.Tuple(ch_types.DateTime64(3), ch_types.String)),
    )

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        dt DateTime,
                        dt64 DateTime64(3),
                        arr Array(DateTime64(3)),
                        tup Tuple(DateTime64(3), String),
                        tz_dt DateTime('Asia/Shanghai'),
                        tz_dt64 DateTime64(3, 'Asia/Shanghai')
                    ) ENGINE = MergeTree ORDER BY id
                    """
                )
            )
            await conn.execute(
                text(
                    f"INSERT INTO {table} "
                    "(id, dt, dt64, arr, tup, tz_dt, tz_dt64) "
                    "VALUES (:id, :dt, :dt64, :arr, :tup, :tz_dt, :tz_dt64)"
                ),
                {
                    "id": 1,
                    "dt": SECOND,
                    "dt64": MILLIS,
                    "arr": [MILLIS],
                    "tup": (MILLIS, "first"),
                    # A zone-pinned column reads a naive value as its wall
                    # time in that zone, whatever the server runs in.
                    "tz_dt": datetime(2026, 1, 1, 8),
                    "tz_dt64": datetime(2026, 1, 1, 8, 0, 0, 123000),
                },
            )

            zone = await _server_zone(conn)
            second = _expected(SECOND, zone, aware)
            millis = _expected(MILLIS, zone, aware)

            selected = text(
                f"SELECT dt, dt64, arr, tup, tz_dt, tz_dt64 FROM {table}"
            )
            row = (await conn.execute(selected)).one()
            _assert_matches(row.dt, second, aware)
            _assert_matches(row.dt64, millis, aware)
            _assert_matches(row.arr[0], millis, aware)
            _assert_matches(row.tup[0], millis, aware)
            assert row.dt64.microsecond == 123000
            assert row.tup[1] == "first"

            grouped = (
                await conn.execute(
                    text(f"SELECT groupArray((dt, dt64, tup.2)) FROM {table}")
                )
            ).scalar_one()
            _assert_matches(grouped[0][0], second, aware)
            _assert_matches(grouped[0][1], millis, aware)
            assert grouped[0][2] == "first"

            # An explicit zone on the column outranks the client setting.
            assert row.tz_dt.utcoffset() == timedelta(hours=8)
            assert row.tz_dt == SECOND
            assert row.tz_dt.microsecond == 0
            assert row.tz_dt64.utcoffset() == timedelta(hours=8)
            assert row.tz_dt64 == MILLIS
            assert row.tz_dt64.microsecond == 123000

            # The typed SQLAlchemy path passes the driver value through.
            typed_row = (
                await conn.execute(
                    select(typed.c.dt, typed.c.dt64, typed.c.arr, typed.c.tup)
                )
            ).one()
            _assert_matches(typed_row.dt, second, aware)
            _assert_matches(typed_row.dt64, millis, aware)
            _assert_matches(typed_row.arr[0], millis, aware)
            _assert_matches(typed_row.tup[0], millis, aware)
            assert typed_row.tup[1] == "first"

            # Values read back can be bound again as they are.
            for where, value in (
                ("dt = :v", row.dt),
                ("dt64 = :v", row.dt64),
                ("dt64 IN :v", (row.dt64, row.dt64)),
            ):
                assert await _count(conn, table, where, value) == 1
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()


@pytest.mark.asyncio
@ENGINE_CASES
async def test_datetime_as_utc_stays_a_client_setting(settings, query, aware):
    engine = _engine_with(settings, query)

    try:
        async with engine.connect() as conn:
            proto = _proto_connection(conn)
            assert proto.client_settings["datetime_as_utc"] is aware
            assert "datetime_as_utc" not in proto.settings

            # ClickHouse refuses settings it does not know, so these run only
            # if the driver stripped the client setting before the wire.
            assert (await conn.execute(text("SELECT 1"))).scalar_one() == 1
            assert await _server_setting(conn, "datetime_as_utc") is None
            # The dialect's join default survives alongside a DSN setting.
            assert await _server_setting(conn, "join_use_nulls") == "1"
    finally:
        await engine.dispose()


@pytest.mark.parametrize("value", ["false", "0"])
@pytest.mark.asyncio
async def test_use_client_time_zone_dsn_value_reaches_the_server(value):
    engine = _engine_with(
        None, {"datetime_as_utc": "true", "use_client_time_zone": value}
    )

    try:
        async with engine.connect() as conn:
            assert _proto_connection(conn).settings[
                "use_client_time_zone"
            ] is False
            setting = await _server_setting(conn, "use_client_time_zone")
            assert setting == "0"

            row = (
                await conn.execute(
                    text(
                        "SELECT toDateTime64('2026-01-01 00:00:00.123', 3)"
                        " AS ts"
                    )
                )
            ).one()
            assert row.ts.utcoffset() == timedelta(0)
            assert row.ts.microsecond == 123000
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@ENGINE_CASES
async def test_core_insert_and_text_insert_store_the_same_instant(
    settings, query, aware
):
    table = _table_name("dt_insert_paths")
    engine = _engine_with(settings, query)
    metadata = MetaData()
    typed = Table(
        table,
        metadata,
        Column("id", ch_types.UInt64, primary_key=True),
        Column("dt", ch_types.DateTime),
        Column("dt64", ch_types.DateTime64(3)),
        engines.MergeTree(order_by=("id",)),
    )

    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            zone = await _server_zone(conn)

            await conn.execute(
                typed.insert(), {"id": 1, "dt": SECOND, "dt64": MILLIS}
            )
            # A text() VALUES section substitutes its parameters as text, so
            # this is the other write path into the same columns.
            await conn.execute(
                text(
                    f"INSERT INTO {table} (id, dt, dt64) "
                    "VALUES (:id, :dt, :dt64)"
                ),
                {"id": 2, "dt": SECOND, "dt64": MILLIS},
            )

            ordered = select(typed.c.id, typed.c.dt, typed.c.dt64).order_by(
                typed.c.id
            )
            rows = (await conn.execute(ordered)).all()
            assert [row.id for row in rows] == [1, 2]

            first, second = rows
            assert first.dt == second.dt
            assert first.dt64 == second.dt64
            _assert_matches(first.dt, _expected(SECOND, zone, aware), aware)
            _assert_matches(first.dt64, _expected(MILLIS, zone, aware), aware)
            assert second.dt64.microsecond == 123000
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        await engine.dispose()
