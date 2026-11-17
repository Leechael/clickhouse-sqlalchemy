# Issue #200 Clickhouse Integration Table Engines

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/200
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2022-09-15T11:57:50Z
- Updated: 2022-09-15T15:58:44Z
- Author: AEzzatA
- Labels: none
- Comments: 1

## 判断
ClickHouse Integration table engines 支持缺口。

## 本地 fork 现状
engines 包主要覆盖 MergeTree/Distributed/Kafka/Buffer 等，需比对 integration engines。

## 建议动作
按 ClickHouse engine 清单补缺失引擎。

## Issue 摘要
Currently I want to build a model using [RabbitMQ Engine ](https://clickhouse.com/docs/en/engines/table-engines/integrations/rabbitmq/) However I see that its not implemented here. so while I can survive using raw queries for this model; the problem is the models, I would then define some models outside of the python codebase. so is there a solution for this already I couldn't fine?
