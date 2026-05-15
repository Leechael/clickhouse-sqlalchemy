from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_filter_pagination_gap_and_argmax_queries_return_expected_rows():
    table = _table_name("sync_monitoring")
    engine = _engine()

    try:
        async with engine.begin() as conn:
            now_result = await conn.execute(text("SELECT now()"))
            current_minute = now_result.scalar_one().replace(second=0, microsecond=0)
            first_sync = current_minute - timedelta(minutes=5)
            first_failure = current_minute - timedelta(minutes=4)
            second_failure = current_minute - timedelta(minutes=3)
            last_sync = current_minute - timedelta(minutes=2)

            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            await conn.execute(
                text(
                    f"""
                    CREATE TABLE {table} (
                        snowflake_id UInt64,
                        node_id UInt32,
                        sync_time DateTime,
                        success UInt8,
                        error_message String DEFAULT '',
                        duration_ms UInt32,
                        node_version String,
                        controller_version String DEFAULT '',
                        proxy_version String DEFAULT ''
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
                        snowflake_id, node_id, sync_time, success, error_message,
                        duration_ms, node_version, controller_version, proxy_version
                    )
                    VALUES (
                        :snowflake_id, :node_id, :sync_time, :success,
                        :error_message, :duration_ms, :node_version,
                        :controller_version, :proxy_version
                    )
                    """
                ),
                [
                    {
                        "snowflake_id": 1,
                        "node_id": 7,
                        "sync_time": first_sync,
                        "success": 1,
                        "error_message": "",
                        "duration_ms": 90,
                        "node_version": "1.0.0",
                        "controller_version": "1.0.0",
                        "proxy_version": "1.0.0",
                    },
                    {
                        "snowflake_id": 2,
                        "node_id": 7,
                        "sync_time": first_failure,
                        "success": 0,
                        "error_message": "redacted timeout",
                        "duration_ms": 400,
                        "node_version": "1.0.0",
                        "controller_version": "1.0.0",
                        "proxy_version": "1.0.0",
                    },
                    {
                        "snowflake_id": 3,
                        "node_id": 8,
                        "sync_time": first_failure,
                        "success": 0,
                        "error_message": "redacted timeout",
                        "duration_ms": 420,
                        "node_version": "2.0.0",
                        "controller_version": "2.0.0",
                        "proxy_version": "2.0.0",
                    },
                    {
                        "snowflake_id": 4,
                        "node_id": 7,
                        "sync_time": second_failure,
                        "success": 0,
                        "error_message": "redacted timeout",
                        "duration_ms": 410,
                        "node_version": "1.0.1",
                        "controller_version": "1.0.1",
                        "proxy_version": "1.0.1",
                    },
                    {
                        "snowflake_id": 5,
                        "node_id": 8,
                        "sync_time": second_failure,
                        "success": 0,
                        "error_message": "redacted timeout",
                        "duration_ms": 430,
                        "node_version": "2.0.1",
                        "controller_version": "2.0.1",
                        "proxy_version": "2.0.1",
                    },
                    {
                        "snowflake_id": 6,
                        "node_id": 7,
                        "sync_time": last_sync,
                        "success": 1,
                        "error_message": "",
                        "duration_ms": 120,
                        "node_version": "1.0.2",
                        "controller_version": "1.0.2",
                        "proxy_version": "1.0.2",
                    },
                ],
            )

            conditions = (
                f"node_id = :node_id AND sync_time >= now() - INTERVAL :days DAY "
                "AND success = :success"
            )
            count_result = await conn.execute(
                text(f"SELECT count() FROM {table} WHERE {conditions}"),
                {"node_id": 7, "days": 1, "success": 0},
            )
            assert count_result.scalar_one() == 2

            page_result = await conn.execute(
                text(
                    f"""
                    SELECT sync_time, success, error_message, duration_ms, node_version
                    FROM {table}
                    WHERE {conditions}
                    ORDER BY sync_time DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                {
                    "node_id": 7,
                    "days": 1,
                    "success": 0,
                    "limit": 1,
                    "offset": 0,
                },
            )
            page_row = page_result.one()
            assert page_row.sync_time == second_failure
            assert page_row.success == 0
            assert page_row.error_message == "redacted timeout"
            assert page_row.node_version == "1.0.1"

            daily_result = await conn.execute(
                text(
                    f"""
                    SELECT
                        toDate(sync_time) AS date,
                        count() AS total_checks,
                        sumIf(1, success = 1) AS successful_checks,
                        round(avg(duration_ms), 0) AS avg_duration_ms
                    FROM {table}
                    WHERE node_id = :node_id
                      AND sync_time >= now() - INTERVAL :days DAY
                    GROUP BY date
                    ORDER BY date
                    """
                ),
                {"node_id": 7, "days": 1},
            )
            daily_row = daily_result.one()
            assert daily_row.total_checks == 4
            assert daily_row.successful_checks == 2
            assert daily_row.avg_duration_ms == 255

            outage_result = await conn.execute(
                text(
                    f"""
                    SELECT
                        min(sync_time) AS started_at,
                        max(sync_time) AS ended_at,
                        count() AS failed_checks
                    FROM (
                        SELECT
                            sync_time,
                            sync_time - toIntervalMinute(rowNumberInAllBlocks()) AS grp
                        FROM {table}
                        WHERE node_id = :node_id
                          AND sync_time >= now() - INTERVAL :days DAY
                          AND success = 0
                        ORDER BY sync_time
                    )
                    GROUP BY grp
                    ORDER BY started_at
                    """
                ),
                {"node_id": 7, "days": 1},
            )
            outage_row = outage_result.one()
            assert outage_row.started_at == first_failure
            assert outage_row.ended_at == second_failure
            assert outage_row.failed_checks == 2

            shared_outage_result = await conn.execute(
                text(
                    f"""
                    SELECT sync_time
                    FROM {table}
                    WHERE node_id IN :node_ids
                      AND sync_time >= now() - INTERVAL :days DAY
                    GROUP BY sync_time
                    HAVING countIf(success = 1) = 0
                       AND count() >= :node_count
                    ORDER BY sync_time
                    """
                ),
                {
                    "node_ids": (7, 8),
                    "days": 1,
                    "node_count": 2,
                },
            )
            assert [row.sync_time for row in shared_outage_result] == [
                first_failure,
                second_failure,
            ]

            current_state_result = await conn.execute(
                text(
                    f"""
                    SELECT
                        node_id,
                        argMax(success, sync_time) AS current_success,
                        argMax(node_version, sync_time) AS current_version,
                        max(sync_time) AS last_sync_at
                    FROM {table}
                    WHERE node_id IN :node_ids
                    GROUP BY node_id
                    ORDER BY node_id
                    """
                ),
                {"node_ids": (7, 8)},
            )
            current_rows = current_state_result.fetchall()
            assert [(row.node_id, row.current_success) for row in current_rows] == [
                (7, 1),
                (8, 0),
            ]
            assert current_rows[0].current_version == "1.0.2"
            assert current_rows[0].last_sync_at == last_sync
            assert current_rows[1].current_version == "2.0.1"

    finally:
        await _drop(engine, table)
        await engine.dispose()

@pytest.mark.asyncio
async def test_enum_join_and_count_queries_return_expected_rows():
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
