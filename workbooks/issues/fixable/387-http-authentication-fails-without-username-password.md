# Issue #387 HTTP authentication fails without username/password

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/387
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2025-09-07T19:31:53Z
- Updated: 2025-09-07T19:31:53Z
- Author: medgyes
- Labels: none
- Comments: 0

## 判断
HTTP 无用户名密码时仍发送 Basic auth，可能导致无认证服务失败。

## 本地 fork 现状
RequestsTransport 总是设置 self.auth=(username, password) 并传给 requests.post。

## 建议动作
username/password 为空时传 auth=None，并补 HTTP transport 测试。

## Issue 摘要
**Describe the bug** Username,password is not mandatory for clickhouse. If they are not set then the current implementation sends a `Basic Og==` as the Authorization header and it fails. **To Reproduce** The code is not much, but one need a clickhouse instance without any user/password auth. I used the `clickhouse/clickhouse-server:23.3.13.6-alpine` docker image without the `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD`...
