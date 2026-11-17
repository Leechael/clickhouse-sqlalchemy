# Issue #313 using http mode, connecting database failed when account password ends with @

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/313
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-05-23T09:20:16Z
- Updated: 2024-05-25T01:12:40Z
- Author: flyly0755
- Labels: none
- Comments: 2

## 判断
HTTP 密码以 @ 结尾连接失败，可能是 URL parsing/quoting 问题。

## 本地 fork 现状
HTTP base 从 URL query/credentials 解析后传给 RequestsTransport。

## 建议动作
补特殊字符密码 URL 测试，确认需 quote_plus 文档还是解析修复。

## Issue 摘要
**Describe the bug** ```python from sqlalchemy import create_engine from sqlalchemy.orm import sessionmaker from sqlalchemy.pool import NullPool chuser = "default" chpwd = "chpwd123@" # end with @ chhost = "chhost" chport = "8123" dbname = 'db1' uri = "{}://{}:{}@{}:{}/{}".format('clickhouse', chuser, chpwd, chhost, chport, dbname) ch_engine = create_engine(uri, echo=False, poolclass=NullPool) ch_session = sessionmak...
