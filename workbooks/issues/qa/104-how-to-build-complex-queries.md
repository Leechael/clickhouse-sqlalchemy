# Issue #104 How to build complex queries?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/104
- Category: 问答
- Priority: low
- Created: 2020-09-29T14:23:13Z
- Updated: 2020-09-30T16:33:26Z
- Author: artbeglaryan
- Labels: none
- Comments: 3

## 判断
复杂查询构建问答。

## 本地 fork 现状
历史维护者已确认部分语法是 bug，但 issue 本身偏用法讨论。

## 建议动作
整理复杂查询示例；具体 bug 拆成独立 issue。

## Issue 摘要
Let's say I have 2 distributed tables with the same sharding key, sample expression and distributed_product_mode is 'local'. How I can use clickhouse-sqlalchemy to build complex query like folowing? ``` from sqlalchemy import Column, MetaData from clickhouse_sqlalchemy import Table, types metadata = MetaData() table_A = Table('table_A', metadata, Column('col_1', types.String), Column('col_2', types.DateTime)) table_B...
