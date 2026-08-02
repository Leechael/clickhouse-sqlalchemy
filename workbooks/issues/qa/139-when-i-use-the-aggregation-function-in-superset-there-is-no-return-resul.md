# Issue #139 When I use the aggregation function in superset, there is no return result

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/139
- Category: 问答
- Priority: low
- Created: 2021-08-25T10:20:32Z
- Updated: 2022-07-05T18:38:27Z
- Author: zhenxxxx
- Labels: none
- Comments: 1

## 判断
Superset 聚合无结果信息不足，可能是用法/兼容问题。

## 本地 fork 现状
无 Superset 集成测试。

## 建议动作
请求最小 SQL/版本；可补 Superset 文档建议。

## Issue 摘要
**Describe the bug** When I use the aggregation function in superset, there is no return result, and I see a StopIteration exception thrown when I debug ![image](https://user-images.githubusercontent.com/18146612/130773335-eba57a86-a6b9-400f-8bfa-c0c82293e848.png) The lines only contains one elements that the aggregation function result. So the types is NULL, **Versions** - Python 3.7
