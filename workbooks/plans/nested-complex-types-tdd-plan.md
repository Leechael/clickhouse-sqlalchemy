# Nested And Complex Types TDD Plan

## Goal

Fix the user-visible failures behind issues #101, #135, #269, and #328 without
turning the work into a full ClickHouse SQL parser or an unbounded Nested type
feature. Related insert/reflection issues #209 and #310 should be included in
the blast-radius test set because they touch the same batch-insert and quoted
type-argument paths.

The target outcome is:

- Existing supported ClickHouse types can be composed recursively in type
  expressions.
- Default ClickHouse `flatten_nested = 1` one-level `Nested` columns can be
  inserted through a clear SQLAlchemy-facing API.
- Reflection does not invent a logical `Nested` structure when ClickHouse
  reports flattened physical columns.
- Deeper `Nested` behavior is designed with `flatten_nested = 0` in mind, but
  not accidentally promised by the first implementation.

## Issue Mapping

- #101: Batch insert with Nested columns does not work as expected.
  - Primary path: `flatten_nested = 1`, one-level `Nested`, batch insert.
- #135: Nested not working.
  - Primary path: `types.Nested(...)` must survive SQLAlchemy type lifecycle
    and one-level usage.
- #269: Reflection fails on complex nested types.
  - Primary path: recursive type expression parsing for `Map`, `Nullable`,
    `Tuple`, and related supported types.
- #328: Nested maps, tuples, enums do not work.
  - Primary path: `Map(Enum8(...), String)`, nested `Tuple`, nested `Map`.
  - Secondary path: `Nested` children with complex supported types, subject to
    flattening rules.
- #209: KeyError when inserting list of dictionaries with SQLAlchemy Core.
  - Related path: batch insert parameter normalization must not regress when
    one-level `Nested` mappings are expanded.
- #310: DateTime64 timezone reflection gets extra quoted.
  - Related path: quoted type arguments must remain stable while making the
    recursive type splitter quote-aware.

## Premises And Constraints

### Official ClickHouse Behavior

ClickHouse defaults `flatten_nested` to `1`.

With `flatten_nested = 1`:

- `Nested(a T, b U)` is flattened into physical columns:
  - `parent.a Array(T)`
  - `parent.b Array(U)`
- This is the default user path.
- First-stage support is limited to one logical `Nested` level.

With `flatten_nested = 0`:

- `Nested(...)` remains a single column whose underlying shape is
  `Array(Tuple(...))`.
- ClickHouse documents arbitrary nesting as possible in this mode.
- This plan reserves the design path, but does not require full insert support
  in the first implementation.

### Boundary

Support only ClickHouse types already exposed by this package, such as:

- `Array`
- `Nullable`
- `LowCardinality`
- `Map`
- `Tuple`
- `Nested`
- `Enum8`
- `Enum16`
- `DateTime`
- `DateTime64`
- `Decimal*`
- `AggregateFunction`
- `SimpleAggregateFunction`

Do not parse arbitrary SQL.

Only parse type expressions returned by `DESCRIBE TABLE` or produced by the
package's type compiler.

Do not perform full ClickHouse semantic validation in Python. If ClickHouse
rejects a combination, the server remains the authority.

### Reflection Rule

Reflection must use `DESCRIBE TABLE` output as truth.

If ClickHouse reports:

```text
members.name Array(String)
members.age  Array(UInt8)
```

then reflection should initially return two array columns. It should not
silently reconstruct `members Nested(...)` during the first stage.

If ClickHouse reports:

```text
members Nested(name String, age UInt8)
```

then the type parser may return `types.Nested(...)`.

### Insert Rule

First-stage `Nested` insert support targets `flatten_nested = 1`.

Recommended user API:

```python
session.execute(table.insert(), [
    {
        "id": 1,
        "members": {
            "name": ["alice", "bob"],
            "age": [34, 29],
        },
    },
])
```

Equivalent low-level form may be accepted:

```python
session.execute(table.insert(), [
    {
        "id": 1,
        "members.name": ["alice", "bob"],
        "members.age": [34, 29],
    },
])
```

Out of scope for stage one:

```python
{"members": [{"name": "alice", "age": 34}]}
```

That row-oriented shape belongs to the future `flatten_nested = 0` path or an
explicit conversion feature.

If a user passes the row-oriented shape in stage one, fail early with a clear
error and an example of the supported mapping shape. Do not pass it through to
the driver silently.

### ORM Rule

Flattened reflection may expose dotted column names such as `members.name`.
Stage one only promises Core-level visibility and correct column typing for
those physical columns. ORM users may need explicit property mapping or quoted
column access. Automatically turning dotted reflected columns into ORM-friendly
logical attributes is out of scope for this plan.

## Current Diff Reconciliation

The current exploratory diff is ahead of this plan and has already gone through
more than one Stage 4 attempt.

Earlier exploratory helpers included:

- `_prepare_nested_insert`
- `_expand_nested_insert_statement`
- `_parse_insert_values`

Those helpers attempted to parse and rewrite compiled `INSERT` SQL text in the
execution layer. That path is rejected.

The current exploratory diff instead includes:

- `_prepare_flattened_nested_insert`
- `_expand_nested_insert_row`
- `_render_flattened_nested_insert`

This second attempt is structurally better because it uses SQLAlchemy
execution context, table metadata, and row parameters instead of regex-parsing
the already compiled statement. However, it is still Stage 4 behavior and is
still ahead of the TDD sequence unless it is preceded by the Stage 4
feasibility gate and public execution tests.

Default Stage 0 decision:

- Keep only tests that match the levels below.
- Keep `types.Nested` lifecycle fixes only if Level 3 tests require them.
- Keep recursive type parser changes only if Level 1 tests require them.
- Revert or defer all Stage 4 insert normalization before continuing with
  Stage 1, including the structured `_prepare_flattened_nested_insert` attempt
  unless the team explicitly chooses to keep it as a spike artifact outside the
  green path.

Reason:

- Parsing and rewriting `INSERT` text in `do_execute`/`do_executemany` is a
  mini SQL parser.
- It conflicts with the non-goal of avoiding arbitrary SQL parsing.
- It has known edge cases: schema-qualified names, quoted identifiers,
  `INSERT ... SELECT`, generated SQL with dialect-specific whitespace,
  single-row literal inserts, and native batch paths that remove `VALUES`
  templates.

Chosen Stage 4 direction:

- Prefer compile-time expansion if SQLAlchemy exposes a clean hook.
- If compile-time expansion is not feasible, allow a narrow structured
  execution-context normalization hook that:
  - uses `context.compiled.statement.table` and user row parameters;
  - renders a fresh, narrow `INSERT` from table metadata;
  - never inspects the old SQL string to discover table names, column lists, or
    values;
  - is covered by public `session.execute(table.insert(), rows)` tests.
- Do not accept regex-based or token-based compiled SQL rewriting unless this
  plan is amended with a small accepted grammar and explicit unsupported cases.

## TDD Strategy

Each stage starts by writing a failing test that describes the supported user
behavior. Implementation should be the smallest change that turns the test
green. Refactoring only follows after the behavior is covered.

```
RED:    Add one failing test for one user behavior.
GREEN:  Make the smallest code change to pass that test.
REFACTOR: Remove duplication and clarify parser boundaries.
```

Avoid adding broad helper abstractions before at least two tests force the same
shape.

## Test Levels

### Level 1: Pure Type Parser Tests

Fast unit tests against the dialect's type parsing path.

Purpose:

- Cover #269 and the parser half of #328.
- Avoid a real ClickHouse dependency.
- Prevent comma-splitting regressions inside nested parentheses or quoted enum
  labels.

Initial failing tests:

```text
test_reflect_map_of_map_nullable_value
test_reflect_map_with_enum_key
test_reflect_tuple_with_nested_tuple_and_map
test_reflect_named_tuple
test_reflect_datetime64_timezone_argument
test_reflect_aggregate_function_with_parameterized_function
test_reflect_simple_aggregate_function_with_tuple_argument
```

Representative inputs:

```text
Map(String, Map(String, Nullable(String)))
Map(Enum8('hello, world' = 1, 'plain' = 2), String)
Tuple(Tuple(String, UInt32), Map(String, Nullable(Int64)))
Tuple(name String, value Float32)
DateTime64(3, 'America/New_York')
AggregateFunction(quantiles(0.5, 0.9), UInt64)
SimpleAggregateFunction(maxMap, Tuple(Array(UInt32), Array(UInt32)))
```

Assertions:

- Top-level type class is correct.
- Nested type tree is correct.
- Enum values survive quoted labels and comma-containing enum labels.
- Quoted string arguments such as DateTime64 timezone values remain stable and
  are not double-quoted.
- No type degrades to `NullType` unless it is truly unknown.

Required implementation detail:

- The shared type-expression argument splitter must be quote-aware and
  escape-aware, not merely parenthesis-aware. `Map`, `Tuple`, `Nested`,
  `AggregateFunction`, `SimpleAggregateFunction`, and DateTime parameter
  parsing must not each invent incompatible splitting behavior.

### Level 2: DDL Compiler Symmetry Tests

Pure compile tests from Python type objects to ClickHouse DDL.

Purpose:

- Cover #328 from the create-table direction.
- Keep compiler behavior aligned with parser support.

Initial failing tests:

```text
test_compile_map_with_enum_key
test_compile_nested_tuple_and_map
test_compile_map_of_map_nullable_value
```

Representative Python declarations:

```python
types.Map(types.Enum8(Color), types.String)
types.Tuple(
    types.Tuple(types.String, types.UInt32),
    types.Map(types.String, types.Nullable(types.Int64)),
)
types.Map(
    types.String,
    types.Map(types.String, types.Nullable(types.String)),
)
```

Assertions:

- DDL contains the exact recursive type expression.
- Enum labels and numeric values render correctly.
- Existing simple type compile tests remain unchanged.

### Level 3: Nested Type Lifecycle Tests

Pure SQLAlchemy compile tests for `types.Nested`.

Purpose:

- Cover the #135 failure class where `Nested` is not usable as a SQLAlchemy
  type because copying/adapting drops its columns.
- Keep this separate from insert behavior.

Initial failing tests:

```text
test_nested_type_compiles_for_create_table
test_nested_type_compiles_for_insert_statement
test_nested_empty_columns_rejected
```

Assertions:

- `types.Nested(Column(...))` compiles in `CREATE TABLE`.
- `table.insert()` can compile without raising
  `ValueError: columns must be specified for nested type`.
- `types.Nested()` still raises `ValueError`.

### Level 4: Default Flattened Nested Integration Tests

Native and HTTP ClickHouse round-trip tests where feasible. These tests must
set the session explicitly:

```sql
SET flatten_nested = 1
```

Transport note:

- Native/asynch paths should set `flatten_nested` through the execution
  settings used by the driver for the DDL/DML under test. A bare
  `SET flatten_nested = 1` is not sufficient for every driver path because
  some settings are applied per query rather than as durable session state.
- HTTP may need driver settings/query parameters depending on the existing
  test fixture. The test must assert the setting before creating the table
  instead of relying on a global default.

Purpose:

- Cover #101 and the default ClickHouse user path.
- Confirm one-level Nested insert works with server behavior, not just string
  compilation.

Initial failing tests:

```text
test_flatten_nested_one_level_batch_insert_mapping_round_trip
test_flatten_nested_reflection_returns_array_subcolumns
```

Optional follow-up test:

```text
test_flatten_nested_one_level_direct_dotted_keys_round_trip
```

Do not make the dotted-key test part of the initial red set unless Stage 4 has
already proven the nested mapping API through public execution behavior. Dotted
keys are a compatibility convenience, not the primary API.

Feasibility note:

- A spike may show that SQLAlchemy drops unknown dotted keys for
  `table.insert()` before the dialect hook sees parameters. If so, direct
  dotted-key support is documented as unsupported in stage one rather than
  forcing a broad table/column adapter.

Table:

```sql
CREATE TABLE t (
    id UInt32,
    members Nested(name String, age UInt8)
) ENGINE = Memory
```

Mapping payload:

```python
[
    {
        "id": 1,
        "members": {
            "name": ["alice", "bob"],
            "age": [34, 29],
        },
    },
    {
        "id": 2,
        "members": {
            "name": ["carol"],
            "age": [41],
        },
    },
]
```

Expected query:

```sql
SELECT id, members.name, members.age FROM t ORDER BY id
```

Expected result:

```python
[
    (1, ["alice", "bob"], [34, 29]),
    (2, ["carol"], [41]),
]
```

Reflection assertions:

- `inspect(engine).get_columns("t")` returns `members.name` and `members.age`
  as array columns.
- It does not reconstruct a single `members` column in stage one.

Helper unit tests:

- Helper-level tests for parameter normalization may be added, but they are not
  a substitute for the round-trip tests above.
- Public execution unit tests with a mocked cursor may be added to prove the
  dialect transforms `session.execute(table.insert(), rows)` before the
  driver call. These tests support Stage 4 development, but they still do not
  replace a real ClickHouse round-trip.
- Existing tests that directly call private helpers such as
  `_prepare_nested_insert` or `_prepare_flattened_nested_insert` should either
  be rewritten around public compile/execution behavior, or clearly marked as
  helper tests that only support the integration coverage.
- Stage 4 is not accepted until a real ClickHouse insert round-trip with
  `flatten_nested = 1` passes.

Implementation preference:

- Prefer compile-time or structured parameter-normalization-time expansion.
- If using an execution-context hook, treat it as structured parameter
  normalization, not SQL parsing: the hook may use table metadata and row
  mappings, but must not parse the compiled SQL string.
- Apply or explicitly exclude each transport. In particular, HTTP, native, and
  asynch may not share the same `do_execute`/`do_executemany` implementation.
- If direct dotted-key insert is supported, prove it through public
  `session.execute(table.insert(), rows)` behavior, not only by testing a
  private helper.

Feasibility gate:

- Before implementing Stage 4, run a short spike that proves where SQLAlchemy
  still exposes structured insert columns and user parameters for
  `table.insert()` executemany.
- The spike must identify the exact hook to use, such as compiler/crud
  customization, an execution context pre-processing point before SQL text is
  finalized, or a table/type-level construct that causes child columns to be
  compiled structurally.
- If no structured hook can support the API, pause and amend this plan before
  accepting SQL text rewriting. Do not quietly fall back to regex-based
  `INSERT` rewriting.

Feasibility result:

- For `session.execute(table.insert(), rows)` with nested mapping payloads,
  the dialect execution hook still sees:
  - `context.compiled.statement.table`;
  - structured mapping parameters containing the logical `Nested` key;
  - `context.compiled_parameters`.
- Therefore Stage 4 may use a narrow execution-context normalization hook that
  expands `{"members": {"name": [...], "age": [...]}}` into
  `members.name` and `members.age` parameters and renders a fresh `INSERT`
  column list from table metadata.
- The hook must not inspect or parse the old compiled SQL string.
- A spike showed that direct dotted keys such as `members.name` are dropped by
  SQLAlchemy Core for `table.insert()` before the dialect sees parameters.
  Dotted-key insert is therefore not required in stage one.
- Native inherits the base dialect hook. Asynch overrides execute methods and
  must call the same helper explicitly. HTTP keeps a `VALUES` template because
  its cursor formats rows client-side; native/asynch keep the native
  `INSERT ... VALUES` shape for driver-side batch parameters.

### Level 5: `flatten_nested = 0` Design Guard Tests

These tests may initially be skipped or marked expected-fail until the second
stage is implemented.

Purpose:

- Keep future arbitrary-depth support visible.
- Avoid accidentally implementing flattened-only assumptions that block the
  unflattened path.

Potential tests:

```text
test_probe_unflattened_nested_describe_shape
test_unflattened_nested_describe_returns_nested_type
test_unflattened_nested_depth_three_type_parser
test_unflattened_nested_insert_not_supported_has_clear_error
```

Before asserting a fixed reflection shape, add an empirical probe test that
records:

- ClickHouse server version.
- Effective `flatten_nested` setting.
- `DESCRIBE TABLE` output for an unflattened nested table.

Only convert that probe into a hard assertion after the supported version range
is known. If versions differ, version-gate the test and document the observed
shape.

Setup:

```sql
SET flatten_nested = 0
CREATE TABLE t (
    n Nested(
        a UInt32,
        b Nested(
            c String,
            d Nested(e Date)
        )
    )
) ENGINE = Memory
```

Stage-one acceptable behavior:

- Type parser can parse the `Nested(...)` string if `DESCRIBE` returns it.
- Insert through SQLAlchemy may raise a clear `NotImplementedError` or warning
  for unflattened nested payloads.
- No silent mis-expansion into dotted arrays.

Stage-two target behavior:

```python
{"n": [{"a": 1, "b": [{"c": "x", "d": [{"e": date(2026, 1, 1)}]}]}]}
```

or a tuple-oriented shape aligned with `clickhouse-driver`.

The exact API must be designed separately before implementation.

## Implementation Sequence

### Stage 0: Reset Scope

Before implementation, review the existing exploratory diff and reduce it to
the chosen stage.

Keep:

- Tests that match this plan.
- Minimal `types.Nested` copy/adapt behavior only after Level 3 tests fail.
- Recursive type parser changes only after Level 1 tests fail.

Remove or defer:

- Broad Nested parser behavior not tied to explicit tests.
- Automatic reconstruction of flattened columns into `types.Nested`.
- Row-oriented Nested insert conversion.
- Execution-time `INSERT` string parsing or Stage 4 insert normalization in
  `do_execute`/`do_executemany`.
- Private helper tests that pretend to satisfy Stage 4 without a real insert
  round-trip.
- The current `tests/drivers/test_complex_types.py::NestedInsertTestCase`
  helper tests, unless they are rewritten as public compile/execution tests or
  moved under a clearly labeled helper-test section after integration coverage
  exists.

Default answer to "keep or revert the current Stage 4 diff":

- Revert/defer the regex SQL string rewriting path.
- Revert/defer the current structured `_prepare_flattened_nested_insert` path
  unless the immediate next work item is Stage 4 and it is driven by public
  execution tests.
- Reintroduce one-level flattened `Nested` insert only through tests that
  exercise public SQLAlchemy execution behavior, followed by real ClickHouse
  round-trip coverage.

Expected worktree shape after Stage 0:

- No execution-time `INSERT` string parsing helpers in `base.py`.
- No Stage 4 insert-normalization hook in the accepted green diff unless Stage
  4 tests are being implemented in the same slice.
- No private-helper-only tests claiming Stage 4 coverage.
- Parser and `Nested` lifecycle changes are either reverted, or are immediately
  preceded by matching red tests from Level 1 or Level 3.

### Stage 1: Recursive Non-Nested Type Parser

RED:

- Add Level 1 parser tests for `Map`, `Tuple`, `Enum`, aggregate functions.

GREEN:

- Replace ad hoc comma splitting in type reflection with a bracket-aware and
  quote-aware argument splitter. Concretely, update `parse_arguments` in
  `clickhouse_sqlalchemy/drivers/util.py` to recognize single quotes, double
  quotes, backticks, and backslash escapes. It is the shared splitter for
  `Map`, `Tuple`, `Nested`, `AggregateFunction`, and
  `SimpleAggregateFunction`; fixing it once fixes them all.
- Move the quote/whitespace bookkeeping currently embedded inside
  `ClickHouseDialect._parse_named_type_argument` into a sibling helper in
  the same `util.py` module so the comma splitter and the `name Type`
  splitter share one tested quoting contract instead of two ad hoc copies.
- Keep the parser limited to type expressions.

REFACTOR:

- Centralize type-expression argument splitting in `util.py`.
- Remove duplicated quote/escape handling from local parser helpers in
  `base.py`.
- Preserve existing simple type behavior.

Done when:

- Level 1 tests pass.
- Existing reflection tests pass.

### Stage 2: DDL Compiler Symmetry

RED:

- Add Level 2 compiler tests.

GREEN:

- Fix only compiler paths required by these recursive supported types.

REFACTOR:

- Avoid special casing combinations that the generic recursive compiler can
  already handle.

Done when:

- Level 2 tests pass.
- Existing DDL/compiler tests pass.

### Stage 3: Nested Type Lifecycle

RED:

- Add Level 3 tests for create table and insert compilation.

GREEN:

- Make `types.Nested` copy/adapt with its child columns intact.
- Preserve `types.Nested()` empty rejection.

REFACTOR:

- Keep lifecycle fixes inside the type class if possible.

Done when:

- `table.insert()` with a `Nested` column compiles.
- No insert semantics are added yet.

### Stage 4: Default Flattened Nested Insert

RED:

- Add Level 4 ClickHouse integration tests with explicit
  `SET flatten_nested = 1`.
- Add the nested mapping round-trip first. Add dotted-key coverage only after
  the primary mapping API works or after the open decision explicitly requires
  dotted-key support.

GREEN:

- First pass the Stage 4 feasibility gate and document the chosen structured
  hook in the implementation notes or test comments.
- Implement one-level mapping expansion for `types.Nested`.
- Ensure batch insert and single-row insert use the same path.
- Support direct dotted keys if they are already compatible with SQLAlchemy's
  execution path or can be handled with a small explicit adapter.
- Reject row-oriented payloads such as `{"members": [{"name": "alice"}]}` with
  a clear error and supported examples.

REFACTOR:

- Put expansion behind a clearly named helper.
- Guard it so it only applies to one-level `types.Nested` in flattened mode.
- Keep SQL generation structured. Do not parse and rewrite arbitrary compiled
  `INSERT` strings.

Done when:

- Batch insert round-trip passes.
- Reflection test confirms flattened array columns.
- The chosen insert hook is documented, and it is not regex-based compiled SQL
  rewriting.
- No two-level flattened Nested support is implied.
- Unsupported payload shapes fail early with a useful message.

### Stage 5: Unflattened Nested Future Guard

RED:

- Add skipped or expected-fail tests documenting `flatten_nested = 0` target
  behavior.

GREEN:

- Only implement parsing or warning behavior if it is small and directly
  useful.

REFACTOR:

- Document the stage-two API decision needed for unflattened insert.

Done when:

- Future path is visible.
- Stage one cannot accidentally mis-handle unflattened Nested data silently.

## Scenario Matrix

| Scenario | Setting | Stage | Expected Behavior |
| --- | --- | --- | --- |
| `Map(String, Map(String, Nullable(String)))` reflection | n/a | 1 | Parse recursive map tree |
| `Map(Enum8(...), String)` reflection | n/a | 1 | Parse enum key and string value |
| nested `Tuple` reflection | n/a | 1 | Parse tuple tree |
| complex type DDL compile | n/a | 2 | Render valid recursive type SQL |
| `DateTime64(3, 'America/New_York')` reflection | n/a | 1 | Preserve timezone quoting |
| `Nested()` empty | n/a | 3 | Raise `ValueError` |
| one-level `Nested` create table | n/a | 3 | Compile DDL |
| one-level `Nested` insert compile | n/a | 3 | Compile without copy/adapt failure |
| one-level `Nested` batch insert | `flatten_nested=1` | 4 | Round-trip arrays |
| direct dotted Nested insert | `flatten_nested=1` | 4 optional | Round-trip arrays or document unsupported |
| reflection of flattened Nested | `flatten_nested=1` | 4 | Return dotted array columns |
| depth-3 Nested type reflection | `flatten_nested=0` | 5 | Parse or expected-fail with documented target |
| depth-3 Nested insert | `flatten_nested=0` | 5 | Clear unsupported behavior in stage one |
| row-oriented one-level Nested payload | `flatten_nested=1` | 4 | Clear unsupported error |

## Acceptance Criteria

Stage one through four are complete when:

- Parser tests pass for recursive supported non-Nested types.
- Compiler tests pass for recursive supported non-Nested types.
- `types.Nested(...)` compiles through SQLAlchemy lifecycle paths.
- One-level `Nested` batch insert round-trips with `flatten_nested = 1`.
- Stage 4 uses public SQLAlchemy execution behavior, not only private helper
  tests.
- Reflection in default flattened mode returns array subcolumns, not a
  fabricated logical `Nested` column.
- Execution-time arbitrary SQL string rewriting is absent unless this plan is
  amended with a narrower accepted grammar.
- Unflattened nested behavior is either explicitly skipped/xfail or emits a
  clear unsupported signal.

## Non-Goals

- Full SQL parser.
- Rewriting arbitrary compiled `INSERT` SQL in the execution layer.
- Automatic grouping of `parent.child Array(...)` reflected columns into
  `types.Nested` in stage one.
- Arbitrary-depth flattened Nested insert.
- Row-oriented one-level Nested payload conversion unless separately approved.
- Update or alter support for Nested subfields.
- Alembic autogenerate and Nested type-diff parity. This remains outside stages
  1-5 and should be planned separately after reflection and DDL behavior are
  stable.

## Open Decisions

1. Should stage-four direct dotted-key insert be required, or only the nested
   mapping API?
   - Default: require nested mapping API; dotted keys are accepted only if they
     work through public execution behavior with minimal extra code.
2. Should unsupported `flatten_nested = 0` insert raise, warn, or skip through
   to the driver untouched?
   - Default: raise a clear unsupported error for ORM/Core structured inserts;
     leave raw textual SQL untouched.
3. Should reflection eventually offer an opt-in mode to group flattened dotted
   array columns back into `types.Nested`?
   - Default: no grouping in stage one. Consider opt-in grouping only after
     Core reflection and ORM implications are documented.
4. Should docs recommend setting `flatten_nested = 1` explicitly in examples,
   or rely on ClickHouse default while tests set it explicitly?
   - Default: examples can mention it is the ClickHouse default; tests must set
     it explicitly.
5. Should `flatten_nested = 0` support use list-of-dicts or tuple-oriented
   payloads?
   - Default: defer. Align with `clickhouse-driver` only after probe tests
     establish reflected shape and server-version behavior.
