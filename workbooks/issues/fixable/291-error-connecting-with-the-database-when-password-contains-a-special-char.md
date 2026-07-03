# Issue #291 Error connecting with the database when password contains a special character (+%...) with native engine.

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/291
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-02-06T16:29:55Z
- Updated: 2024-03-19T10:09:35Z
- Author: marcvivancos
- Labels: none
- Comments: 1

## 判断
native engine 密码含特殊字符连接失败，可能是 URL decode/driver 参数传递。

## 本地 fork 现状
需要复现 native URL parser 处理 +/% 等字符。

## 建议动作
补 URL credential 特殊字符测试，文档要求 percent-encoding 或修解析。

## Issue 摘要
**Describe the bug** The bug is when there is a special character in the password, the problem seems to be in the file `drives/native/base.py` where the password and the username get `quote` two times. First in the function `create_connect_args` and then in the `render_as_string` method from sqlalchemy url: ```python def create_connect_args(self, url): url = url.set(drivername='clickhouse') if url.username: url = url...
