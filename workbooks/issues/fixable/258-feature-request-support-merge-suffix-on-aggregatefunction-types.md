# Issue #258 Feature request: support -Merge suffix on AggregateFunction types

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/258
- Category: 我们可以跟进修复
- Priority: low
- Created: 2023-08-23T20:19:47Z
- Updated: 2023-08-23T21:44:17Z
- Author: HacKanCuBa
- Labels: none
- Comments: 1

## 判断
AggregateFunction -Merge 后缀支持缺失。

## 本地 fork 现状
AggregateFunction 当前接受 agg_func 字符串/函数，但需确认反射 parser 对 -Merge。

## 建议动作
补 AggregateFunction(sumMerge, T) 编译/反射测试。

## Issue 摘要
First of all, thanks for all the work done here! To the point, currently there's no way to deal w/ AggregateFunction types, so we need a way to issue, say, `sumMerge` instead of `sum`, `uniqMerge` instead of `uniq`, etc. See [this example](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/aggregatingmergetree#example-of-an-aggregated-materialized-view) of an Aggregated Mat View: ```sql CREATE TABL...
