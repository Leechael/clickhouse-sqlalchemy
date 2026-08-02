# Issue #262 _reflect_table() error on migration autogeneration

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/262
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2023-09-18T10:18:33Z
- Updated: 2023-09-18T10:42:51Z
- Author: ObsidianDestroyer
- Labels: none
- Comments: 1

## 判断
Alembic autogeneration _reflect_table 错误，和 #368 同类。

## 本地 fork 现状
comparators.py 已有 Alembic 版本兼容 wrapper。

## 建议动作
跑 tests/alembic 确认。

## Issue 摘要
**Describe the bug** So, I have created a model for my table in Clickhouse: ```python from __future__ import annotations from sqlalchemy.schema import Column from clickhouse_sqlalchemy import types, engines from collector.common.database.models import BaseModel class TrackingPositionChangesOrdo(BaseModel): __tablename__ = 'TrackingPositionChangesOrdo' id = Column(types.UInt64, primary_key=True) srid = Column(types.St...
