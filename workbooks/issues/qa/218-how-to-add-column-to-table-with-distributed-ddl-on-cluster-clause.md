# Issue #218 How to add column to table with distributed ddl ON CLUSTER clause

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/218
- Category: 问答
- Priority: medium
- Created: 2022-11-18T13:12:14Z
- Updated: 2022-11-21T11:58:12Z
- Author: AntonFriberg
- Labels: none
- Comments: 3

## 判断
ALTER ADD COLUMN ON CLUSTER 用法问题，也可能需要 Alembic op 文档。

## 本地 fork 现状
DDL Table create/drop 支持 cluster；Alembic operations 部分支持 on_cluster。

## 建议动作
回复可用 clickhouse_cluster/on_cluster 的路径；若 add_column 缺失则另开 fix。

## Issue 摘要
**Describe the bug** Hi! I know that you can specify `{'clickhouse_cluster': '{cluster}'}` in the `__table_args__` of a model in order to add the `ON CLUSTER '{cluster}'` clause to the CREATE TABLE statement. However, I have not found any way of adding the same clause to other types of operations such as adding a column to table, removing column from table, updating values in database, etc. Is this a know limitation ...
