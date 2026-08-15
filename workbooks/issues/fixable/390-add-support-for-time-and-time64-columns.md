# Issue #390 Add support for Time and Time64 columns

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/390
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2025-09-24T20:01:39Z
- Updated: 2025-09-24T20:01:39Z
- Author: joe-clickhouse
- Labels: none
- Comments: 0

## 判断
ClickHouse 新增 Time/Time64 类型，当前类型表未支持。

## 本地 fork 现状
types/common.py 和 typecompiler 中没有 Time/Time64。

## 建议动作
新增类型、编译、反射和 HTTP/native/asynch 转换测试。

## Issue 摘要
ClickHouse 25.6 introduced [Time](https://clickhouse.com/docs/sql-reference/data-types/time) and [Time64](https://clickhouse.com/docs/sql-reference/data-types/time64) columns.
