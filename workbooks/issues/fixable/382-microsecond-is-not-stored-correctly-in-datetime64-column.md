# Issue #382 Microsecond is not stored correctly in DateTime64 column

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/382
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2025-07-04T03:27:45Z
- Updated: 2025-07-04T03:27:45Z
- Author: freedom0116
- Labels: none
- Comments: 0

## 判断
DateTime64 微秒/小数精度存储问题，需要确认文本绑定和 asynch fork 处理。

## 本地 fork 现状
本地已有 tests/drivers/asynch/test_datetime64_precision.py，HTTP datetime_converter 只用 %f 到微秒。

## 建议动作
复现 issue 的 driver 路径；若涉及纳秒，需扩展解析/绑定策略。

## Issue 摘要
**Describe the bug** Try to insert DateTime64 data but somehow the stored data missed microsecond info. **To Reproduce** Any insert query for DateTime64 column. **Expected behavior** Should stored with microsecond information in DateTime64 column. Here is the source code for doing the datetime handling: https://github.com/xzkostyan/clickhouse-sqlalchemy/blob/master/clickhouse_sqlalchemy/drivers/http/transport.py#L29 ...
