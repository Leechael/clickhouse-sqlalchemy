# Issue #269 Reflection fails on complex nested types

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/269
- Category: 我们可以跟进修复
- Priority: high
- Created: 2023-10-27T04:39:36Z
- Updated: 2023-10-27T04:39:36Z
- Author: hsheth2
- Labels: none
- Comments: 0

## 判断
复杂嵌套类型反射失败，和 #328/#135/#101 相关。

## 本地 fork 现状
类型解析支持基础 Array/Nullable/Tuple/Map/Nested，但复杂组合风险高。

## 建议动作
补 parser 级别复杂类型测试，修 parse_arguments/get_inner_spec。

## Issue 摘要
**Describe the bug** For a table DDL like this: ``` CREATE TABLE IF NOT EXISTS bugtable on cluster 'local' ( id Int, metadata Map(String, Map(String, Nullable(String))) ) ENGINE = MergeTree() order by id ``` Reflection using get_columns() fails with `Map.__init__() missing 1 required positional argument: 'value_type'` It looks like the issue is in this code https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/a314...
