# Issue #135 Nested not working

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/135
- Category: 我们可以跟进修复
- Priority: high
- Created: 2021-08-06T10:37:52Z
- Updated: 2023-04-24T14:30:45Z
- Author: frad00r4
- Labels: bug
- Comments: 1

## 判断
Nested 类型不工作，和 #101/#269/#328 同类。

## 本地 fork 现状
基础 Nested DDL 存在，但插入/反射复杂路径仍有已知风险。

## 建议动作
合并到 Nested 主题修复计划。

## Issue 摘要
Hello **Describe the bug** When I try to use Nested field in model way, I get exception `ValueError: columns must be specified for nested type` **To Reproduce** ```sql CREATE TABLE IF NOT EXISTS test_table ( id UInt64, nstd Nested(test String) ) ENGINE = MergeTree() ORDER BY id; INSERT INTO test_table (id, nstd.test) VALUES (111, ['name', 'table']), (222,['name1', 'table2']); ``` ```python engine = create_engine('cli...
