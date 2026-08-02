# Issue #341 select(...).final() is not applying the final clause to the query

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/341
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-10-08T02:49:39Z
- Updated: 2025-04-30T10:14:53Z
- Author: udupama
- Labels: none
- Comments: 1

## 判断
select(...).final() 未生效需要按 SQLAlchemy 版本确认。

## 本地 fork 现状
本地 selectable/ORM query 有 final()，测试覆盖简单 FROM FINAL。

## 建议动作
复现 issue 的具体 select 形式；若是 2.0 select API 克隆丢状态，补测试修复。

## Issue 摘要
**Describe the bug** select(...).final() is not applying the final clause to the query when we use in ORM mode **To Reproduce** `class SimpleEntity:` `__tablename__ = 'xxx' a = Column(types.String, nullable=False, primary_key=True) b = Column(types.String, nullable=False, primary_key=True) c = Column(types.String, nullable=False)` `select(SimpleEntity).final().where(...)` **Expected behavior** FINAL clause applied to...
