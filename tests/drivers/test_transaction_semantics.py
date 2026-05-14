import pytest
from sqlalchemy.exc import ArgumentError

from clickhouse_sqlalchemy.drivers.base import ClickHouseDialect


class _DBAPIConnection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.executed = []

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def execute(self, statement):
        self.executed.append(statement)


def test_transaction_hooks_are_noops():
    dialect = ClickHouseDialect()
    connection = _DBAPIConnection()

    assert dialect.do_begin(connection) is None
    assert dialect.do_commit(connection) is None
    assert dialect.do_rollback(connection) is None

    assert connection.commits == 0
    assert connection.rollbacks == 0
    assert connection.executed == []


def test_only_autocommit_isolation_level_is_supported():
    dialect = ClickHouseDialect()
    connection = _DBAPIConnection()

    assert dialect.get_isolation_level_values(connection) == ['AUTOCOMMIT']
    assert dialect.get_default_isolation_level(connection) == 'AUTOCOMMIT'
    assert dialect.get_isolation_level(connection) == 'AUTOCOMMIT'
    assert dialect.detect_autocommit_setting(connection) is True
    assert dialect._assert_and_set_isolation_level(
        connection,
        'AUTOCOMMIT',
    ) is None

    with pytest.raises(ArgumentError, match='Invalid value'):
        dialect._assert_and_set_isolation_level(
            connection,
            'READ COMMITTED',
        )


def test_savepoints_are_not_supported():
    dialect = ClickHouseDialect()
    connection = _DBAPIConnection()

    for method in (
        dialect.do_savepoint,
        dialect.do_rollback_to_savepoint,
        dialect.do_release_savepoint,
    ):
        with pytest.raises(NotImplementedError, match='SAVEPOINT'):
            method(connection, 'sa_savepoint_1')

    assert connection.executed == []
