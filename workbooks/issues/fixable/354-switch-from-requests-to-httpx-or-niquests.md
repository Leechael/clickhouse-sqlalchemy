# Issue #354 Switch from requests to httpx or niquests

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/354
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-12-10T09:44:49Z
- Updated: 2025-09-03T18:40:02Z
- Author: mohaidoss
- Labels: none
- Comments: 1

## 判断
HTTP driver 从 requests 切换到 httpx/niquests 是可跟进的依赖/transport 改造。

## 本地 fork 现状
当前 HTTP transport 直接 import requests 并用 requests.Session。

## 建议动作
评估兼容层，优先支持可注入 session，避免一次性破坏 API。

## Issue 摘要
**Describe the bug** Support for advanced HTTP features. Modern library that is maintained. **niquests**: is a drop in replacement to requests with support for async, http2... **httpx**: as modern as niquests and more stable, but not compatible with requests **Versions** - requests - Python version > 3.8
