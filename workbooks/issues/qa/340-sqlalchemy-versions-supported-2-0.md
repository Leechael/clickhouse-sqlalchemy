# Issue #340 SQLAlchemy versions supported (2.0?)

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/340
- Category: 问答
- Priority: medium
- Created: 2024-10-03T17:12:11Z
- Updated: 2024-10-15T10:53:56Z
- Author: MicaelJarniac
- Labels: none
- Comments: 2

## 判断
SQLAlchemy 2.0 支持范围问答。

## 本地 fork 现状
pyproject 明确 SQLAlchemy>=2.0.0,<2.1.0。

## 建议动作
回复本 fork 支持 SQLAlchemy 2.0，不以 1.4 为目标。

## Issue 摘要
On the docs, it says: > Release 0.3.2. > > Supported SQLAlchemy: 1.4. https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/523559e625e59b7f39bfaaff4fb58a52a1e33a34/docs/index.rst?plain=1#L4-L6 On the dependencies, however: > `'sqlalchemy>=2.0.0,<2.1.0',` https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/523559e625e59b7f39bfaaff4fb58a52a1e33a34/setup.py#L99 This confused me. Which versions of SQLAlchemy are a...
