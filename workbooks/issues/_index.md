# Upstream open issues triage

- Upstream repo: https://github.com/xzkostyan/clickhouse-sqlalchemy
- Snapshot date: 2026-05-16
- Open issues checked: 96
- Recorded issue files: 93
- Skipped as non-actionable: 3

## Buckets

- 我们可以跟进修复: 70
- 问答: 23

## Notes

- asynch is currently pinned to our fork: `asynch @ git+https://github.com/Leechael/asynch.git@1a74a71`.
- Several upstream asynch compatibility reports may already be resolved locally; those are marked `done-check` and still need targeted test confirmation before closing the loop.
- Pure upstream maintenance/release/version bump requests are listed in `_skipped.md` instead of getting individual issue files.

## Maintenance

- Use this file as the tracking entry point for upstream issue follow-up.
- Keep one detail file per recorded issue under `fixable/` or `qa/`.
- When an issue is investigated, update both its detail file and the status/priority shown here.
- Treat `done-check` as "probably fixed in our fork, but needs targeted verification".
- Add newly discovered upstream issues here only after creating the matching detail file.

## Recorded issues

- #402 [Consider making driver dependencies extras](fixable/402-consider-making-driver-dependencies-extras.md) - 我们可以跟进修复 - medium
- #400 [Asynch driver incompatible with asynch 0.3.1+ and SQLAlchemy 2.0.44+](fixable/400-asynch-driver-incompatible-with-asynch-0-3-1-plus-and-sqlalchemy-2-0-44.md) - 我们可以跟进修复 - high
- #399 [`alembic_version` table can no longer be created with `order by tuple` since 25.12](fixable/399-alembic-version-table-can-no-longer-be-created-with-order-by-tuple-since.md) - 我们可以跟进修复 - high
- #398 [No way to omit parameters for Replicated* table engines constructor](fixable/398-no-way-to-omit-parameters-for-replicated-table-engines-constructor.md) - 我们可以跟进修复 - medium
- #396 [HTTP driver don't support the boolean type](fixable/396-http-driver-don-t-support-the-boolean-type.md) - 我们可以跟进修复 - medium
- #393 [Incompatible with Sqlalchemy v2.0.44 using asynch](fixable/393-incompatible-with-sqlalchemy-v2-0-44-using-asynch.md) - 我们可以跟进修复 - done-check
- #390 [Add support for Time and Time64 columns](fixable/390-add-support-for-time-and-time64-columns.md) - 我们可以跟进修复 - medium
- #387 [HTTP authentication fails without username/password](fixable/387-http-authentication-fails-without-username-password.md) - 我们可以跟进修复 - medium
- #386 [There is issue with commit and rollback these 2 methods in asynch scenario](fixable/386-there-is-issue-with-commit-and-rollback-these-2-methods-in-asynch-scenar.md) - 我们可以跟进修复 - done-check
- #382 [Microsecond is not stored correctly in DateTime64 column](fixable/382-microsecond-is-not-stored-correctly-in-datetime64-column.md) - 我们可以跟进修复 - medium
- #378 [Multi-bind session fails on commit() due to NotSupportedError from asynch](fixable/378-multi-bind-session-fails-on-commit-due-to-notsupportederror-from-asynch.md) - 我们可以跟进修复 - done-check
- #373 [Feature request: map ClickHouse String columns to pandas StringDtype instead of object](qa/373-feature-request-map-clickhouse-string-columns-to-pandas-stringdtype-inst.md) - 问答 - low
- #371 [Conda installation requires SQLAlchemy 1.4](qa/371-conda-installation-requires-sqlalchemy-1-4.md) - 问答 - low
- #368 [Broken import due to Alembic removed _reflect_table](fixable/368-broken-import-due-to-alembic-removed-reflect-table.md) - 我们可以跟进修复 - done-check
- #366 [sqlalchemy bindparam support for delete works only for one parameter](fixable/366-sqlalchemy-bindparam-support-for-delete-works-only-for-one-parameter.md) - 我们可以跟进修复 - medium
- #365 [Is there any plan to support clickhouse new feature generateSerialID?](fixable/365-is-there-any-plan-to-support-clickhouse-new-feature-generateserialid.md) - 我们可以跟进修复 - low
- #362 [SQLAlchemy 1.4 or 2?](qa/362-sqlalchemy-1-4-or-2.md) - 问答 - medium
- #359 [Add support for BFloat16](fixable/359-add-support-for-bfloat16.md) - 我们可以跟进修复 - low
- #354 [Switch from requests to httpx or niquests](fixable/354-switch-from-requests-to-httpx-or-niquests.md) - 我们可以跟进修复 - medium
- #352 [Alembic with `asynch` driver fails on `commit()`](fixable/352-alembic-with-asynch-driver-fails-on-commit.md) - 我们可以跟进修复 - done-check
- #351 [Support for asynch 0.2.5?](fixable/351-support-for-asynch-0-2-5.md) - 我们可以跟进修复 - done-check
- #350 [v0.2.x and SQLAlchemy 1.4.x - TypeError: expected bytes, str found](fixable/350-v0-2-x-and-sqlalchemy-1-4-x-typeerror-expected-bytes-str-found.md) - 我们可以跟进修复 - medium
- #349 [Feature Request: Support for MyPy](fixable/349-feature-request-support-for-mypy.md) - 我们可以跟进修复 - low
- #345 [Add the "pyproject.toml" file backended with building/packaging/dependency manager.](fixable/345-add-the-pyproject-toml-file-backended-with-building-packaging-dependency.md) - 我们可以跟进修复 - done-check
- #341 [select(...).final() is not applying the final clause to the query](fixable/341-select-final-is-not-applying-the-final-clause-to-the-query.md) - 我们可以跟进修复 - medium
- #340 [SQLAlchemy versions supported (2.0?)](qa/340-sqlalchemy-versions-supported-2-0.md) - 问答 - medium
- #339 [Datetime parser in HTTP driver transport does not support datetime with nanoseconds](fixable/339-datetime-parser-in-http-driver-transport-does-not-support-datetime-with.md) - 我们可以跟进修复 - medium
- #335 [Division operator results in an invalid cast](fixable/335-division-operator-results-in-an-invalid-cast.md) - 我们可以跟进修复 - medium
- #334 [Defining polygon type in table](fixable/334-defining-polygon-type-in-table.md) - 我们可以跟进修复 - low
- #333 [generate of alembic, no engine shows up](fixable/333-generate-of-alembic-no-engine-shows-up.md) - 我们可以跟进修复 - medium
- #330 [Table metadata fails to reflect if is_deleted column is set along with version in ReplacingMergeTree engine](fixable/330-table-metadata-fails-to-reflect-if-is-deleted-column-is-set-along-with-v.md) - 我们可以跟进修复 - medium
- #328 [Nested maps, tuples, enums don't work](fixable/328-nested-maps-tuples-enums-don-t-work.md) - 我们可以跟进修复 - high
- #324 [Feature Request: Support clickhouse-connect's NEW AsyncClient wrapper](fixable/324-feature-request-support-clickhouse-connect-s-new-asyncclient-wrapper.md) - 我们可以跟进修复 - medium
- #319 [Sqlalchemy can't catch asynch's error](fixable/319-sqlalchemy-can-t-catch-asynch-s-error.md) - 我们可以跟进修复 - medium
- #316 [Cannot seem to run ALTER command on replicas of the same shard](fixable/316-cannot-seem-to-run-alter-command-on-replicas-of-the-same-shard.md) - 我们可以跟进修复 - medium
- #313 [using http mode, connecting database failed when account password ends with @ ](fixable/313-using-http-mode-connecting-database-failed-when-account-password-ends-wi.md) - 我们可以跟进修复 - medium
- #310 [Table reflection for DateTime64 timezone will be extra quoted](fixable/310-table-reflection-for-datetime64-timezone-will-be-extra-quoted.md) - 我们可以跟进修复 - medium
- #309 [Support VariantType](fixable/309-support-varianttype.md) - 我们可以跟进修复 - low
- #308 [With chdb this clickhouse downsized memory database, can clickhouse-sqlalchemy support it or not?](qa/308-with-chdb-this-clickhouse-downsized-memory-database-can-clickhouse-sqlal.md) - 问答 - low
- #306 [`create_all` for all the `MaterializedView`](fixable/306-create-all-for-all-the-materializedview.md) - 我们可以跟进修复 - medium
- #305 [Support/example for creating views](qa/305-support-example-for-creating-views.md) - 问答 - low
- #298 [Create a cluster table orm class with engines.Distributed which has a logs attribute, how to use variable to indicate it?](qa/298-create-a-cluster-table-orm-class-with-engines-distributed-which-has-a-lo.md) - 问答 - low
- #294 [Does `clickhouse-sqlalchemy` 3.0.0 support `sqlalchemy` of the version 1.4.*?](qa/294-does-clickhouse-sqlalchemy-3-0-0-support-sqlalchemy-of-the-version-1-4.md) - 问答 - medium
- #291 [Error connecting with the database when password contains a special character (+%...) with native engine.](fixable/291-error-connecting-with-the-database-when-password-contains-a-special-char.md) - 我们可以跟进修复 - medium
- #290 [Collate is not generating a correct query](fixable/290-collate-is-not-generating-a-correct-query.md) - 我们可以跟进修复 - medium
- #282 [Bulk update fails on ClickHouse](qa/282-bulk-update-fails-on-clickhouse.md) - 问答 - low
- #281 [Table name included in CRUD update while ClickHouse does not accept it](fixable/281-table-name-included-in-crud-update-while-clickhouse-does-not-accept-it.md) - 我们可以跟进修复 - medium
- #279 [Usage with CHDB?](qa/279-usage-with-chdb.md) - 问答 - low
- #276 ['inherit_cache' attribute warning when executing a query](fixable/276-inherit-cache-attribute-warning-when-executing-a-query.md) - 我们可以跟进修复 - done-check
- #272 [Table reflection fails for bare DateTime](fixable/272-table-reflection-fails-for-bare-datetime.md) - 我们可以跟进修复 - done-check
- #270 [Insert int data which is out of datatype limit can be inserted successfully, without data check](qa/270-insert-int-data-which-is-out-of-datatype-limit-can-be-inserted-successfu.md) - 问答 - medium
- #269 [Reflection fails on complex nested types](fixable/269-reflection-fails-on-complex-nested-types.md) - 我们可以跟进修复 - high
- #262 [_reflect_table() error on migration autogeneration](fixable/262-reflect-table-error-on-migration-autogeneration.md) - 我们可以跟进修复 - done-check
- #258 [Feature request: support -Merge suffix on AggregateFunction types](fixable/258-feature-request-support-merge-suffix-on-aggregatefunction-types.md) - 我们可以跟进修复 - low
- #252 [Add missing geo data types.](fixable/252-add-missing-geo-data-types.md) - 我们可以跟进修复 - medium
- #251 [Is clickhouse-sqlalchemy support integrating with  flask-sqlalchemy?](qa/251-is-clickhouse-sqlalchemy-support-integrating-with-flask-sqlalchemy.md) - 问答 - low
- #248 [SAMPLE is not working with select()](fixable/248-sample-is-not-working-with-select.md) - 我们可以跟进修复 - medium
- #244 [SETTINGS clause](fixable/244-settings-clause.md) - 我们可以跟进修复 - medium
- #243 [ch_settings should be stated in the documentation](qa/243-ch-settings-should-be-stated-in-the-documentation.md) - 问答 - low
- #235 [Alembic branching is not supported](fixable/235-alembic-branching-is-not-supported.md) - 我们可以跟进修复 - medium
- #231 [FINAL statement not working](fixable/231-final-statement-not-working.md) - 我们可以跟进修复 - medium
- #225 [Not clear how to use "https"](qa/225-not-clear-how-to-use-https.md) - 问答 - low
- #223 [how to create a class ORM relate with postgres table](qa/223-how-to-create-a-class-orm-relate-with-postgres-table.md) - 问答 - low
- #218 [How to add column to table with distributed ddl ON CLUSTER clause](qa/218-how-to-add-column-to-table-with-distributed-ddl-on-cluster-clause.md) - 问答 - medium
- #211 [with uri clickhouse://  to insert data with  integer field, there isn't range check, can insert successfully with out of range integer value](qa/211-with-uri-clickhouse-to-insert-data-with-integer-field-there-isn-t-range.md) - 问答 - medium
- #209 [`KeyError` when inserting list of dictionaries with SQLAlchemy core](fixable/209-keyerror-when-inserting-list-of-dictionaries-with-sqlalchemy-core.md) - 我们可以跟进修复 - medium
- #204 [Support for DROP PARTITION statements](fixable/204-support-for-drop-partition-statements.md) - 我们可以跟进修复 - medium
- #203 [sqlalchemy>=1.4 inspection error on future.Engine use](fixable/203-sqlalchemy-1-4-inspection-error-on-future-engine-use.md) - 我们可以跟进修复 - done-check
- #201 [Generated CREATE TABLE statements ignoring nullable value and missing "NOT NULL" modifier](fixable/201-generated-create-table-statements-ignoring-nullable-value-and-missing-no.md) - 我们可以跟进修复 - medium
- #200 [Clickhouse Integration Table Engines](fixable/200-clickhouse-integration-table-engines.md) - 我们可以跟进修复 - medium
- #198 [LIMIT BY & FINAL are lost in SQLAlchemy 1.4](fixable/198-limit-by-and-final-are-lost-in-sqlalchemy-1-4.md) - 我们可以跟进修复 - medium
- #195 [Clickhouse alembic array nullable field](fixable/195-clickhouse-alembic-array-nullable-field.md) - 我们可以跟进修复 - medium
- #190 [How to create AggregatingMergeTree table by materialized view from other tables?](qa/190-how-to-create-aggregatingmergetree-table-by-materialized-view-from-other.md) - 问答 - low
- #189 [Nullable columns don't seem to work](fixable/189-nullable-columns-don-t-seem-to-work.md) - 我们可以跟进修复 - medium
- #188 [how to set a timeout for seesion insert](qa/188-how-to-set-a-timeout-for-seesion-insert.md) - 问答 - low
- #186 [session hangout without any error output](fixable/186-session-hangout-without-any-error-output.md) - 我们可以跟进修复 - medium
- #157 [Nullable DateTime64(x) support](fixable/157-nullable-datetime64-x-support.md) - 我们可以跟进修复 - done-check
- #150 [Array support](fixable/150-array-support.md) - 我们可以跟进修复 - done-check
- #146 [Support CREATE TABLE IF NOT EXISTS](fixable/146-support-create-table-if-not-exists.md) - 我们可以跟进修复 - medium
- #139 [When I use the aggregation function in superset, there is no return result](qa/139-when-i-use-the-aggregation-function-in-superset-there-is-no-return-resul.md) - 问答 - low
- #135 [Nested not working](fixable/135-nested-not-working.md) - 我们可以跟进修复 - high
- #132 ['nonetype' object has no attribute 'startswith' in drivers/http/transport.py](fixable/132-nonetype-object-has-no-attribute-startswith-in-drivers-http-transport-py.md) - 我们可以跟进修复 - medium
- #122 [Problem with http protocol in clickhouse-sqlalchemy 0.1.5](fixable/122-problem-with-http-protocol-in-clickhouse-sqlalchemy-0-1-5.md) - 我们可以跟进修复 - medium
- #115 [Support for timezone=True for types.DateTime](fixable/115-support-for-timezone-true-for-types-datetime.md) - 我们可以跟进修复 - done-check
- #113 ["global in" support?](fixable/113-global-in-support.md) - 我们可以跟进修复 - low
- #104 [How to build complex queries?](qa/104-how-to-build-complex-queries.md) - 问答 - low
- #101 [Batch insert with nested columns does not work as expected](fixable/101-batch-insert-with-nested-columns-does-not-work-as-expected.md) - 我们可以跟进修复 - high
- #98 [prewhere support?](fixable/98-prewhere-support.md) - 我们可以跟进修复 - medium
- #95 [Multiple FINAL clause support](fixable/95-multiple-final-clause-support.md) - 我们可以跟进修复 - medium
- #61 [connection pool suppt?](qa/61-connection-pool-suppt.md) - 问答 - low
- #54 [can't use raw sql with http driver](fixable/54-can-t-use-raw-sql-with-http-driver.md) - 我们可以跟进修复 - done-check
- #15 [Nullable types not detected correctly](fixable/15-nullable-types-not-detected-correctly.md) - 我们可以跟进修复 - done-check
- #11 [flask integration](qa/11-flask-integration.md) - 问答 - low
