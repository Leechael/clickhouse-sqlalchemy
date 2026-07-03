# Issue #324 Feature Request: Support clickhouse-connect's NEW AsyncClient wrapper

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/324
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-07-10T17:30:33Z
- Updated: 2025-03-29T06:02:16Z
- Author: kdcokenny
- Labels: none
- Comments: 9

## 判断
支持 clickhouse-connect AsyncClient 是新 driver/adapter 工作。

## 本地 fork 现状
当前 driver entry points 只有 http/native/asynch。

## 建议动作
评估是否新增 clickhouse-connect driver；范围较大，先做设计。

## Issue 摘要
clickhouse-connect recently released an async wrapper for using the native library asynchronously. I experience many issues with asynch which clickhouse-connect doesn't have. If we could add this wrapper as a dialect that would be great! https://github.com/ClickHouse/clickhouse-connect/releases/tag/v0.7.16
