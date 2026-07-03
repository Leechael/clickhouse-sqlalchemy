# Issue #351 Support for asynch 0.2.5?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/351
- Category: 我们可以跟进修复
- Priority: done-check
- Created: 2024-11-08T19:29:16Z
- Updated: 2025-05-06T14:40:43Z
- Author: nils-borrmann-tacto
- Labels: none
- Comments: 2

## 判断
asynch 0.2.5 支持问题可能已因 Leechael/asynch fork 不再存在。

## 本地 fork 现状
pyproject 不再用 PyPI asynch 0.2.5，而是 git fork 固定 commit。

## 建议动作
记录当前 fork 兼容基线；确认无须追上游 asynch 0.2.5。

## Issue 摘要
clickhouse-sqlalchemy currently requires `asynch <= 0.2.4`. Version 0.2.5 of asynch was released 3 weeks ago. Is this deliberately not supported because of incompatibilities or have the dependencies just not been updated since?
