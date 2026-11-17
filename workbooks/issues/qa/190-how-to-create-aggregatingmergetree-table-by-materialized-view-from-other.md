# Issue #190 How to create AggregatingMergeTree table by materialized view from other tables?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/190
- Category: 问答
- Priority: low
- Created: 2022-08-09T04:11:03Z
- Updated: 2022-08-09T13:07:57Z
- Author: hoangnguyennhu
- Labels: none
- Comments: 1

## 判断
通过 MV 创建 AggregatingMergeTree 表是用法问题。

## 本地 fork 现状
docs/features.rst 有 MaterializedView/engine 示例。

## 建议动作
补 AggregatingMergeTree + MV 示例。

## Issue 摘要
Now I want to create some AggregatingMergeTree tables but it is not mentioned on the documentation and I did not find any example about it. Here is clickhouse queries about my table: CREATE TABLE IF NOT EXISTS extrema_value ( MaxValue SimpleAggregateFunction(max, Float64), MinValue SimpleAggregateFunction(min, Float64), ID UInt64 ) ENGINE = AggregatingMergeTree() ORDER BY (ID) CREATE MATERIALIZED VIEW extrema_value_m...
