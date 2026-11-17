# Issue #101 Batch insert with nested columns does not work as expected

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/101
- Category: 我们可以跟进修复
- Priority: high
- Created: 2020-08-17T11:58:08Z
- Updated: 2022-07-05T18:54:29Z
- Author: erosennin
- Labels: bug
- Comments: 2

## 判断
Nested columns 批量插入忽略 members.age，是真实插入编译/参数问题。

## 本地 fork 现状
Nested DDL 有支持，但列名包含 dot 的 insert path 需修。

## 建议动作
补 Nested insert round-trip 测试，修列展开/参数映射。

## Issue 摘要
**Describe the bug** There seems to be no way to specify the values of nested columns when inserting data. **To Reproduce** ```python import sqlalchemy as sa from clickhouse_sqlalchemy import engines, types, select engine = sa.create_engine("clickhouse+native://localhost/default", echo=True) metadata = sa.MetaData() family = sa.Table( "family", metadata, sa.Column("id", types.UInt32, primary_key=True), sa.Column("mem...
