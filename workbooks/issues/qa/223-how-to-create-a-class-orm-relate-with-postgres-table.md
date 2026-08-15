# Issue #223 how to create a class ORM relate with postgres table

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/223
- Category: 问答
- Priority: low
- Created: 2022-12-06T07:28:39Z
- Updated: 2022-12-06T07:28:39Z
- Author: flyly0755
- Labels: none
- Comments: 0

## 判断
ClickHouse ORM 类关联 PostgreSQL 表是跨数据库建模问答，非本 dialect bug。

## 本地 fork 现状
本仓库只提供 ClickHouse dialect。

## 建议动作
回复需用 SQLAlchemy 多 bind/独立 metadata，不做跨库关系自动化。

## Issue 摘要
Usually, create a ORM class as below: ```python from sqlalchemy import Column from clickhouse_sqlalchemy.ext.declarative import declarative_base ChBase = declarative_base() class TbFile(ChBase): __tablename__ = 'tb_file' __table_args__ = {'comment': 'File Info Table V2.0'} created = Column(types.DateTime, server_default=F.now()) filename = Column(types.String, primary_key=True) id = Column(types.UInt32) __table_args_...
