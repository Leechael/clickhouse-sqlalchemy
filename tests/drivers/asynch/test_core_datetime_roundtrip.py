from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_select_returns_nested_arrays_and_datetime64_milliseconds():
    table = _table_name("event_timeline")
    engine = _engine()

    started_at = datetime(2026, 1, 1, 0, 0, 0, 123000)
    failed_at = datetime(2026, 1, 1, 0, 0, 1, 234000)
    completed_at = datetime(2026, 1, 1, 0, 0, 2, 456000)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        message_id String,
                        event_type String,
                        resource_id String,
                        timestamp DateTime64(3),
                        priority String,
                        workspace_id UInt64,
                        actor_id UInt64,
                        resource_name String,
                        state String,
                        resource_type String,
                        old_resource_type Nullable(String),
                        new_resource_type Nullable(String),
                        `tags.key` Array(String),
                        `tags.value` Array(String),
                        `network_interfaces.id` Array(String),
                        `network_interfaces.public_ip` Array(Nullable(String)),
                        `network_interfaces.security_groups` Array(Array(String)),
                        `block_devices.device_name` Array(String),
                        `block_devices.size_gb` Array(UInt32),
                        `block_devices.delete_on_termination` Array(UInt8),
                        operation_payload String DEFAULT '',
                        target_state String DEFAULT '',
                        operation_type String DEFAULT '',
                        correlation_id String DEFAULT '',
                        compose_hash String DEFAULT '',
                        duration_seconds UInt32 DEFAULT 0
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(timestamp)
                    ORDER BY (timestamp, resource_id, message_id)
                    """
                )
            )

            insert = text(
                f"""
                INSERT INTO {table} (
                    snowflake_id, message_id, event_type, resource_id, timestamp,
                    priority, workspace_id, actor_id, resource_name, state,
                    resource_type, old_resource_type, new_resource_type,
                    `tags.key`, `tags.value`,
                    `network_interfaces.id`, `network_interfaces.public_ip`,
                    `network_interfaces.security_groups`,
                    `block_devices.device_name`, `block_devices.size_gb`,
                    `block_devices.delete_on_termination`, operation_payload,
                    target_state, operation_type, correlation_id, compose_hash,
                    duration_seconds
                )
                VALUES (
                    :snowflake_id, :message_id, :event_type, :resource_id,
                    :timestamp, :priority, :workspace_id, :actor_id,
                    :resource_name, :state, :resource_type, :old_resource_type,
                    :new_resource_type, :tags_key, :tags_value,
                    :network_interface_ids, :network_interface_public_ips,
                    :network_interface_security_groups,
                    :block_device_names, :block_device_sizes,
                    :block_device_delete_flags, :operation_payload,
                    :target_state, :operation_type, :correlation_id,
                    :compose_hash, :duration_seconds
                )
                """
            )

            common = {
                "resource_id": "resource-0001",
                "priority": "normal",
                "workspace_id": 101,
                "actor_id": 202,
                "resource_name": "redacted-resource",
                "resource_type": "standard-small",
                "target_state": "running",
                "operation_type": "resize",
                "correlation_id": "corr-redacted-001",
                "compose_hash": "hash-redacted",
                "network_interface_ids": ["net-1", "net-2"],
                "network_interface_public_ips": [None, "203.0.113.10"],
                "network_interface_security_groups": [["sg-a"], ["sg-a", "sg-b"]],
                "block_device_names": ["root", "data"],
                "block_device_sizes": [40, 80],
                "block_device_delete_flags": [1, 0],
            }
            await conn.execute(
                insert,
                {
                    **common,
                    "snowflake_id": 1,
                    "message_id": "msg-start",
                    "event_type": "resource.resize.start",
                    "timestamp": started_at,
                    "state": "resizing",
                    "old_resource_type": "standard-small",
                    "new_resource_type": "standard-medium",
                    "tags_key": ["phase", "component"],
                    "tags_value": ["start", "control"],
                    "operation_payload": json.dumps({"cpu": 4, "memory": 8192}),
                    "duration_seconds": 0,
                },
            )
            await conn.execute(
                insert,
                {
                    **common,
                    "snowflake_id": 2,
                    "message_id": "msg-error",
                    "event_type": "resource.resize.error",
                    "timestamp": failed_at,
                    "state": "recovering",
                    "old_resource_type": None,
                    "new_resource_type": None,
                    "tags_key": ["Error", "phase"],
                    "tags_value": ["redacted failure detail", "retry"],
                    "operation_payload": "",
                    "duration_seconds": 1,
                },
            )
            await conn.execute(
                insert,
                {
                    **common,
                    "snowflake_id": 3,
                    "message_id": "msg-end",
                    "event_type": "resource.resize.end",
                    "timestamp": completed_at,
                    "state": "running",
                    "old_resource_type": None,
                    "new_resource_type": None,
                    "tags_key": ["phase"],
                    "tags_value": ["end"],
                    "operation_payload": "",
                    "duration_seconds": 2,
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    WITH operation_groups AS (
                        SELECT
                            correlation_id,
                            argMin(operation_type, timestamp) AS main_operation_type,
                            min(timestamp) AS started_at,
                            max(timestamp) AS completed_at,
                            dateDiff('millisecond', min(timestamp), max(timestamp)) AS duration_ms,
                            countIf(event_type LIKE '%.error') > 0 AS has_error,
                            anyIf(
                                arrayElement(tags.value, indexOf(tags.key, 'Error')),
                                event_type LIKE '%.error' AND has(tags.key, 'Error')
                            ) AS error_message,
                            arrayDistinct(
                                arrayMap(
                                    x -> tupleElement(x, 2),
                                    arraySort(groupArray((timestamp, operation_type)))
                                )
                            ) AS sub_operations,
                            arraySort(groupArray((timestamp, event_type, state))) AS events_data,
                            anyIf(operation_payload, event_type = 'resource.resize.start') AS resize_payload,
                            any(`network_interfaces.public_ip`) AS public_ips,
                            any(`network_interfaces.security_groups`) AS security_groups
                        FROM {table}
                        WHERE resource_id = :resource_id
                          AND correlation_id != ''
                        GROUP BY correlation_id
                    )
                    SELECT
                        correlation_id,
                        main_operation_type,
                        started_at,
                        completed_at,
                        duration_ms,
                        has_error,
                        error_message,
                        sub_operations,
                        events_data,
                        resize_payload,
                        public_ips,
                        security_groups
                    FROM operation_groups
                    WHERE main_operation_type IN :operation_types
                    """
                ),
                {
                    "resource_id": "resource-0001",
                    "operation_types": ("resize",),
                },
            )
            row = result.one()

            assert row.duration_ms == 2333
            assert row.has_error == 1
            assert row.error_message == "redacted failure detail"
            assert row.sub_operations == ["resize"]
            assert json.loads(row.resize_payload)["cpu"] == 4
            assert row.public_ips == [None, "203.0.113.10"]
            assert row.security_groups == [["sg-a"], ["sg-a", "sg-b"]]
            _assert_ms(row.started_at, 123000)
            _assert_ms(row.completed_at, 456000)
            _assert_ms(row.events_data[0][0], 123000)
            _assert_ms(row.events_data[1][0], 234000)
            _assert_ms(row.events_data[2][0], 456000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_nullable_fixed_string_rows_preserve_datetime64_timestamps():
    table = _table_name("attestation_rows")
    engine = _engine()

    created_at = datetime(2026, 1, 6, 6, 7, 8, 321000)
    verified_at = datetime(2026, 1, 6, 6, 7, 9, 654000)
    checksum = _fixed_hex(64)

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        version UInt32,
                        key_type String,
                        environment_type String,
                        vendor String,
                        user_data String,
                        content String,
                        cert_data Nullable(String),
                        checksum FixedString(64),
                        created_at DateTime64(3, 'UTC') DEFAULT now64(),
                        verified UInt8 DEFAULT 0,
                        verified_at DateTime64(3, 'UTC') DEFAULT created_at,
                        platform_id String DEFAULT ''
                    )
                    ENGINE = MergeTree
                    PRIMARY KEY created_at
                    ORDER BY created_at
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, version, key_type, environment_type,
                        vendor, user_data, content, cert_data, checksum,
                        created_at, verified, verified_at, platform_id
                    )
                    VALUES (
                        :snowflake_id, :version, :key_type, :environment_type,
                        :vendor, :user_data, :content, :cert_data, :checksum,
                        :created_at, :verified, :verified_at, :platform_id
                    )
                    """
                ),
                {
                    "snowflake_id": 20,
                    "version": 4,
                    "key_type": "KEY_TYPE_REDACTED",
                    "environment_type": "ENV_REDACTED",
                    "vendor": "0x" + "01" * 16,
                    "user_data": "0x" + "02" * 20,
                    "content": "0x" + "03" * 64,
                    "cert_data": None,
                    "checksum": checksum,
                    "created_at": created_at,
                    "verified": 1,
                    "verified_at": verified_at,
                    "platform_id": "platform-redacted",
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        checksum,
                        verified,
                        verified_at,
                        created_at,
                        content,
                        cert_data,
                        platform_id
                    FROM {table}
                    WHERE checksum IN (:checksum)
                    ORDER BY created_at ASC
                    LIMIT :limit
                    """
                ),
                {"checksum": checksum, "limit": 50},
            )
            row = result.one()

            assert row.checksum == checksum
            assert row.verified == 1
            assert row.content.startswith("0x")
            assert row.cert_data is None
            assert row.platform_id == "platform-redacted"
            _assert_ms(row.created_at, 321000)
            _assert_ms(row.verified_at, 654000)

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_arrays_nullable_datetime64_and_raw_json_round_trip():
    table = _table_name("message_events")
    engine = _engine()

    created_at = datetime(2026, 1, 9, 9, 1, 2, 345000)
    data_created_at = datetime(2026, 1, 9, 9, 1, 1, 987000)
    payload = {
        "type": "message.delivered",
        "data": {
            "message_id": "msg-redacted",
            "to": ["recipient@example.invalid", "audit@example.invalid"],
        },
    }

    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        event_type String,
                        created_at DateTime64(3),
                        message_id Nullable(String),
                        sender Nullable(String),
                        recipients Array(String),
                        subject Nullable(String),
                        data_created_at Nullable(DateTime64(3)),
                        raw_payload String
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (created_at, event_type)
                    """
                )
            )

            await _execute_each(
                conn,
                text(
                    f"""
                    INSERT INTO {table} (
                        snowflake_id, event_type, created_at, message_id,
                        sender, recipients, subject, data_created_at, raw_payload
                    )
                    VALUES (
                        :snowflake_id, :event_type, :created_at, :message_id,
                        :sender, :recipients, :subject, :data_created_at,
                        :raw_payload
                    )
                    """
                ),
                {
                    "snowflake_id": 1,
                    "event_type": "message.delivered",
                    "created_at": created_at,
                    "message_id": "msg-redacted",
                    "sender": "sender@example.invalid",
                    "recipients": ["recipient@example.invalid", "audit@example.invalid"],
                    "subject": "redacted subject",
                    "data_created_at": data_created_at,
                    "raw_payload": json.dumps(payload),
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        event_type,
                        created_at,
                        data_created_at,
                        message_id,
                        has(recipients, :recipient) AS matched_recipient,
                        JSONExtractString(raw_payload, 'type') AS payload_type,
                        JSONExtractString(raw_payload, 'data', 'message_id') AS payload_message_id
                    FROM {table}
                    WHERE has(recipients, :recipient)
                      AND event_type = :event_type
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "recipient": "recipient@example.invalid",
                    "event_type": "message.delivered",
                },
            )
            row = result.one()

            assert row.matched_recipient == 1
            assert row.payload_type == "message.delivered"
            assert row.payload_message_id == "msg-redacted"
            _assert_ms(row.created_at, 345000)
            _assert_ms(row.data_created_at, 987000)

    finally:
        await _drop(engine, table)
        await engine.dispose()
