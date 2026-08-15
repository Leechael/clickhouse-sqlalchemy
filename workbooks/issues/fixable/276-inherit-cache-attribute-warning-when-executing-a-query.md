# Issue #276 'inherit_cache' attribute warning when executing a query

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/276
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2023-11-22T16:58:41Z
- Updated: 2024-04-02T19:29:25Z
- Author: AviSarmani
- Labels: none
- Comments: 1

## 判断
inherit_cache 警告，本地函数类看起来已有 inherit_cache=True。

## 本地 fork 现状
clickhouse_sqlalchemy/sql/functions.py 中多个函数类设置 inherit_cache=True。

## 建议动作
复现原告警；若消失则标为已修，否则补遗漏类。

## Issue 摘要
**To Reproduce** In database: ``` CREATE TABLE test_01 ( `first_col` String) ENGINE = Log; CREATE TABLE test_02 ( `first_col` String) ENGINE = Log; ``` Code: ``` from clickhouse_sqlalchemy import Table from clickhouse_sqlalchemy import select as chselect test_01 = Table( "test_01", metadata, autoload_with=engine, ) test_02 = Table( "test_02", metadata, autoload_with=engine, ) sel = ( chselect(test_01.c.first_col) .se...
