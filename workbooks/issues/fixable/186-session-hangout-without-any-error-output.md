# Issue #186 session hangout without any error output

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/186
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-08-01T07:06:02Z
- Updated: 2022-08-01T08:08:08Z
- Author: flyly0755
- Labels: none
- Comments: 1

## 判断
session hang without error 需要超时/错误传播调查。

## 本地 fork 现状
当前没有足够复现信息，但 timeout/streaming/error handling 可加强。

## 建议动作
请求复现；同时检查 HTTP streaming 和 native timeout 文档。

## Issue 摘要
**Describe the bug** https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/master/clickhouse_sqlalchemy/drivers/http/transport.py#L102 ```python self.timeout = float(timeout) if timeout is not None else None ``` with this line code, is there any issue here when timeout is None, then self.timeout is None? when self.timeout is None, means code below the post method with self.timout this inarg will not timeout forever...
