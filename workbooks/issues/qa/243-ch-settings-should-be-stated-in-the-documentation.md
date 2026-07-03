# Issue #243 ch_settings should be stated in the documentation

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/243
- Category: 问答
- Priority: low
- Created: 2023-04-20T06:11:33Z
- Updated: 2023-04-20T06:11:33Z
- Author: StygianSmash
- Labels: none
- Comments: 0

## 判断
ch_settings 文档说明请求。

## 本地 fork 现状
docs/features.rst 已有 settings 段落，connection 文档也提到参数。

## 建议动作
更新文档入口，明确 ch_settings/connect_args/execution_options 差异。

## Issue 摘要
developers should know that they can change clickhouse setting in http driver mode by setting `ch_settings`. ```python from sqlalchemy import create_engine engine = create_engine( 'clickhouse+http://localhost/test', connect_args={"ch_settings": {'max_execution_time': 10}} ) ```
