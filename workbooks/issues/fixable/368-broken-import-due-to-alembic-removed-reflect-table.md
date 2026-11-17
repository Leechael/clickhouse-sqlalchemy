# Issue #368 Broken import due to Alembic removed _reflect_table

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/368
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2025-03-07T12:51:19Z
- Updated: 2025-09-23T13:42:54Z
- Author: thomas-dufour
- Labels: none
- Comments: 3

## 判断
Alembic 删除/移动 _reflect_table 的兼容问题，本地已有 fallback。

## 本地 fork 现状
comparators.py 对 alembic.util.sqla_compat、compare、compare.util 多路径导入做了兼容。

## 建议动作
跑 tests/alembic，若通过可标为已修。

## Issue 摘要
**Describe the bug** Alembic version 1.15 removed function `_reflect_table` from alembic/util/sqla_compat.py. This prevents the import of `clickhouse_sqlalchemy.alembic.dialect` in my alembic/env.py file as I was taking example on https://github.com/xzkostyan/clickhouse-sqlalchemy-alembic-example/blob/main/simple/migrations/env.py. I plan to open a PR soon. I already did a patch on a local fork of clickhouse-sqlalche...
