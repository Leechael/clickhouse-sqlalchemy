# Issue #371 Conda installation requires SQLAlchemy 1.4

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/371
- Category: 问答
- Priority: low
- Created: 2025-03-24T05:12:47Z
- Updated: 2025-05-16T17:07:29Z
- Author: vant7
- Labels: none
- Comments: 1

## 判断
Conda 包依赖元数据滞后通常在 conda-forge feedstock 维护，不一定在本仓库修。

## 本地 fork 现状
项目本身 pyproject 已要求 SQLAlchemy>=2。

## 建议动作
引导去 conda-forge recipe 更新依赖；本仓库可补安装文档说明。

## Issue 摘要
**Describe the bug** Conda installation requires sqlachemy of 1.4. Extracting out package informations from [conda-forge](https://anaconda.org/conda-forge/clickhouse-sqlalchemy/files) I see `info/meta.yaml` ``` # This file created by conda-build 24.5.1 # meta.yaml template originally from: # /home/conda/recipe_root, last modified Wed Jun 12 16:00:06 2024 # ------------------------------------------------ package: nam...
