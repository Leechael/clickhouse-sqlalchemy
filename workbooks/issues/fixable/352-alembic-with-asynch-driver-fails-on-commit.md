# Issue #352 Alembic with `asynch` driver fails on `commit()`

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/352
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2024-11-20T18:41:22Z
- Updated: 2024-11-20T18:41:22Z
- Author: kusaku
- Labels: none
- Comments: 0

## 判断
Alembic + asynch commit() 失败，和 #386/#378 同类；本地已 no-op。

## 本地 fork 现状
AsyncAdapt_asynch_connection.commit 捕获 NotSupportedError。

## 建议动作
跑 Alembic async 场景或补最小回归。

## Issue 摘要
**Describe the bug** When using asynch driver, alembic migrations fail on commit: ``` alembic upgrade head INFO [sqlalchemy.engine.Engine] select version() INFO [sqlalchemy.engine.Engine] [generated in 0.00012s] {} INFO [sqlalchemy.engine.Engine] select currentDatabase() INFO [sqlalchemy.engine.Engine] [generated in 0.00008s] {} INFO [alembic.runtime.migration] Context impl ClickHouseDialectImpl. INFO [alembic.runtim...
