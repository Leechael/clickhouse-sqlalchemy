from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_replacing_mergetree_union_watermarks_and_timezone_queries():
    point_table = _table_name("health_point")
    interval_table = _table_name("health_interval")
    daily_table = _table_name("health_daily")
    engine = _engine()

    device_id = "device-redacted-1"
    first_point = datetime(2026, 2, 1, 23, 30, 0, 123000)
    second_point = datetime(2026, 2, 2, 0, 30, 0, 456000)
    interval_start = datetime(2026, 2, 2, 1, 0, 0, 111000)
    interval_end = datetime(2026, 2, 2, 1, 15, 0, 222000)
    created_old = datetime(2026, 2, 2, 1, 0, 1, 333000)
    created_new = datetime(2026, 2, 2, 1, 0, 2, 444000)

    try:
        async with engine.begin() as conn:
            for table in (daily_table, interval_table, point_table):
                await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {point_table} (
                        device_id String,
                        timestamp DateTime64(3),
                        value Float64,
                        motion_context Nullable(Int32),
                        source Nullable(String),
                        created_at DateTime64(3) DEFAULT now64()
                    )
                    ENGINE = ReplacingMergeTree(created_at)
                    PARTITION BY toYYYYMM(timestamp)
                    ORDER BY (device_id, timestamp)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {interval_table} (
                        device_id String,
                        start_time DateTime64(3),
                        end_time DateTime64(3),
                        value Float64,
                        source Nullable(String),
                        created_at DateTime64(3) DEFAULT now64()
                    )
                    ENGINE = ReplacingMergeTree(created_at)
                    PARTITION BY toYYYYMM(start_time)
                    ORDER BY (device_id, start_time)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {daily_table} (
                        device_id String,
                        date Date,
                        value Float64,
                        source Nullable(String),
                        created_at DateTime64(3) DEFAULT now64()
                    )
                    ENGINE = ReplacingMergeTree(created_at)
                    PARTITION BY toYYYYMM(date)
                    ORDER BY (device_id, date)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {point_table} (
                        device_id, timestamp, value, motion_context, source, created_at
                    )
                    VALUES (
                        :device_id, :timestamp, :value, :motion_context,
                        :source, :created_at
                    )
                    """
                ),
                [
                    {
                        "device_id": device_id,
                        "timestamp": first_point,
                        "value": 61.0,
                        "motion_context": None,
                        "source": "source-redacted",
                        "created_at": created_old,
                    },
                    {
                        "device_id": device_id,
                        "timestamp": first_point,
                        "value": 62.5,
                        "motion_context": 2,
                        "source": "source-redacted",
                        "created_at": created_new,
                    },
                    {
                        "device_id": device_id,
                        "timestamp": second_point,
                        "value": 64.0,
                        "motion_context": 3,
                        "source": None,
                        "created_at": created_new,
                    },
                ],
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {interval_table} (
                        device_id, start_time, end_time, value, source, created_at
                    )
                    VALUES (
                        :device_id, :start_time, :end_time, :value,
                        :source, :created_at
                    )
                    """
                ),
                {
                    "device_id": device_id,
                    "start_time": interval_start,
                    "end_time": interval_end,
                    "value": 12.5,
                    "source": "source-redacted",
                    "created_at": created_new,
                },
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {daily_table} (
                        device_id, date, value, source, created_at
                    )
                    VALUES (:device_id, :date, :value, :source, :created_at)
                    """
                ),
                {
                    "device_id": device_id,
                    "date": date(2026, 2, 2),
                    "value": 58.0,
                    "source": None,
                    "created_at": created_new,
                },
            )

            latest_point = await conn.execute(
                text(
                    f"""
                    SELECT timestamp, value, motion_context, source, created_at
                    FROM {point_table} FINAL
                    WHERE device_id = :device_id
                      AND timestamp >= :start
                      AND timestamp <= :end
                    ORDER BY timestamp
                    """
                ),
                {
                    "device_id": device_id,
                    "start": first_point,
                    "end": second_point,
                },
            )
            point_rows = latest_point.fetchall()
            assert [row.value for row in point_rows] == [62.5, 64.0]
            assert point_rows[0].motion_context == 2
            assert point_rows[1].source is None
            _assert_ms(point_rows[0].timestamp, 123000)
            _assert_ms(point_rows[0].created_at, 444000)

            counts = await conn.execute(
                text(
                    f"""
                    SELECT 'point' AS table_name, count() AS count
                    FROM {point_table} FINAL
                    WHERE device_id = :device_id
                    UNION ALL
                    SELECT 'interval' AS table_name, count() AS count
                    FROM {interval_table} FINAL
                    WHERE device_id = :device_id
                    UNION ALL
                    SELECT 'daily' AS table_name, count() AS count
                    FROM {daily_table} FINAL
                    WHERE device_id = :device_id
                    """
                ),
                {"device_id": device_id},
            )
            assert {row.table_name: row.count for row in counts} == {
                "point": 2,
                "interval": 1,
                "daily": 1,
            }

            watermarks = await conn.execute(
                text(
                    f"""
                    SELECT 'point' AS table_name, toString(max(timestamp)) AS watermark
                    FROM {point_table}
                    WHERE device_id = :device_id
                    UNION ALL
                    SELECT 'interval' AS table_name, toString(max(start_time)) AS watermark
                    FROM {interval_table}
                    WHERE device_id = :device_id
                    UNION ALL
                    SELECT 'daily' AS table_name, toString(max(date)) AS watermark
                    FROM {daily_table}
                    WHERE device_id = :device_id
                    """
                ),
                {"device_id": device_id},
            )
            watermarks_by_table = {row.table_name: row.watermark for row in watermarks}
            assert watermarks_by_table["point"].startswith("2026-02-02 00:30:00")
            assert watermarks_by_table["interval"].startswith("2026-02-02 01:00:00")
            assert watermarks_by_table["daily"] == "2026-02-02"

            days = await conn.execute(
                text(
                    f"""
                    SELECT DISTINCT toDayOfMonth(toTimeZone(timestamp, :timezone)) AS day
                    FROM {point_table} FINAL
                    WHERE device_id = :device_id
                      AND timestamp >= :start
                      AND timestamp < :end
                    ORDER BY day
                    """
                ),
                {
                    "device_id": device_id,
                    "timezone": "Asia/Taipei",
                    "start": datetime(2026, 2, 1, 0, 0, 0),
                    "end": datetime(2026, 2, 3, 0, 0, 0),
                },
            )
            assert [row.day for row in days] == [2]

            daily_rows = await conn.execute(
                text(
                    f"""
                    SELECT date, value, source
                    FROM {daily_table} FINAL
                    WHERE device_id = :device_id
                      AND date >= :start_date
                      AND date <= :end_date
                    ORDER BY date
                    LIMIT :limit
                    """
                ),
                {
                    "device_id": device_id,
                    "start_date": date(2026, 2, 1),
                    "end_date": date(2026, 2, 3),
                    "limit": 2000,
                },
            )
            daily_row = daily_rows.one()
            assert daily_row.date == date(2026, 2, 2)
            assert daily_row.value == 58.0
            assert daily_row.source is None

    finally:
        for table in (daily_table, interval_table, point_table):
            await _drop(engine, table)
        await engine.dispose()
