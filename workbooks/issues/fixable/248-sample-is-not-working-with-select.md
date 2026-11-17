# Issue #248 SAMPLE is not working with select()

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/248
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2023-05-08T18:49:00Z
- Updated: 2023-05-08T18:49:00Z
- Author: Ninefiveblade
- Labels: none
- Comments: 0

## 判断
SAMPLE 在 select() 不工作需要按新版 select API 复现。

## 本地 fork 现状
selectable.py 有 sample()，测试覆盖基础 select().sample。

## 建议动作
复现 issue 形态，可能是 SQLAlchemy 1.4/2.0 generative 状态丢失。

## Issue 摘要
**Describe the bug** SAMPLE method is not working select(<model>).sample(1) -> SELECT <model>.id FROM <model> SAMPLE, but now it looks like SELECT <model>.id FROM <model> **To Reproduce** from sqlalchemy import Column from sqlalchemy.orm import declarative_base from clickhouse_sqlalchemy import select, types Base = declarative_base() FORMAT_REPRESENTATION_NAME = "ID {id}, Date {name}" FORMAT_DOMAIN_TABLE = "{id} - {n...
