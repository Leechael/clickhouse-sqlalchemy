# Issue #386 There is issue with commit and rollback these 2 methods in asynch scenario

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/386
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2025-08-30T06:53:51Z
- Updated: 2025-09-01T01:18:28Z
- Author: flyly0755
- Labels: none
- Comments: 0

## 判断
asynch commit/rollback 对 ClickHouse 非事务应 no-op；本地代码已捕获 NotSupportedError。

## 本地 fork 现状
AsyncAdapt_asynch_connection._commit_async/_rollback_async 捕获 dbapi.NotSupportedError 后返回 None。

## 建议动作
跑 asynch commit/rollback 测试；可作为已修复候选。

## Issue 摘要
https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/3dc8df9da598ac51e20e9b7bb110ae97e250fab7/clickhouse_sqlalchemy/drivers/asynch/connector.py#L178C1-L183C1 ```python def rollback(self): self.await_(self._connection.rollback()) def commit(self): self.await_(self._connection.commit()) ``` Because ClickHouse does not support transaction, then will raise error: ``` xxx\asynch\connection.py", line 181, in commit rais...
