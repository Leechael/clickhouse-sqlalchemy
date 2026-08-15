# Issue #251 Is clickhouse-sqlalchemy support integrating with  flask-sqlalchemy?

- Upstream: https://github.com/xzkostyan/clickhouse-sqlalchemy/issues/251
- Category: 问答
- Priority: low
- Created: 2023-06-13T11:27:42Z
- Updated: 2023-06-21T01:14:11Z
- Author: flyly0755
- Labels: none
- Comments: 2

## 判断
Flask-SQLAlchemy 集成是用法/集成问答。

## 本地 fork 现状
历史评论已有 query_class 示例；仓库无 Flask wrapper。

## 建议动作
整理推荐用法到文档或回复不提供直接 wrapper。

## Issue 摘要
**Describe the bug** With flask-sqlalchemy, ORM class showed as below, inherit db.Model where db come from SQLAlchemy(app) ```python from flask import Flask from flask_sqlalchemy import SQLAlchemy app = Flask(__name__) app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///example.sqlite" db = SQLAlchemy(app) class User(db.Model): id = db.Column(db.Integer, primary_key=True) username = db.Column(db.String, unique=True, n...
