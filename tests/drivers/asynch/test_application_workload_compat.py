import asyncio
import enum as pyenum
import json
import os
import uuid
from datetime import date
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import bindparam
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.asyncio import create_async_engine

from clickhouse_sqlalchemy import engines
from clickhouse_sqlalchemy import Table
from clickhouse_sqlalchemy import types as ch_types


class _ProcessingState(pyenum.IntEnum):
    created = 1
    running = 2
    failed = 3


class _RedactedPayload(TypeDecorator):
    impl = ch_types.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps({"wrapped": value}, sort_keys=True)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)["wrapped"]


def _load_dotenv_test():
    candidates = []
    explicit = os.environ.get("TEST_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit))

    candidates.extend(parent / ".env.test" for parent in (Path.cwd(), *Path.cwd().parents))

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


def _table_name(prefix):
    return f"test_ch_compat_{prefix}_{uuid.uuid4().hex[:8]}"


def _fixed_hex(length):
    return "a" * length


def _uuid(index=1):
    return f"00000000-0000-4000-8000-{index:012d}"


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


async def _drop(engine, table):
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))


async def _execute_each(conn, statement, rows):
    if isinstance(rows, dict):
        await conn.execute(statement, rows)
        return

    for row in rows:
        await conn.execute(statement, row)


def _assert_ms(value, expected_microsecond):
    assert value.microsecond == expected_microsecond


@pytest.mark.asyncio
async def test_event_operation_timeline_keeps_nested_arrays_and_datetime64_ms():
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
async def test_event_pairing_window_query_keeps_datetime64_ms():
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
async def test_metered_usage_hourly_pagination_keeps_decimal_and_datetime64_ms():
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
async def test_metered_usage_invoice_summary_uses_sumif_and_datetime_bounds():
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
async def test_revision_history_fixed_string_uuid_json_and_hash_expressions():
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
async def test_attestation_rows_keep_fixed_string_nullable_and_verified_timestamps():
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
async def test_user_activity_enum_materialized_date_and_grouped_time_ranges():
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
async def test_webhook_delivery_aggregates_countif_avgif_and_nullable_datetime64_ms():
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
async def test_message_provider_logs_keep_arrays_nullable_datetime64_and_raw_json():
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


@pytest.mark.asyncio
async def test_payment_webhook_logs_filter_payload_like_and_datetime64_ms():
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
async def test_ip_risk_logs_keep_bool_json_and_datetime64_ms():
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
async def test_node_sync_uptime_queries_cover_sumif_maxif_and_streak_scan():
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


@pytest.mark.asyncio
async def test_account_recharge_events_keep_float64_and_datetime64_ms():
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
async def test_manual_uuid_conversion_supports_string_casts_and_python_uuid_values():
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


@pytest.mark.asyncio
async def test_type_decorator_runs_bind_and_result_processors_with_core_table():
    table_name = _table_name("typed_payload")
    engine = _engine()
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("id", ch_types.UInt64, primary_key=True),
        Column("payload", _RedactedPayload()),
        Column("created_at", ch_types.DateTime64(3)),
        engines.Memory(),
    )

    created_at = datetime(2026, 1, 15, 15, 16, 17, 864000)
    payload = {"kind": "redacted", "items": [1, 2, 3]}

    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
            await conn.run_sync(metadata.create_all)
            await conn.execute(
                table.insert(),
                {"id": 1, "payload": payload, "created_at": created_at},
            )

            processed = await conn.execute(
                select(table.c.id, table.c.payload, table.c.created_at)
                .where(table.c.id == 1)
            )
            row = processed.one()

            assert row.id == 1
            assert row.payload == payload
            _assert_ms(row.created_at, 864000)

            raw = await conn.execute(
                text(f"SELECT payload FROM {table_name} WHERE id = :id"),
                {"id": 1},
            )
            assert json.loads(raw.scalar_one()) == {"wrapped": payload}

    finally:
        await _drop(engine, table_name)
        await engine.dispose()


@pytest.mark.asyncio
async def test_enum_type_roundtrip_with_python_intenum_and_low_cardinality_text():
    table_name = _table_name("enum_state")
    engine = _engine()
    metadata = MetaData()
    table = Table(
        table_name,
        metadata,
        Column("id", ch_types.UInt64, primary_key=True),
        Column("state", ch_types.Enum8(_ProcessingState)),
        Column("category", ch_types.LowCardinality(ch_types.String)),
        Column("created_at", ch_types.DateTime64(3)),
        engines.Memory(),
    )

    created_at = datetime(2026, 1, 16, 16, 17, 18, 975000)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
            await conn.run_sync(metadata.create_all)
            await conn.execute(
                table.insert(),
                {
                    "id": 1,
                    "state": _ProcessingState.running,
                    "category": "background",
                    "created_at": created_at,
                },
            )

            result = await conn.execute(
                select(table.c.id, table.c.state, table.c.category, table.c.created_at)
                .where(table.c.state == _ProcessingState.running)
            )
            row = result.one()

            assert row.id == 1
            assert row.state == _ProcessingState.running
            assert row.category == "background"
            _assert_ms(row.created_at, 975000)

            grouped = await conn.execute(
                text(
                    f"""
                    SELECT state, category, count() AS count
                    FROM {table_name}
                    WHERE state IN :states
                    GROUP BY state, category
                    """
                ),
                {"states": ("running", "failed")},
            )
            grouped_row = grouped.one()
            assert grouped_row.state == "running"
            assert grouped_row.category == "background"
            assert grouped_row.count == 1

    finally:
        await _drop(engine, table_name)
        await engine.dispose()


@pytest.mark.asyncio
async def test_asyncio_gather_concurrent_inserts_and_queries_preserve_results():
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
async def test_announcement_targeting_tables_support_enum_joins_and_counts():
    targets = _table_name("announcement_targets")
    affected = _table_name("announcement_affected")
    sends = _table_name("announcement_sends")
    engine = _engine()
    created_at = datetime(2026, 1, 18, 18, 0, 0)

    try:
        async with engine.begin() as conn:
            for table in (sends, affected, targets):
                await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {targets} (
                        announcement_id UInt32,
                        target_type Enum8('group' = 1, 'workspace' = 2, 'actor' = 3, 'node' = 4),
                        target_id UInt32,
                        created_at DateTime DEFAULT now()
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (announcement_id, target_type, target_id)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {affected} (
                        announcement_id UInt32,
                        actor_id UInt32,
                        actor_email String,
                        affect_reason Enum8('direct_actor' = 1, 'via_group' = 2, 'via_workspace' = 3, 'via_node' = 4),
                        source_id UInt32,
                        created_at DateTime DEFAULT now()
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (announcement_id, actor_id)
                    """
                )
            )
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {sends} (
                        announcement_id UInt32,
                        actor_id UInt32,
                        actor_email String,
                        provider_message_id String,
                        batch_id String,
                        sent_at DateTime DEFAULT now()
                    )
                    ENGINE = MergeTree
                    PARTITION BY toYYYYMM(sent_at)
                    ORDER BY (announcement_id, actor_id)
                    """
                )
            )

            await conn.execute(
                text(
                    f"""
                    INSERT INTO {targets} (
                        announcement_id, target_type, target_id, created_at
                    )
                    VALUES (
                        :announcement_id, :target_type, :target_id, :created_at
                    )
                    """
                ),
                {
                    "announcement_id": 1,
                    "target_type": "node",
                    "target_id": 501,
                    "created_at": created_at,
                },
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {affected} (
                        announcement_id, actor_id, actor_email, affect_reason,
                        source_id, created_at
                    )
                    VALUES (
                        :announcement_id, :actor_id, :actor_email,
                        :affect_reason, :source_id, :created_at
                    )
                    """
                ),
                {
                    "announcement_id": 1,
                    "actor_id": 601,
                    "actor_email": "actor@example.invalid",
                    "affect_reason": "via_node",
                    "source_id": 501,
                    "created_at": created_at,
                },
            )
            await conn.execute(
                text(
                    f"""
                    INSERT INTO {sends} (
                        announcement_id, actor_id, actor_email,
                        provider_message_id, batch_id, sent_at
                    )
                    VALUES (
                        :announcement_id, :actor_id, :actor_email,
                        :provider_message_id, :batch_id, :sent_at
                    )
                    """
                ),
                {
                    "announcement_id": 1,
                    "actor_id": 601,
                    "actor_email": "actor@example.invalid",
                    "provider_message_id": "message-redacted",
                    "batch_id": "batch-redacted",
                    "sent_at": created_at,
                },
            )

            result = await conn.execute(
                text(
                    f"""
                    SELECT
                        t.target_type,
                        a.affect_reason,
                        count() AS affected_count,
                        countIf(s.provider_message_id != '') AS sent_count,
                        groupArray(a.actor_email) AS actor_emails
                    FROM {targets} AS t
                    INNER JOIN {affected} AS a
                        ON t.announcement_id = a.announcement_id
                       AND t.target_id = a.source_id
                    LEFT JOIN {sends} AS s
                        ON a.announcement_id = s.announcement_id
                       AND a.actor_id = s.actor_id
                    WHERE t.target_type IN :target_types
                    GROUP BY t.target_type, a.affect_reason
                    """
                ),
                {"target_types": ("node", "workspace")},
            )
            row = result.one()

            assert row.target_type == "node"
            assert row.affect_reason == "via_node"
            assert row.affected_count == 1
            assert row.sent_count == 1
            assert row.actor_emails == ["actor@example.invalid"]

    finally:
        for table in (sends, affected, targets):
            await _drop(engine, table)
        await engine.dispose()


@pytest.mark.asyncio
async def test_registration_logs_preserve_header_json_and_datetime_filtering():
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


@pytest.mark.asyncio
async def test_billing_records_view_and_hourly_summary_materialized_view():
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
async def test_mutation_update_and_delete_with_bound_datetime64_values():
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
async def test_audit_queries_cover_interpolated_in_lists_dates_and_api_path_matching():
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
async def test_expanding_bindparams_for_last_activity_queries():
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


@pytest.mark.asyncio
async def test_raw_generated_usage_insert_sql_preserves_decimal_literals_and_escaping():
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


@pytest.mark.xfail(
    reason="textual executemany with native INSERT placeholder substitution not yet supported"
)
@pytest.mark.asyncio
async def test_textual_executemany_insert_supports_multiple_parameter_rows():
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
async def test_textual_insert_multiple_rows_one_by_one():
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
