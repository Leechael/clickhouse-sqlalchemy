# Issue #188 how to set a timeout for seesion insert

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/188
- Category: 问答
- Priority: low
- Created: 2022-08-08T03:01:03Z
- Updated: 2024-10-25T14:38:00Z
- Author: flyly0755
- Labels: none
- Comments: 1

## 判断
session insert timeout 是连接/driver 参数用法问题。

## 本地 fork 现状
RequestsTransport/native/asynch 都有不同 timeout/settings 路径。

## 建议动作
回复具体 driver 的 timeout/connect_args 设置；补 docs。

## Issue 摘要
```python from clickhouse_sqlalchemy import make_session from sqlalchemy import create_engine from sqlalchemy.pool import NullPool engine = create_engine(uri, echo=False, poolclass=NullPool) session = make_session(engine) ``` i want to know, whether clickhouse-sqlalchemy package supports sql cmd execute timeout configuration? and how to config sql insert timeout in create_engine method? now i meet situation in this i...
