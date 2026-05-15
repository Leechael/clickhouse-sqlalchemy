from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_conditional_aggregation_accepts_datetime_bound_parameters():
    table = _table_name("usage_summary")
    engine = _engine()

    compute_ts = datetime(2026, 1, 4, 1, 0, 0, 125000)
    disk_ts = datetime(2026, 1, 4, 1, 10, 0, 875000)
    start_time = datetime(2026, 1, 4, 0, 0, 0, 100000)
    end_time = datetime(2026, 1, 5, 0, 0, 0, 900000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        resource_id String,
                        workspace_id UInt64,
                        timestamp DateTime64(3),
                        usage_type String,
                        cost Decimal64(6),
                        duration_minutes Float64,
                        billing_start DateTime64(3),
                        billing_end DateTime64(3)
                    )
                    ENGINE = MergeTree
                    ORDER BY (workspace_id, timestamp, resource_id)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, resource_id, workspace_id, timestamp,
                        usage_type, cost, duration_minutes, billing_start,
                        billing_end
                    )
                    VALUES (
                        :snowflake_id, :resource_id, :workspace_id, :timestamp,
                        :usage_type, :cost, :duration_minutes, :billing_start,
                        :billing_end
                    )
                    """
                ),
                [
                    {
                        "snowflake_id": 1,
                        "resource_id": "resource-usage-2",
                        "workspace_id": 301,
                        "timestamp": compute_ts,
                        "usage_type": "compute",
                        "cost": Decimal("1.500000"),
                        "duration_minutes": 30.25,
                        "billing_start": start_time,
                        "billing_end": end_time,
                    },
                    {
                        "snowflake_id": 2,
                        "resource_id": "resource-usage-2",
                        "workspace_id": 301,
                        "timestamp": disk_ts,
                        "usage_type": "disk",
                        "cost": Decimal("0.250000"),
                        "duration_minutes": 30.25,
                        "billing_start": start_time,
                        "billing_end": end_time,
                    },
                ],
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        resource_id,
                        sumIf(cost, usage_type != 'disk') AS compute_cost,
                        sumIf(cost, usage_type = 'disk') AS disk_cost,
                        sumIf(ifNull(duration_minutes, 0), usage_type != 'disk') AS compute_minutes,
                        min(billing_start) AS earliest_billing,
                        max(billing_end) AS latest_billing,
                        max(timestamp) AS latest_event
                    FROM {table}
                    WHERE workspace_id = :workspace_id
                      AND timestamp >= :start_time
                      AND timestamp < :end_time
                    GROUP BY resource_id
                    ORDER BY compute_cost + disk_cost DESC
                    """
                ),
                {
                    "workspace_id": 301,
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )
            row = result.one()

            assert row.compute_cost == Decimal("1.500000")
            assert row.disk_cost == Decimal("0.250000")
            assert row.compute_minutes == 30.25
            _assert_ms(row.earliest_billing, 100000)
            _assert_ms(row.latest_billing, 900000)
            _assert_ms(row.latest_event, 875000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_enum_filters_materialized_dates_and_grouped_time_ranges():
    table = _table_name("activity_logs")
    engine = _engine()

    first_request = datetime(2026, 1, 7, 8, 9, 10, 111000)
    last_request = datetime(2026, 1, 7, 8, 10, 11, 999000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        trace_id String,
                        actor_id UInt64,
                        auth_method Enum8('api_token' = 1, 'cookie_login' = 2),
                        ip_address String,
                        request_path String,
                        http_method Enum8('GET' = 1, 'POST' = 2, 'PUT' = 3, 'DELETE' = 4, 'PATCH' = 5),
                        response_code UInt16,
                        request_time DateTime64(3),
                        request_date Date MATERIALIZED toDate(request_time),
                        request_hour UInt8 MATERIALIZED toHour(request_time),
                        request_dow UInt8 MATERIALIZED toDayOfWeek(request_time)
                    )
                    ENGINE = MergeTree
                    PARTITION BY request_date
                    ORDER BY (actor_id, request_time)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, trace_id, actor_id, auth_method,
                        ip_address, request_path, http_method, response_code,
                        request_time
                    )
                    VALUES (
                        :snowflake_id, :trace_id, :actor_id, :auth_method,
                        :ip_address, :request_path, :http_method,
                        :response_code, :request_time
                    )
                    """
                ),
                [
                    {
                        "snowflake_id": 1,
                        "trace_id": "trace-redacted-1",
                        "actor_id": 900,
                        "auth_method": "api_token",
                        "ip_address": "198.51.100.10",
                        "request_path": "/api/resources/redacted/start",
                        "http_method": "POST",
                        "response_code": 202,
                        "request_time": first_request,
                    },
                    {
                        "snowflake_id": 2,
                        "trace_id": "trace-redacted-2",
                        "actor_id": 900,
                        "auth_method": "cookie_login",
                        "ip_address": "198.51.100.10",
                        "request_path": "/api/resources/redacted/stop",
                        "http_method": "DELETE",
                        "response_code": 204,
                        "request_time": last_request,
                    },
                ],
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        ip_address,
                        count(*) AS request_count,
                        min(request_time) AS first_seen,
                        max(request_time) AS last_seen,
                        any(request_date) AS sample_request_date,
                        any(request_hour) AS request_hour,
                        groupArray(http_method) AS methods
                    FROM {table}
                    WHERE actor_id = :actor_id
                      AND toDate(request_time) >= :start_date
                      AND (
                        request_path LIKE :start_path
                        OR request_path LIKE :stop_path
                      )
                    GROUP BY ip_address
                    ORDER BY last_seen DESC
                    """
                ),
                {
                    "actor_id": 900,
                    "start_date": date(2026, 1, 7),
                    "start_path": "%/start",
                    "stop_path": "%/stop",
                },
            )
            row = result.one()

            assert row.request_count == 2
            assert row.sample_request_date == date(2026, 1, 7)
            assert row.request_hour == 8
            assert set(row.methods) == {"POST", "DELETE"}
            _assert_ms(row.first_seen, 111000)
            _assert_ms(row.last_seen, 999000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_countif_avgif_aggregates_preserve_nullable_datetime64_values():
    table = _table_name("delivery_logs")
    engine = _engine()

    created_at = datetime(2026, 1, 8, 12, 0, 0, 333000)
    delivered_at = datetime(2026, 1, 8, 12, 0, 1, 777000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        endpoint_id UInt32,
                        workspace_id UInt32,
                        event_id String,
                        event_type String,
                        status String,
                        attempts UInt8 DEFAULT 0,
                        request_url String,
                        request_body String,
                        response_status UInt16 DEFAULT 0,
                        response_body String DEFAULT '',
                        error_message String DEFAULT '',
                        duration_ms UInt32 DEFAULT 0,
                        created_at DateTime64(3),
                        delivered_at Nullable(DateTime64(3)),
                        original_event_id String DEFAULT ''
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (workspace_id, created_at, event_id)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, endpoint_id, workspace_id, event_id,
                        event_type, status, attempts, request_url, request_body,
                        response_status, response_body, error_message,
                        duration_ms, created_at, delivered_at, original_event_id
                    )
                    VALUES (
                        :snowflake_id, :endpoint_id, :workspace_id, :event_id,
                        :event_type, :status, :attempts, :request_url,
                        :request_body, :response_status, :response_body,
                        :error_message, :duration_ms, :created_at,
                        :delivered_at, :original_event_id
                    )
                    """
                ),
                [
                    {
                        "snowflake_id": 1,
                        "endpoint_id": 1,
                        "workspace_id": 400,
                        "event_id": "event-redacted-1",
                        "event_type": "resource.updated",
                        "status": "success",
                        "attempts": 1,
                        "request_url": "https://example.invalid/hook",
                        "request_body": "{}",
                        "response_status": 200,
                        "response_body": "{}",
                        "error_message": "",
                        "duration_ms": 1444,
                        "created_at": created_at,
                        "delivered_at": delivered_at,
                        "original_event_id": "origin-redacted-1",
                    },
                    {
                        "snowflake_id": 2,
                        "endpoint_id": 1,
                        "workspace_id": 400,
                        "event_id": "event-redacted-2",
                        "event_type": "resource.updated",
                        "status": "failed",
                        "attempts": 2,
                        "request_url": "https://example.invalid/hook",
                        "request_body": "{}",
                        "response_status": 500,
                        "response_body": "redacted",
                        "error_message": "redacted error",
                        "duration_ms": 0,
                        "created_at": created_at,
                        "delivered_at": None,
                        "original_event_id": "origin-redacted-2",
                    },
                ],
            )

            result = await conn.execute(
                text(
                    f"""
                    WITH delivery_stats AS (
                        SELECT
                            count() AS total,
                            countIf(status = 'success') AS success_count,
                            countIf(status = 'failed') AS failed_count,
                            round(avgIf(duration_ms, duration_ms > 0)) AS avg_duration_ms,
                            maxIf(duration_ms, duration_ms > 0) AS max_duration_ms,
                            min(created_at) AS first_delivery_at,
                            max(created_at) AS last_delivery_at,
                            max(delivered_at) AS last_delivered_at
                        FROM {table}
                        WHERE endpoint_id = :endpoint_id AND workspace_id = :workspace_id
                    )
                    SELECT
                        total,
                        success_count,
                        failed_count,
                        avg_duration_ms,
                        max_duration_ms,
                        last_delivery_at,
                        last_delivered_at,
                        dateDiff('millisecond', first_delivery_at, last_delivered_at) AS elapsed_ms
                    FROM delivery_stats
                    """
                ),
                {"endpoint_id": 1, "workspace_id": 400},
            )
            row = result.one()

            assert row.total == 2
            assert row.success_count == 1
            assert row.failed_count == 1
            assert row.avg_duration_ms == 1444
            assert row.max_duration_ms == 1444
            assert row.elapsed_ms == 1444
            _assert_ms(row.last_delivery_at, 333000)
            _assert_ms(row.last_delivered_at, 777000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_sumif_maxif_and_streak_queries_return_expected_rows():
    table = _table_name("node_sync")
    engine = _engine()

    first_sync = datetime(2026, 1, 12, 12, 0, 0)
    second_sync = datetime(2026, 1, 12, 13, 0, 0)
    third_sync = datetime(2026, 1, 12, 14, 0, 0)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        node_id UInt32,
                        sync_time DateTime,
                        success UInt8,
                        error_message String DEFAULT '',
                        duration_ms UInt32,
                        node_version String,
                        controller_version String,
                        proxy_version String
                    )
                    ENGINE = MergeTree
                    ORDER BY (sync_time, node_id)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        node_id, sync_time, success, error_message, duration_ms,
                        node_version, controller_version, proxy_version
                    )
                    VALUES (
                        :node_id, :sync_time, :success, :error_message,
                        :duration_ms, :node_version, :controller_version,
                        :proxy_version
                    )
                    """
                ),
                [
                    {
                        "node_id": 42,
                        "sync_time": first_sync,
                        "success": 0,
                        "error_message": "redacted",
                        "duration_ms": 300,
                        "node_version": "1.0.0",
                        "controller_version": "1.0.0",
                        "proxy_version": "1.0.0",
                    },
                    {
                        "node_id": 42,
                        "sync_time": second_sync,
                        "success": 1,
                        "error_message": "",
                        "duration_ms": 100,
                        "node_version": "1.0.1",
                        "controller_version": "1.0.1",
                        "proxy_version": "1.0.1",
                    },
                    {
                        "node_id": 42,
                        "sync_time": third_sync,
                        "success": 1,
                        "error_message": "",
                        "duration_ms": 120,
                        "node_version": "1.0.1",
                        "controller_version": "1.0.1",
                        "proxy_version": "1.0.1",
                    },
                ],
            )

            summary = await conn.execute(
                text(
                    f"""
                    SELECT
                        count() AS total_checks,
                        sumIf(1, success = 1) AS successful_checks,
                        if(total_checks > 0, round(successful_checks / total_checks * 100, 2), 0) AS uptime_percent,
                        round(avg(duration_ms), 0) AS avg_duration_ms,
                        maxIf(sync_time, success = 1) AS last_online_at,
                        maxIf(sync_time, success = 0) AS last_offline_at
                    FROM {table}
                    WHERE node_id = :node_id
                    """
                ),
                {"node_id": 42},
            )
            row = summary.one()
            assert row.total_checks == 3
            assert row.successful_checks == 2
            assert float(row.uptime_percent) == 66.67
            assert row.avg_duration_ms == 173
            assert row.last_online_at == third_sync
            assert row.last_offline_at == first_sync

            streak_result = await conn.execute(
                text(
                    f"""
                    SELECT success
                    FROM {table}
                    WHERE node_id = :node_id
                    ORDER BY sync_time DESC
                    LIMIT :limit
                    """
                ),
                {"node_id": 42, "limit": 24},
            )
            streak = 0
            for (success,) in streak_result:
                if success:
                    streak += 1
                else:
                    break
            assert streak == 2

    finally:
        await _drop(engine, table)
        await engine.dispose()
