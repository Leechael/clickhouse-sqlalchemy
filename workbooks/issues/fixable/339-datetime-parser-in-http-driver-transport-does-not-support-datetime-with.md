# Issue #339 Datetime parser in HTTP driver transport does not support datetime with nanoseconds

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/339
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-10-01T08:58:05Z
- Updated: 2024-10-01T08:58:05Z
- Author: jordanauge
- Labels: none
- Comments: 0

## 判断
HTTP DateTime parser 不支持纳秒，当前 datetime.strptime(%f) 只能处理最多 6 位。

## 本地 fork 现状
datetime_converter 对小数秒用 %f。

## 建议动作
截断/保留纳秒策略需明确；增加 DateTime64(9) HTTP 解析测试。

## Issue 摘要
**Describe the bug** I have OpenTelemetry data stored in Clickhouse. Timestamps have nanosecond granularity. **To Reproduce** Any SQL query retrieving those timestamps. **Expected behavior** Timestamps should be properly parsed (eventually losing precision), but an exception is returned. The call to strptime fails when timestamps have a nanosecond component with a ValueError (unconverted data remains) : https://githu...
