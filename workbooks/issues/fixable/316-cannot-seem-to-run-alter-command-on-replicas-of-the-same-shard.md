# Issue #316 Cannot seem to run ALTER command on replicas of the same shard

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/316
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-06-28T00:42:55Z
- Updated: 2024-07-01T14:20:47Z
- Author: sudhanvaghebbale
- Labels: none
- Comments: 2

## 判断
同分片副本 ALTER ON CLUSTER 问题，可能需要 DDL/on_cluster 支持增强。

## 本地 fork 现状
Alembic operations 已支持部分 on_cluster；普通 ALTER 能力需确认。

## 建议动作
复现 ALTER 路径，补 on_cluster 参数传递。

## Issue 摘要
Hi all, I wanted to reach out regarding an issue I have been facing while running Clickhouse schema migrations using alembic. This issue may not be related to alembic altogether but wanted to know if someone else has experienced this. Here's what I have been trying to do - ### Clickhouse Setup I have a cluster setup containing two Clickhouse nodes which are part of the same shard i.e. two replicas on one shard. I am ...
