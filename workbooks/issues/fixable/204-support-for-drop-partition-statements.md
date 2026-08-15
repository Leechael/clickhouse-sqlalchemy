# Issue #204 Support for DROP PARTITION statements

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/204
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-10-11T15:09:19Z
- Updated: 2022-10-11T15:09:19Z
- Author: georgipeev
- Labels: none
- Comments: 0

## 判断
DROP PARTITION statement 支持缺失。

## 本地 fork 现状
未见 drop partition 高层 API。

## 建议动作
新增 DDL/helper 或 Alembic op，覆盖 DETACH/DROP PARTITION 编译。

## Issue 摘要
**Describe the bug** Clickhouse is not designed to support deleting rows, although it supports it via expensive `ALTER TABLE ... DELETE WHERE` statements. A much more efficient way of deleting rows is dropping whole partitions, which is why reasonable table schema designers take care to partition their tables with that in mind. However, `ALTER TABLE ... DROP PARTITION` statements are not currently supported by the li...
