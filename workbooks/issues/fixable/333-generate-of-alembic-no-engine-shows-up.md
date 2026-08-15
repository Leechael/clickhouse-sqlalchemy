# Issue #333 generate of alembic, no engine shows up

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/333
- Category: 我们可以跟进修复
- Priority: medium
- Created: 2024-08-29T15:57:34Z
- Updated: 2025-05-30T11:06:05Z
- Author: xodiumx
- Labels: none
- Comments: 1

## 判断
Alembic autogenerate engine 丢失问题，本 fork 已有 renderer，但需复现。

## 本地 fork 现状
alembic/renderers.py 覆盖 engine 渲染，tests/alembic/test_render_create_table.py 有相关测试。

## 建议动作
复现 issue 的模型；若仍丢 engine，补 comparator/render 测试。

## Issue 摘要
Hi, trying to use `alembic` in conjunction with `clickhouse_sqlalchemy`, but when running the command: ```sh alembic revision --autogenerate -m "init" ``` engine is not generated in the migration _______ **To Reproduce** ```python # env from logging.config import fileConfig from sqlalchemy import engine_from_config from sqlalchemy import pool from clickhouse_sqlalchemy.alembic.dialect import patch_alembic_version, in...
