# Issue #290 Collate is not generating a correct query

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/290
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-01-24T13:41:39Z
- Updated: 2024-01-24T13:41:49Z
- Author: alessandrolulli
- Labels: none
- Comments: 0

## 判断
Collate 编译 SQL 不正确，属于 SQL compiler 缺口。

## 本地 fork 现状
未见 collate 专门处理。

## 建议动作
补 collate 表达式编译测试并实现 ClickHouse 语法。

## Issue 摘要
**Describe the bug** The collate sqlalchemy function is not correctly handled in the Clickhouse dialect **To Reproduce** from sqlalchemy.sql.operators import collate `query.collate(asc("display_name"), "en"))` it generates the following query: `SELECT ... FROM test WHERE ... ORDER BY display_name ASC COLLATE en LIMIT 0, 300` **Expected behavior** The correct query should be: `SELECT ... FROM test WHERE ... ORDER BY d...
