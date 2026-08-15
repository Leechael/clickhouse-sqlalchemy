# Issue #122 Problem with http protocol in clickhouse-sqlalchemy 0.1.5

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/122
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2021-03-03T04:45:39Z
- Updated: 2022-06-01T09:51:00Z
- Author: hodgesrm
- Labels: none
- Comments: 3

## 判断
HTTP protocol 0.1.5 问题较老，但可能仍覆盖 HTTP 格式/解析稳定性。

## 本地 fork 现状
HTTP transport 现在强制 default_format=TabSeparatedWithNamesAndTypes。

## 建议动作
复查原报错是否已由 default_format 修复；补 raw SQL HTTP 回归。

## Issue 摘要
**Describe the bug** I'm using clickhouse-sqlalchemy 0.2.0 from pypi.org and have been unable to get http protocol to work properly. If I provide a URL like http://demo:demo@localhost:8123/default the engine.execute() method does not return data. It works fine for native protocol, e.g, a URL like 'clickhouse+native://demo:demo@localhost/default'. **To Reproduce** ``` from sqlalchemy import create_engine urls = ['clic...
