# Issue #225 Not clear how to use "https"

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/225
- Category: 问答
- Priority: low
- Created: 2022-12-16T00:45:21Z
- Updated: 2022-12-16T08:46:00Z
- Author: tfrokt
- Labels: none
- Comments: 1

## 判断
HTTPS 连接使用方法不清楚，偏文档。

## 本地 fork 现状
docs/connection.rst 有 verify/cert/header/http_session 等 HTTP 配置。

## 建议动作
补 https URL、verify/cert 示例。

## Issue 摘要
Trying to connect to clickhouse using `https://<url>:8443` It is not clear to me from the docs where I would pass the [driver options](https://clickhouse-sqlalchemy.readthedocs.io/en/latest/connection.html#driver-options), such as `protocol='https'`.
