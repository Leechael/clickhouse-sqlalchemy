# Issue #362 SQLAlchemy 1.4 or 2?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/362
- Category: 问答
- Priority: medium
- Created: 2025-02-01T01:51:26Z
- Updated: 2025-09-03T18:50:54Z
- Author: Kevin-Prichard
- Labels: none
- Comments: 1

## 判断
SQLAlchemy 1.4/2.0 支持范围问题；本 fork 已明确转向 SQLAlchemy 2。

## 本地 fork 现状
pyproject 要求 SQLAlchemy>=2.0.0,<2.1.0。

## 建议动作
回复支持范围：本 fork 以 SQLAlchemy 2.0 为基线，不再承诺 1.4。

## Issue 摘要
**Describe the bug** It says "Supported SQLAlchemy: 1.4." on clickhouse-sqlalchemy.readthedocs.io, and "Release 0.3.2." But when I specify those in my requirements.txt, I get- ``` ERROR: Cannot install -r requirements.txt (line 3), clickhouse-sqlalchemy==0.3.2 and sqlalchemy==1.4.54 because these package versions have conflicting dependencies. The conflict is caused by: The user requested sqlalchemy==1.4.54 clickhous...
