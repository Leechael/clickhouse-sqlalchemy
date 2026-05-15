from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_interval_overlap_in_filters_and_nullable_values_round_trip():
    sleep_table = _table_name("sleep_stage")
    activity_table = _table_name("activity_interval")
    category_table = _table_name("category_event")
    workout_table = _table_name("workout_event")
    engine = _engine()

    device_id = "device-redacted-2"
    window_start = datetime(2026, 2, 3, 22, 0, 0, 111000)
    sleep_start = datetime(2026, 2, 3, 22, 30, 0, 222000)
    sleep_end = datetime(2026, 2, 4, 6, 45, 0, 333000)
    activity_start = datetime(2026, 2, 4, 6, 30, 0, 444000)
    activity_end = datetime(2026, 2, 4, 7, 0, 0, 555000)
    category_start = datetime(2026, 2, 4, 7, 30, 0, 666000)
    category_end = datetime(2026, 2, 4, 7, 35, 0, 777000)
    workout_start = datetime(2026, 2, 4, 8, 0, 0, 888000)
    workout_end = datetime(2026, 2, 4, 8, 45, 0, 999000)
    window_end = datetime(2026, 2, 4, 9, 0, 0, 0)

    try:
        async with engine.begin() as conn:
            for table in (workout_table, category_table, activity_table, sleep_table):
                await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {sleep_table} (
                        device_id String,
                        start_time DateTime64(3),
                        end_time DateTime64(3),
                        stage Int32,
                        source Nullable(String),
                        created_at DateTime64(3) DEFAULT now64()
                    )
                    ENGINE = ReplacingMergeTree(created_at)
                    PARTITION BY toYYYYMM(start_time)
                    ORDER BY (device_id, start_time, end_time)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {activity_table} (
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
                    CREATE TABLE {category_table} (
                        device_id String,
                        start_time DateTime64(3),
                        end_time DateTime64(3),
                        value Nullable(Int32),
                        source Nullable(String),
                        created_at DateTime64(3) DEFAULT now64()
                    )
                    ENGINE = ReplacingMergeTree(created_at)
                    PARTITION BY toYYYYMM(start_time)
                    ORDER BY (device_id, start_time, end_time)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {workout_table} (
                        device_id String,
                        start_time DateTime64(3),
                        end_time DateTime64(3),
                        workout_type String,
                        duration_seconds Float64,
                        total_energy_kcal Nullable(Float64),
                        total_distance_meters Nullable(Float64),
                        source Nullable(String),
                        created_at DateTime64(3) DEFAULT now64()
                    )
                    ENGINE = ReplacingMergeTree(created_at)
                    PARTITION BY toYYYYMM(start_time)
                    ORDER BY (device_id, start_time)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {sleep_table} (
                        device_id, start_time, end_time, stage, source
                    )
                    VALUES (
                        :device_id, :start_time, :end_time, :stage, :source
                    )
                    """
                ),
                [
                    {
                        "device_id": device_id,
                        "start_time": sleep_start,
                        "end_time": sleep_end,
                        "stage": 2,
                        "source": "source-redacted",
                    },
                    {
                        "device_id": device_id,
                        "start_time": datetime(2026, 2, 4, 7, 0, 0, 0),
                        "end_time": datetime(2026, 2, 4, 7, 15, 0, 0),
                        "stage": 0,
                        "source": "source-redacted",
                    },
                ],
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {activity_table} (
                        device_id, start_time, end_time, value, source
                    )
                    VALUES (
                        :device_id, :start_time, :end_time, :value, :source
                    )
                    """
                ),
                {
                    "device_id": device_id,
                    "start_time": activity_start,
                    "end_time": activity_end,
                    "value": 36.5,
                    "source": None,
                },
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {category_table} (
                        device_id, start_time, end_time, value, source
                    )
                    VALUES (
                        :device_id, :start_time, :end_time, :value, :source
                    )
                    """
                ),
                {
                    "device_id": device_id,
                    "start_time": category_start,
                    "end_time": category_end,
                    "value": None,
                    "source": "source-redacted",
                },
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {workout_table} (
                        device_id, start_time, end_time, workout_type,
                        duration_seconds, total_energy_kcal,
                        total_distance_meters, source
                    )
                    VALUES (
                        :device_id, :start_time, :end_time, :workout_type,
                        :duration_seconds, :total_energy_kcal,
                        :total_distance_meters, :source
                    )
                    """
                ),
                {
                    "device_id": device_id,
                    "start_time": workout_start,
                    "end_time": workout_end,
                    "workout_type": "workout-redacted",
                    "duration_seconds": 2700.0,
                    "total_energy_kcal": None,
                    "total_distance_meters": 5000.25,
                    "source": "source-redacted",
                },
            )

            sleep_rows = await conn.execute(
                text(
                    f"""
                    SELECT device_id, start_time, end_time, stage, source
                    FROM {sleep_table} FINAL
                    WHERE device_id = :device_id
                      AND start_time >= :start
                      AND start_time < :end
                      AND stage IN :stages
                    ORDER BY start_time
                    """
                ),
                {
                    "device_id": device_id,
                    "start": window_start,
                    "end": window_end,
                    "stages": (2, 3, 4),
                },
            )
            sleep_row = sleep_rows.one()
            assert sleep_row.stage == 2
            _assert_ms(sleep_row.start_time, 222000)
            _assert_ms(sleep_row.end_time, 333000)

            interval_rows = await conn.execute(
                text(
                    f"""
                    SELECT device_id, start_time, end_time, value, source
                    FROM {activity_table} FINAL
                    WHERE device_id = :device_id
                      AND start_time < :end
                      AND end_time > :start
                    ORDER BY start_time
                    """
                ),
                {
                    "device_id": device_id,
                    "start": sleep_end,
                    "end": window_end,
                },
            )
            interval_row = interval_rows.one()
            assert interval_row.value == 36.5
            assert interval_row.source is None
            _assert_ms(interval_row.start_time, 444000)
            _assert_ms(interval_row.end_time, 555000)

            category_rows = await conn.execute(
                text(
                    f"""
                    SELECT device_id, start_time, end_time, value, source
                    FROM {category_table} FINAL
                    WHERE device_id = :device_id
                      AND start_time < :end
                      AND end_time > :start
                    ORDER BY start_time
                    """
                ),
                {
                    "device_id": device_id,
                    "start": window_start,
                    "end": window_end,
                },
            )
            category_row = category_rows.one()
            assert category_row.value is None
            _assert_ms(category_row.start_time, 666000)
            _assert_ms(category_row.end_time, 777000)

            workout_rows = await conn.execute(
                text(
                    f"""
                    SELECT
                        workout_type,
                        duration_seconds,
                        total_energy_kcal,
                        total_distance_meters,
                        source
                    FROM {workout_table} FINAL
                    WHERE device_id = :device_id
                      AND start_time < :end
                      AND end_time > :start
                    ORDER BY start_time
                    """
                ),
                {
                    "device_id": device_id,
                    "start": window_start,
                    "end": window_end,
                },
            )
            workout_row = workout_rows.one()
            assert workout_row.workout_type == "workout-redacted"
            assert workout_row.duration_seconds == 2700.0
            assert workout_row.total_energy_kcal is None
            assert workout_row.total_distance_meters == 5000.25

    finally:
        for table in (workout_table, category_table, activity_table, sleep_table):
            await _drop(engine, table)
        await engine.dispose()
