from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_grouped_pagination_preserves_decimal_and_datetime64_values():
    table = _table_name("metered_usage")
    engine = _engine()

    event_ts = datetime(2026, 1, 3, 4, 5, 6, 789000)
    billing_start = datetime(2026, 1, 3, 4, 0, 0, 250000)
    billing_end = datetime(2026, 1, 3, 5, 0, 0, 750000)

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
                        event_type String,
                        cost Decimal64(6),
                        details String,
                        usage_type String DEFAULT 'combined',
                        billing_start DateTime64(3),
                        billing_end DateTime64(3),
                        duration_minutes Float64,
                        billing_key String DEFAULT '',
                        resource_type String DEFAULT '',
                        hourly_rate Decimal64(6) DEFAULT 0,
                        billing_hour DateTime MATERIALIZED toStartOfHour(timestamp),
                        billing_day Date MATERIALIZED toDate(timestamp),
                        version UInt64 DEFAULT toUnixTimestamp64Milli(now64())
                    )
                    ENGINE = ReplacingMergeTree(version)
                    PARTITION BY toYYYYMM(timestamp)
                    ORDER BY (resource_id, toStartOfHour(billing_start), usage_type, event_type)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, resource_id, workspace_id, timestamp,
                        event_type, cost, details, usage_type, billing_start,
                        billing_end, duration_minutes, billing_key,
                        resource_type, hourly_rate
                    )
                    VALUES (
                        :snowflake_id, :resource_id, :workspace_id, :timestamp,
                        :event_type, :cost, :details, :usage_type,
                        :billing_start, :billing_end, :duration_minutes,
                        :billing_key, :resource_type, :hourly_rate
                    )
                    """
                ),
                [
                    {
                        "snowflake_id": 1,
                        "resource_id": "resource-usage-1",
                        "workspace_id": 300,
                        "timestamp": event_ts,
                        "event_type": "compute",
                        "cost": Decimal("0.123456"),
                        "details": "redacted compute usage",
                        "usage_type": "compute",
                        "billing_start": billing_start,
                        "billing_end": billing_end,
                        "duration_minutes": 60.5,
                        "billing_key": "usage-key-1",
                        "resource_type": "standard-medium",
                        "hourly_rate": Decimal("0.122000"),
                    },
                    {
                        "snowflake_id": 2,
                        "resource_id": "resource-usage-1",
                        "workspace_id": 300,
                        "timestamp": event_ts,
                        "event_type": "storage",
                        "cost": Decimal("0.001111"),
                        "details": "redacted storage usage",
                        "usage_type": "disk",
                        "billing_start": billing_start,
                        "billing_end": billing_end,
                        "duration_minutes": 60.5,
                        "billing_key": "usage-key-2",
                        "resource_type": "standard-medium",
                        "hourly_rate": Decimal("0.002000"),
                    },
                ],
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        billing_hour AS hour,
                        sum(cost) AS total_cost,
                        groupArray(DISTINCT event_type) AS event_types,
                        min(billing_start) AS earliest_billing,
                        max(billing_end) AS latest_billing,
                        dateDiff('millisecond', min(billing_start), max(billing_end)) AS billing_duration_ms,
                        any(timestamp) AS sample_timestamp
                    FROM {table}
                    WHERE workspace_id = :workspace_id
                      AND event_type IN :event_types
                    GROUP BY billing_hour
                    ORDER BY billing_hour DESC
                    LIMIT :limit
                    """
                ),
                {
                    "workspace_id": 300,
                    "event_types": ("compute", "storage"),
                    "limit": 10,
                },
            )
            row = result.one()

            assert row.total_cost == Decimal("0.124567")
            assert set(row.event_types) == {"compute", "storage"}
            assert row.billing_duration_ms == 3600500
            _assert_ms(row.earliest_billing, 250000)
            _assert_ms(row.latest_billing, 750000)
            _assert_ms(row.sample_timestamp, 789000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_fixed_string_uuid_json_and_hash_expressions_round_trip():
    table = _table_name("revision_history")
    engine = _engine()

    created_at = datetime(2026, 1, 5, 2, 3, 4, 789000)
    compose_payload = json.dumps(
        {
            "config_file": "services:\n  worker:\n    image: redacted/image:1",
            "startup_script": "#!/bin/sh\necho redacted",
            "search_text": "needle-redacted",
        }
    )

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        table_id Int32,
                        application_id FixedString(40),
                        resource_uuid UUID,
                        compose_hash String,
                        compose_file String,
                        encrypted_env String,
                        user_config String,
                        created_at DateTime64(3, 'UTC'),
                        trace_id Nullable(UUID),
                        operation_type LowCardinality(String),
                        triggered_by Nullable(Int32),
                        config_file_hash Nullable(String),
                        startup_script_hash Nullable(String)
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (table_id, resource_uuid, created_at)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, table_id, application_id, resource_uuid,
                        compose_hash, compose_file, encrypted_env, user_config,
                        created_at, trace_id, operation_type, triggered_by,
                        config_file_hash, startup_script_hash
                    )
                    VALUES (
                        :snowflake_id, :table_id, :application_id, :resource_uuid,
                        :compose_hash, :compose_file, :encrypted_env,
                        :user_config, :created_at, :trace_id, :operation_type,
                        :triggered_by, :config_file_hash, :startup_script_hash
                    )
                    """
                ),
                {
                    "snowflake_id": 10,
                    "table_id": 700,
                    "application_id": _fixed_hex(40),
                    "resource_uuid": _uuid(10),
                    "compose_hash": "compose-redacted",
                    "compose_file": compose_payload,
                    "encrypted_env": "encrypted-redacted",
                    "user_config": "{}",
                    "created_at": created_at,
                    "trace_id": _uuid(11),
                    "operation_type": "deploy",
                    "triggered_by": 701,
                    "config_file_hash": None,
                    "startup_script_hash": None,
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        snowflake_id,
                        application_id,
                        resource_uuid,
                        compose_hash,
                        JSONExtractString(compose_file, 'config_file') AS config_file,
                        JSONExtractString(compose_file, 'startup_script') AS startup_script,
                        lower(hex(SHA256(JSONExtractString(compose_file, 'config_file')))) AS computed_config_hash,
                        lower(hex(SHA256(JSONExtractString(compose_file, 'startup_script')))) AS computed_script_hash,
                        created_at,
                        trace_id,
                        operation_type,
                        triggered_by
                    FROM {table}
                    WHERE application_id = :application_id
                      AND JSONExtractString(compose_file, 'search_text') LIKE :term
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {
                    "application_id": _fixed_hex(40),
                    "term": "%needle%",
                    "limit": 10,
                    "offset": 0,
                },
            )
            row = result.one()

            assert row.snowflake_id == 10
            assert str(row.resource_uuid) == _uuid(10)
            assert row.operation_type == "deploy"
            assert row.triggered_by == 701
            assert row.config_file.startswith("services:")
            assert row.startup_script.startswith("#!/bin/sh")
            assert len(row.computed_config_hash) == 64
            assert len(row.computed_script_hash) == 64
            _assert_ms(row.created_at, 789000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_bool_json_and_datetime64_values_round_trip():
    table = _table_name("network_risk")
    engine = _engine()

    created_at = datetime(2026, 1, 11, 11, 12, 13, 456000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        ip String,
                        score UInt32,
                        risk String,
                        is_datacenter Bool,
                        is_vpn Bool,
                        is_private_relay Bool,
                        is_cloud_provider Bool,
                        is_blacklisted_external Bool,
                        raw_payload String,
                        created_at DateTime64(3)
                    )
                    ENGINE = MergeTree
                    ORDER BY ip
                    """
                )
            )

            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        ip, score, risk, is_datacenter, is_vpn,
                        is_private_relay, is_cloud_provider,
                        is_blacklisted_external, raw_payload, created_at
                    )
                    VALUES (
                        :ip, :score, :risk, :is_datacenter, :is_vpn,
                        :is_private_relay, :is_cloud_provider,
                        :is_blacklisted_external, :raw_payload, :created_at
                    )
                    """
                ),
                {
                    "ip": "203.0.113.44",
                    "score": 75,
                    "risk": "medium",
                    "is_datacenter": True,
                    "is_vpn": False,
                    "is_private_relay": False,
                    "is_cloud_provider": True,
                    "is_blacklisted_external": False,
                    "raw_payload": json.dumps({"source": "redacted", "score": 75}),
                    "created_at": created_at,
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        ip,
                        avg(score) AS avg_score,
                        max(is_datacenter) AS any_datacenter,
                        max(is_cloud_provider) AS any_cloud_provider,
                        JSONExtractInt(raw_payload, 'score') AS payload_score,
                        min(created_at) AS first_seen
                    FROM {table}
                    WHERE ip = :ip
                    GROUP BY ip, raw_payload
                    """
                ),
                {"ip": "203.0.113.44"},
            )
            row = result.one()

            assert row.avg_score == 75
            assert row.any_datacenter == 1
            assert row.any_cloud_provider == 1
            assert row.payload_score == 75
            _assert_ms(row.first_seen, 456000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_float64_amounts_and_datetime64_values_round_trip():
    table = _table_name("account_events")
    engine = _engine()

    timestamp = datetime(2026, 1, 13, 13, 14, 15, 246000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        event_id String,
                        transaction_id String,
                        timestamp DateTime64(3),
                        actor_id UInt64,
                        balance_before Float64,
                        balance_after Float64,
                        transfer_amount Float64,
                        status String DEFAULT 'success',
                        error_message String DEFAULT ''
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(timestamp)
                    ORDER BY (timestamp, actor_id, event_id)
                    """
                )
            )

            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, event_id, transaction_id, timestamp,
                        actor_id, balance_before, balance_after, transfer_amount,
                        status, error_message
                    )
                    VALUES (
                        :snowflake_id, :event_id, :transaction_id, :timestamp,
                        :actor_id, :balance_before, :balance_after,
                        :transfer_amount, :status, :error_message
                    )
                    """
                ),
                {
                    "snowflake_id": 1,
                    "event_id": "account-event-redacted",
                    "transaction_id": "transaction-redacted",
                    "timestamp": timestamp,
                    "actor_id": 800,
                    "balance_before": 10.25,
                    "balance_after": 7.75,
                    "transfer_amount": 2.5,
                    "status": "success",
                    "error_message": "",
                },
            )

            verify = await conn.execute(
                text(
                    f"""
                    SELECT count()
                    FROM {table}
                    WHERE event_id = :event_id
                    """
                ),
                {"event_id": "account-event-redacted"},
            )
            assert verify.scalar_one() == 1

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        actor_id,
                        sum(transfer_amount) AS total_transfer,
                        min(balance_after) AS min_balance_after,
                        max(timestamp) AS last_event_at
                    FROM {table}
                    WHERE actor_id = :actor_id
                    GROUP BY actor_id
                    """
                ),
                {"actor_id": 800},
            )
            row = result.one()

            assert row.total_transfer == 2.5
            assert row.min_balance_after == 7.75
            _assert_ms(row.last_event_at, 246000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_uuid_values_accept_strings_casts_and_python_uuid_objects():
    table = _table_name("manual_uuid")
    engine = _engine()

    resource_uuid = uuid.UUID(_uuid(21))
    trace_uuid = uuid.UUID(_uuid(22))
    created_at = datetime(2026, 1, 14, 14, 15, 16, 135000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        resource_uuid UUID,
                        trace_uuid Nullable(UUID),
                        created_at DateTime64(3)
                    )
                    ENGINE = MergeTree
                    ORDER BY (resource_uuid, created_at)
                    """
                )
            )

            await conn.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, resource_uuid, trace_uuid, created_at
                    )
                    VALUES (
                        :snowflake_id, :resource_uuid, :trace_uuid, :created_at
                    )
                    """
                ),
                {
                    "snowflake_id": 1,
                    "resource_uuid": resource_uuid,
                    "trace_uuid": trace_uuid,
                    "created_at": created_at,
                },
            )

            by_uuid = await conn.execute(
                text(
                    f"""
                    SELECT
                        resource_uuid,
                        trace_uuid,
                        toString(resource_uuid) AS resource_uuid_text,
                        toString(trace_uuid) AS trace_uuid_text,
                        created_at
                    FROM {table}
                    WHERE resource_uuid = :resource_uuid
                    """
                ),
                {"resource_uuid": resource_uuid},
            )
            row = by_uuid.one()

            assert uuid.UUID(str(row.resource_uuid)) == resource_uuid
            assert uuid.UUID(str(row.trace_uuid)) == trace_uuid
            assert uuid.UUID(row.resource_uuid_text) == resource_uuid
            assert uuid.UUID(row.trace_uuid_text) == trace_uuid
            _assert_ms(row.created_at, 135000)

            by_string = await conn.execute(
                text(
                    f"""
                    SELECT count()
                    FROM {table}
                    WHERE resource_uuid = toUUID(:resource_uuid_text)
                    """
                ),
                {"resource_uuid_text": str(resource_uuid)},
            )
            assert by_string.scalar_one() == 1

    finally:
        await _drop(engine, table)
        await engine.dispose()
