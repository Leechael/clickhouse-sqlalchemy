# Issue #366 sqlalchemy bindparam support for delete works only for one parameter

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/366
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2025-03-05T16:53:10Z
- Updated: 2025-06-30T10:02:20Z
- Author: sairamkrish
- Labels: none
- Comments: 1

## 判断
DELETE bindparam 多参数只支持一个，可能是编译栈 include_table 或 CRUD 参数问题。

## 本地 fork 现状
visit_delete 自定义 ALTER TABLE DELETE 编译，测试仅覆盖简单常量。

## 建议动作
新增多个 bindparam 的 DELETE 编译/执行测试并修复参数渲染。

## Issue 摘要
Hello there., Version details : ```log clickhouse-sqlalchemy==0.3.2 SQLAlchemy==2.0.38 ``` When we try to use SqlAlchemy delete using clickhouse-sqlalchemy as the dialect driver, we are facing issue while deleting. When we use bindparam and pass values as an array., this fails. It should be fairly easy to reproduce this issue ```py # let's assume users_table is the table on which we like to delete multiple users base...
