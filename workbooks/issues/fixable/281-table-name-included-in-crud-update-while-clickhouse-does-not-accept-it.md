# Issue #281 Table name included in CRUD update while ClickHouse does not accept it

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/281
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-01-12T11:05:30Z
- Updated: 2024-01-12T11:05:30Z
- Author: vkozmik
- Labels: none
- Comments: 0

## 判断
CRUD UPDATE 带表名前缀导致 ClickHouse 不接受。

## 本地 fork 现状
visit_update 用 include_table 行为需要确认；测试只覆盖简单列名。

## 建议动作
补多表/带 table-qualified column update 编译测试并去除目标表前缀。

## Issue 摘要
I have a query which increments the column by one: query = ( update(Table) .filter(Table.id == '123') .values(counter=Table.counter + 1) ) session.connection().execute(query) This issues ALTER TABLE table UPDATE counter = (table.counter + 1) and database complains about "table.counter" This can be probably fixed by not including table name while calling _get_crud_params, but I do not know if it would have negative si...
