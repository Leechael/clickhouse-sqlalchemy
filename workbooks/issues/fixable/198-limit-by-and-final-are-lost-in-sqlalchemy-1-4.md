# Issue #198 LIMIT BY & FINAL are lost in SQLAlchemy 1.4

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/198
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-08-31T10:17:35Z
- Updated: 2025-10-13T07:33:47Z
- Author: nolar
- Labels: none
- Comments: 10

## 判断
SQLAlchemy 1.4 下 LIMIT BY/FINAL 丢失；本 fork是 SQLAlchemy 2，但同类 generative 状态需确认。

## 本地 fork 现状
limit_by/final 状态存在自定义 Select/Query 类。

## 建议动作
在 SQLAlchemy 2 复现新版 select 链式调用，必要时修 generative 拷贝。

## Issue 摘要
First of all, thanks for the library! It is really helpful and easy to use! **Describe the bug** When using `.limit_by(...)` with SQLAclhemy 1.4, it is lost in the final SQL query. **To Reproduce** ```python from clickhouse_sqlalchemy import engines, types, get_declarative_base, make_session from sqlalchemy import create_engine, MetaData, Column, String, Table from sqlalchemy import Column, PrimaryKeyConstraint url =...
