from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_concurrent_insert_and_select_operations_preserve_results():
    table = _table_name("concurrent_ops")
    engine = _engine()
    base_time = datetime(2026, 1, 17, 17, 18, 19, 111000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        group_id UInt32,
                        item_id UInt32,
                        payload String,
                        created_at DateTime64(3)
                    )
                    ENGINE = MergeTree
                    ORDER BY (group_id, item_id)
                    """
                )
            )

        insert_stmt = text(
            f"""
            INSERT INTO {table} (group_id, item_id, payload, created_at)
            VALUES (:group_id, :item_id, :payload, :created_at)
            """
        )

        async def insert_group(group_id):
            async with engine.begin() as conn:
                for item_id in range(5):
                    await conn.execute(
                        insert_stmt,
                        {
                            "group_id": group_id,
                            "item_id": item_id,
                            "payload": f"redacted-{group_id}-{item_id}",
                            "created_at": base_time.replace(
                                microsecond=111000 + group_id * 1000 + item_id
                            ),
                        },
                    )
            return group_id

        inserted_groups = await asyncio.gather(*(insert_group(i) for i in range(4)))
        assert inserted_groups == [0, 1, 2, 3]

        async def query_group(group_id):
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        f"""
                        SELECT
                            group_id,
                            count() AS row_count,
                            groupArray(payload) AS payloads,
                            max(created_at) AS latest_created_at
                        FROM {table}
                        WHERE group_id = :group_id
                        GROUP BY group_id
                        """
                    ),
                    {"group_id": group_id},
                )
                return result.one()

        rows = await asyncio.gather(*(query_group(i) for i in range(4)))

        assert [row.group_id for row in rows] == [0, 1, 2, 3]
        assert [row.row_count for row in rows] == [5, 5, 5, 5]
        for group_id, row in enumerate(rows):
            assert set(row.payloads) == {
                f"redacted-{group_id}-{item_id}" for item_id in range(5)
            }
            _assert_ms(row.latest_created_at, 111000 + group_id * 1000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_compiled_insert_sql_preserves_decimal_literals_and_string_escaping():
    table = _table_name("raw_usage")
    engine = _engine()

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        resource_id String,
                        timestamp DateTime,
                        event_type String,
                        cost Decimal64(6),
                        details String,
                        billing_start DateTime,
                        billing_end DateTime,
                        duration_minutes Float64,
                        workspace_id Nullable(UInt64),
                        usage_type String,
                        billing_key String,
                        resource_type String,
                        hourly_rate Decimal64(6)
                    )
                    ENGINE = MergeTree
                    ORDER BY (resource_id, timestamp, usage_type, event_type)
                    """
                )
            )

            raw_sql = f"""
            INSERT INTO {table} (
                snowflake_id, resource_id, timestamp, event_type, cost, details,
                billing_start, billing_end, duration_minutes, workspace_id,
                usage_type, billing_key, resource_type, hourly_rate
            )
            VALUES (
                1,
                'resource-raw-1',
                '2026-01-24 00:00:00',
                'hourly.billing',
                toDecimal64('0.123456', 6),
                'details with ''quoted'' value',
                '2026-01-23 23:00:00',
                '2026-01-24 00:00:00',
                60.0,
                NULL,
                'compute',
                'raw-key-redacted',
                'standard-small',
                toDecimal64('0.123456', 6)
            )
            """
            await conn.execute(text(raw_sql))

            result = await conn.execute(
                text(
                    f"""
                    SELECT cost, hourly_rate, details, workspace_id
                    FROM {table}
                    WHERE billing_key = :billing_key
                    """
                ),
                {"billing_key": "raw-key-redacted"},
            )
            row = result.one()

            assert row.cost == Decimal("0.123456")
            assert row.hourly_rate == Decimal("0.123456")
            assert row.details == "details with 'quoted' value"
            assert row.workspace_id is None

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_textual_executemany_insert_accepts_multiple_parameter_rows():
    table = _table_name("textual_many")
    engine = _engine()

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        payload String
                    )
                    ENGINE = Memory
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (id, payload)
                    VALUES (:id, :payload)
                    """
                ),
                [
                    {"id": 1, "payload": "redacted-1"},
                    {"id": 2, "payload": "redacted-2"},
                ],
            )

            result = await conn.execute(
                text(f"SELECT count(), groupArray(payload) FROM {table}")
            )
            count, payloads = result.one()
            assert count == 2
            assert set(payloads) == {"redacted-1", "redacted-2"}

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_textual_single_row_insert_loop_accepts_reused_statement():
    table = _table_name("textual_many")
    engine = _engine()

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        id UInt64,
                        payload String
                    )
                    ENGINE = Memory
                    """
                )
            )
            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (id, payload)
                    VALUES (:id, :payload)
                    """
                ),
                [
                    {"id": 1, "payload": "redacted-1"},
                    {"id": 2, "payload": "redacted-2"},
                ],
            )

            result = await conn.execute(
                text(f"SELECT count(), groupArray(payload) FROM {table}")
            )
            count, payloads = result.one()
            assert count == 2
            assert set(payloads) == {"redacted-1", "redacted-2"}

    finally:
        await _drop(engine, table)
        await engine.dispose()
