from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_view_and_materialized_view_queries_return_expected_rows():
    source = _table_name("usage_source")
    records_view = _table_name("usage_records_view")
    summary_view = _table_name("usage_summary_view")
    engine = _engine()

    timestamp = datetime(2026, 1, 20, 20, 21, 22, 333000)
    billing_start = datetime(2026, 1, 20, 20, 0, 0, 100000)
    billing_end = datetime(2026, 1, 20, 21, 0, 0, 900000)

    try:
        async with engine.begin() as conn:
            for table in (summary_view, records_view, source):
                await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {source} (
                        resource_id String,
                        workspace_id UInt64,
                        timestamp DateTime64(3),
                        event_type String,
                        cost Decimal64(6),
                        details String,
                        billing_start DateTime64(3),
                        billing_end DateTime64(3),
                        billing_hour DateTime MATERIALIZED toStartOfHour(timestamp),
                        billing_day Date MATERIALIZED toDate(timestamp)
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(timestamp)
                    ORDER BY (resource_id, billing_hour, event_type)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE VIEW {records_view} AS
                    SELECT
                        resource_id,
                        workspace_id,
                        timestamp,
                        event_type,
                        cost,
                        details,
                        billing_start,
                        billing_end,
                        billing_hour,
                        billing_day
                    FROM {source}
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE MATERIALIZED VIEW {summary_view}
                    ENGINE = SummingMergeTree()
                    PARTITION BY toYYYYMM(hour)
                    ORDER BY (resource_id, hour)
                    AS SELECT
                        resource_id,
                        toStartOfHour(timestamp) AS hour,
                        sum(cost) AS total_cost,
                        count() AS billing_events
                    FROM {source}
                    GROUP BY resource_id, hour
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {source} (
                        resource_id, workspace_id, timestamp, event_type, cost,
                        details, billing_start, billing_end
                    )
                    VALUES (
                        :resource_id, :workspace_id, :timestamp, :event_type,
                        :cost, :details, :billing_start, :billing_end
                    )
                    """
                ),
                {
                    "resource_id": "resource-view-1",
                    "workspace_id": 880,
                    "timestamp": timestamp,
                    "event_type": "compute",
                    "cost": Decimal("0.333333"),
                    "details": "redacted view usage",
                    "billing_start": billing_start,
                    "billing_end": billing_end,
                },
            )

            records = await conn.execute(
                text(
                    f"""
                    SELECT timestamp, billing_start, billing_end, cost
                    FROM {records_view}
                    WHERE resource_id = :resource_id
                    """
                ),
                {"resource_id": "resource-view-1"},
            )
            record = records.one()
            assert record.cost == Decimal("0.333333")
            _assert_ms(record.timestamp, 333000)
            _assert_ms(record.billing_start, 100000)
            _assert_ms(record.billing_end, 900000)

            summary = await conn.execute(
                text(
                    f"""
                    SELECT total_cost, billing_events
                    FROM {summary_view} FINAL
                    WHERE resource_id = :resource_id
                    """
                ),
                {"resource_id": "resource-view-1"},
            )
            summary_row = summary.one()
            assert summary_row.total_cost == Decimal("0.333333")
            assert summary_row.billing_events == 1

    finally:
        for table in (summary_view, records_view, source):
            await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_mutation_statements_accept_bound_datetime64_values():
    table = _table_name("mutation_rows")
    engine = _engine()

    checksum = _fixed_hex(64)
    created_at = datetime(2026, 1, 21, 21, 22, 23, 111000)
    verified_at = datetime(2026, 1, 21, 21, 22, 24, 222000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        checksum FixedString(64),
                        cert_data Nullable(String),
                        platform_id String DEFAULT '',
                        verified UInt8 DEFAULT 0,
                        created_at DateTime64(3, 'UTC'),
                        verified_at DateTime64(3, 'UTC') DEFAULT created_at
                    )
                    ENGINE = MergeTree
                    ORDER BY created_at
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, checksum, cert_data, platform_id,
                        verified, created_at, verified_at
                    )
                    VALUES (
                        :snowflake_id, :checksum, :cert_data, :platform_id,
                        :verified, :created_at, :verified_at
                    )
                    """
                ),
                {
                    "snowflake_id": 1,
                    "checksum": checksum,
                    "cert_data": "cert-redacted",
                    "platform_id": "",
                    "verified": 0,
                    "created_at": created_at,
                    "verified_at": created_at,
                },
            )

            await conn.execute(
                text(
                    f"""
                    ALTER TABLE {table}
                    UPDATE platform_id = :platform_id,
                           verified = :verified,
                           verified_at = :verified_at
                    WHERE checksum = :checksum
                    SETTINGS mutations_sync = 1
                    """
                ),
                {
                    "platform_id": "platform-redacted",
                    "verified": 1,
                    "verified_at": verified_at,
                    "checksum": checksum,
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT platform_id, verified, created_at, verified_at
                    FROM {table}
                    WHERE checksum = :checksum
                    """
                ),
                {"checksum": checksum},
            )
            row = result.one()
            assert row.platform_id == "platform-redacted"
            assert row.verified == 1
            _assert_ms(row.created_at, 111000)
            _assert_ms(row.verified_at, 222000)

            await conn.execute(
                text(
                    f"""
                    ALTER TABLE {table}
                    DELETE WHERE checksum = :checksum
                    SETTINGS mutations_sync = 1
                    """
                ),
                {"checksum": checksum},
            )
            remaining = await conn.execute(text(f"SELECT count() FROM {table}"))
            assert remaining.scalar_one() == 0

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_interpolated_in_lists_dates_and_path_filters_return_expected_rows():
    events = _table_name("audit_events")
    activity = _table_name("audit_activity")
    engine = _engine()

    resource_uuid = _uuid(31)
    bare_uuid = resource_uuid.replace("-", "")
    event_time = datetime(2026, 1, 22, 22, 23, 24, 555000)
    request_time = datetime(2026, 1, 22, 22, 24, 25, 666000)

    try:
        async with engine.begin() as conn:
            for table in (activity, events):
                await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {events} (
                        resource_id String,
                        event_type String,
                        timestamp DateTime64(3),
                        triggered_by UInt64 DEFAULT 0
                    )
                    ENGINE = MergeTree
                    ORDER BY (resource_id, timestamp)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {activity} (
                        request_path String,
                        http_method Enum8('GET' = 1, 'POST' = 2, 'DELETE' = 3),
                        response_code UInt16,
                        request_time DateTime64(3),
                        request_date Date MATERIALIZED toDate(request_time)
                    )
                    ENGINE = MergeTree
                    PARTITION BY request_date
                    ORDER BY (request_date, request_time)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {events} (
                        resource_id, event_type, timestamp, triggered_by
                    )
                    VALUES (
                        :resource_id, :event_type, :timestamp, :triggered_by
                    )
                    """
                ),
                {
                    "resource_id": resource_uuid,
                    "event_type": "resource.stop.start",
                    "timestamp": event_time,
                    "triggered_by": 0,
                },
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {activity} (
                        request_path, http_method, response_code, request_time
                    )
                    VALUES (
                        :request_path, :http_method, :response_code, :request_time
                    )
                    """
                ),
                {
                    "request_path": f"/api/v1/resources/{bare_uuid}/stop",
                    "http_method": "POST",
                    "response_code": 202,
                    "request_time": request_time,
                },
            )

            event_result = await conn.execute(
                text(
                    f"""
                    SELECT resource_id, event_type, timestamp, triggered_by
                    FROM {events}
                    WHERE resource_id IN ('{resource_uuid}')
                      AND triggered_by = 0
                      AND event_type IN ('resource.stop.start', 'resource.delete.start')
                      AND toDate(timestamp) BETWEEN :start_date AND :end_date
                    ORDER BY timestamp
                    """
                ),
                {
                    "start_date": "2026-01-22",
                    "end_date": "2026-01-22",
                },
            )
            event_row = event_result.one()
            assert event_row.resource_id == resource_uuid
            assert event_row.triggered_by == 0
            _assert_ms(event_row.timestamp, 555000)

            api_result = await conn.execute(
                text(
                    f"""
                    SELECT request_path, http_method, request_time
                    FROM {activity}
                    WHERE request_date BETWEEN :start_date AND :end_date
                      AND response_code < 300
                      AND (
                        (http_method = 'POST' AND request_path LIKE :stop_pattern)
                        OR (http_method = 'DELETE' AND request_path LIKE :delete_pattern)
                      )
                    ORDER BY request_time
                    """
                ),
                {
                    "start_date": "2026-01-22",
                    "end_date": "2026-01-22",
                    "stop_pattern": "/api/v1/resources/%/stop",
                    "delete_pattern": "/api/v1/resources/%",
                },
            )
            api_row = api_result.one()
            assert bare_uuid in api_row.request_path
            assert api_row.http_method == "POST"
            _assert_ms(api_row.request_time, 666000)

    finally:
        for table in (activity, events):
            await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_expanding_bindparams_compile_for_tuple_in_queries():
    table = _table_name("last_activity")
    engine = _engine()
    first_seen = datetime(2026, 1, 23, 23, 0, 0, 123000)
    last_seen = datetime(2026, 1, 23, 23, 30, 0, 987000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        actor_id UInt64,
                        request_time DateTime64(3),
                        request_date Date MATERIALIZED toDate(request_time)
                    )
                    ENGINE = MergeTree
                    ORDER BY (actor_id, request_time)
                    """
                )
            )
            stmt = text(
                f"""
                INSERT INTO {table} (actor_id, request_time)
                VALUES (:actor_id, :request_time)
                """
            )
            await _execute_each(
                conn,
                stmt,
                [
                    {"actor_id": 1, "request_time": first_seen},
                    {"actor_id": 1, "request_time": last_seen},
                    {"actor_id": 2, "request_time": first_seen},
                ],
            )

            query = text(
                f"""
                SELECT actor_id, max(request_time) AS last_activity_at
                FROM {table}
                WHERE actor_id IN :actor_ids
                GROUP BY actor_id
                ORDER BY actor_id
                """
            ).bindparams(bindparam("actor_ids", expanding=True))
            result = await conn.execute(query, {"actor_ids": [1, 2]})
            rows = result.fetchall()

            assert [row.actor_id for row in rows] == [1, 2]
            _assert_ms(rows[0].last_activity_at, 987000)
            _assert_ms(rows[1].last_activity_at, 123000)

    finally:
        await _drop(engine, table)
        await engine.dispose()
