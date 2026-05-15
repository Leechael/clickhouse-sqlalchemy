from tests.drivers.asynch._core_query_helpers import *  # noqa: F403

@pytest.mark.asyncio
async def test_type_decorator_processors_run_for_core_table_round_trip():
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
async def test_intenum_and_low_cardinality_enum_values_round_trip():
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
