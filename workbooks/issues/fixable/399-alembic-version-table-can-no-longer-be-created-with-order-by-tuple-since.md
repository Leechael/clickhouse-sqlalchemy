# Issue #399 `alembic_version` table can no longer be created with `order by tuple` since 25.12

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/399
- Category: 我们可以跟进修复
- Priority: high
- Created: 2026-01-26T15:26:27Z
- Updated: 2026-01-26T15:33:05Z
- Author: xoelop
- Labels: none
- Comments: 0

## 判断
ClickHouse 25.12 禁止 ReplacingMergeTree ORDER BY tuple()，Alembic version table 仍可能踩中。

## 本地 fork 现状
patch_alembic_version 和 version_table_impl 仍用 order_by=func.tuple()。

## 建议动作
把 alembic_version 的 ORDER BY 改为非空列，补 Alembic DDL 编译/迁移测试。

## Issue 摘要
****Describe** the bug** Before 25.12 it was allowed to create ReplacingMergeTree tables with an empty order by clause. Since 25.12, it's no longer allowed ([link](https://clickhouse.com/docs/whats-new/changelog/2025#2512)) > It is now forbidden to create special MergeTree tables (such as ReplacingMergeTree, CollapsingMergeTree, etc.) with an empty ORDER BY key, since merge behavior in these tables is undefined. If y...
