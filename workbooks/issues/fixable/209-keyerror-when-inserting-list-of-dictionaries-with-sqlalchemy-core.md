# Issue #209 `KeyError` when inserting list of dictionaries with SQLAlchemy core

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/209
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-11-02T14:28:53Z
- Updated: 2022-11-03T15:46:52Z
- Author: pankotsias
- Labels: none
- Comments: 0

## 判断
SQLAlchemy core list-of-dicts insert KeyError，属于 insert 参数处理 bug。

## 本地 fork 现状
insert 相关代码有 native 单行优化，需复现 list dict 边界。

## 建议动作
补 Core insert 多 dict 不同 key 集测试。

## Issue 摘要
**Describe the bug** Using a (standard) batch insertion with `sqlalchemy`, i.e. a list of dictionaries with each dict corresponding to a new row, results in an error. **To Reproduce** ```python from sqlalchemy import create_engine, Column, MetaData, func from clickhouse_sqlalchemy import ( make_session, get_declarative_base, types, engines ) from datetime import date from sqlalchemy.ext.declarative import declarative...
