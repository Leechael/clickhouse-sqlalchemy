from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_window_join_predicates_preserve_datetime64_milliseconds():
    table = _table_name("event_pairs")
    engine = _engine()

    first_start = datetime(2026, 1, 2, 10, 0, 0, 111000)
    first_end = datetime(2026, 1, 2, 10, 0, 5, 444000)
    second_start = datetime(2026, 1, 2, 10, 1, 0, 555000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        event_type String,
                        resource_id String,
                        timestamp DateTime64(3),
                        state String,
                        resource_type String,
                        old_resource_type Nullable(String),
                        new_resource_type Nullable(String)
                    )
                    ENGINE = MergeTree
                    ORDER BY (resource_id, timestamp, event_type)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, event_type, resource_id, timestamp, state,
                        resource_type, old_resource_type, new_resource_type
                    )
                    VALUES (
                        :snowflake_id, :event_type, :resource_id, :timestamp,
                        :state, :resource_type, :old_resource_type,
                        :new_resource_type
                    )
                    """
                ),
                [
                    {
                        "snowflake_id": 1,
                        "event_type": "resource.start.start",
                        "resource_id": "resource-0002",
                        "timestamp": first_start,
                        "state": "starting",
                        "resource_type": "standard-small",
                        "old_resource_type": None,
                        "new_resource_type": None,
                    },
                    {
                        "snowflake_id": 2,
                        "event_type": "resource.start.end",
                        "resource_id": "resource-0002",
                        "timestamp": first_end,
                        "state": "running",
                        "resource_type": "standard-small",
                        "old_resource_type": None,
                        "new_resource_type": None,
                    },
                    {
                        "snowflake_id": 3,
                        "event_type": "resource.stop.start",
                        "resource_id": "resource-0002",
                        "timestamp": second_start,
                        "state": "stopping",
                        "resource_type": "standard-small",
                        "old_resource_type": None,
                        "new_resource_type": None,
                    },
                ],
            )

            result = await conn.execute(
                text(
                    f"""
                    WITH filtered_events AS (
                        SELECT *,
                               toDateTime64(timestamp, 3) AS ts_ms,
                               REGEXP_REPLACE(event_type, '\\.(start|end)$', '') AS base_event_type
                        FROM {table}
                        WHERE resource_id = :resource_id
                    ),
                    starts AS (
                        SELECT *,
                               row_number() OVER (PARTITION BY base_event_type ORDER BY ts_ms ASC) AS rn
                        FROM filtered_events
                        WHERE event_type LIKE '%.start'
                    ),
                    ends AS (
                        SELECT *,
                               row_number() OVER (PARTITION BY base_event_type ORDER BY ts_ms ASC) AS rn
                        FROM filtered_events
                        WHERE event_type LIKE '%.end'
                    )
                    SELECT
                        s.base_event_type AS event_type,
                        CASE WHEN e.ts_ms IS NOT NULL THEN e.state ELSE s.state END AS state,
                        CASE WHEN e.ts_ms IS NOT NULL THEN 'completed' ELSE 'pending' END AS status,
                        CASE WHEN e.ts_ms IS NOT NULL THEN dateDiff('millisecond', s.ts_ms, e.ts_ms) ELSE NULL END AS duration_ms,
                        greatest(s.ts_ms, if(e.ts_ms IS NOT NULL, e.ts_ms, s.ts_ms)) AS event_ts
                    FROM starts s
                    LEFT JOIN ends e
                      ON s.base_event_type = e.base_event_type AND s.rn = e.rn
                    ORDER BY event_ts DESC
                    """
                ),
                {"resource_id": "resource-0002"},
            )
            rows = result.fetchall()

            assert [row.status for row in rows] == ["pending", "completed"]
            assert rows[1].duration_ms == 5333
            _assert_ms(rows[0].event_ts, 555000)
            _assert_ms(rows[1].event_ts, 444000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_like_filters_preserve_payload_json_and_datetime64_values():
    table = _table_name("payment_events")
    engine = _engine()

    created_at = datetime(2026, 1, 10, 10, 11, 12, 678000)
    payload = {
        "id": "evt-redacted",
        "type": "payment.succeeded",
        "data": {"object": {"customer": "customer-redacted-1"}},
    }

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        event_id String,
                        event_type String,
                        payload String,
                        created_at DateTime64(3, 'UTC') DEFAULT now64()
                    )
                    ENGINE = MergeTree
                    PRIMARY KEY created_at
                    ORDER BY created_at
                    """
                )
            )

            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, event_id, event_type, payload, created_at
                    )
                    VALUES (
                        :snowflake_id, :event_id, :event_type, :payload,
                        :created_at
                    )
                    """
                ),
                {
                    "snowflake_id": 1,
                    "event_id": "evt-redacted",
                    "event_type": "payment.succeeded",
                    "payload": json.dumps(payload),
                    "created_at": created_at,
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        snowflake_id,
                        event_id,
                        event_type,
                        created_at,
                        payload
                    FROM {table}
                    WHERE (payload LIKE :customer_0 OR payload LIKE :customer_1)
                      AND event_type = :event_type
                      AND created_at >= :since
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "customer_0": "%customer-redacted-1%",
                    "customer_1": "%customer-redacted-2%",
                    "event_type": "payment.succeeded",
                    "since": datetime(2026, 1, 1, 0, 0, 0),
                    "limit": 100,
                },
            )
            row = result.one()

            assert row.event_id == "evt-redacted"
            assert json.loads(row.payload)["data"]["object"]["customer"] == "customer-redacted-1"
            _assert_ms(row.created_at, 678000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_header_json_and_datetime_filters_return_expected_rows():
    table = _table_name("registration_logs")
    engine = _engine()
    registered_at = datetime(2026, 1, 19, 19, 20, 21)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        ip String,
                        email String,
                        table_id String,
                        user_agent String,
                        headers String,
                        registered_at DateTime,
                        is_reachable String
                    )
                    ENGINE = MergeTree
                    ORDER BY (registered_at, table_id, email)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        ip, email, table_id, user_agent, headers,
                        registered_at, is_reachable
                    )
                    VALUES (
                        :ip, :email, :table_id, :user_agent, :headers,
                        :registered_at, :is_reachable
                    )
                    """
                ),
                {
                    "ip": "198.51.100.99",
                    "email": "actor@example.invalid",
                    "table_id": "table-redacted",
                    "user_agent": "agent-redacted",
                    "headers": json.dumps({"x-forwarded-for": "198.51.100.99"}),
                    "registered_at": registered_at,
                    "is_reachable": "true",
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        table_id,
                        email,
                        JSONExtractString(headers, 'x-forwarded-for') AS forwarded_for,
                        any(is_reachable) AS reachable
                    FROM {table}
                    WHERE registered_at >= :start_time
                      AND registered_at < :end_time
                      AND email LIKE :email_pattern
                    GROUP BY table_id, email, headers
                    """
                ),
                {
                    "start_time": datetime(2026, 1, 19, 0, 0, 0),
                    "end_time": datetime(2026, 1, 20, 0, 0, 0),
                    "email_pattern": "%@example.invalid",
                },
            )
            row = result.one()

            assert row.table_id == "table-redacted"
            assert row.email == "actor@example.invalid"
            assert row.forwarded_for == "198.51.100.99"
            assert row.reachable == "true"

    finally:
        await _drop(engine, table)
        await engine.dispose()
