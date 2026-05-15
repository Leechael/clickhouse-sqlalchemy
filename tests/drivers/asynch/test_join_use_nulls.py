import pytest
from unittest.mock import MagicMock, patch

from clickhouse_sqlalchemy.drivers.asynch.connector import AsyncAdapt_asynch_dbapi


class FakeAsynch:
    class errors:
        class ServerException(Exception):
            pass
        class UnexpectedPacketFromServerError(Exception):
            pass
        class LogicalError(Exception):
            pass
        class UnknownTypeError(Exception):
            pass
        class ChecksumDoesntMatchError(Exception):
            pass
        class TypeMismatchError(Exception):
            pass
        class UnknownCompressionMethod(Exception):
            pass
        class TooLargeStringSize(Exception):
            pass
        class NetworkError(Exception):
            pass
        class SocketTimeoutError(Exception):
            pass
        class UnknownPacketFromServerError(Exception):
            pass
        class CannotParseUuidError(Exception):
            pass
        class CannotParseDomainError(Exception):
            pass
        class PartiallyConsumedQueryError(Exception):
            pass
        class ColumnException(Exception):
            pass
        class ColumnTypeMismatchException(Exception):
            pass
        class StructPackException(Exception):
            pass
        class InterfaceError(Exception):
            pass
        class DatabaseError(Exception):
            pass
        class ProgrammingError(Exception):
            pass
        class NotSupportedError(Exception):
            pass

    class connection:
        class Connection:
            def __init__(self, *args, **kwargs):
                self._args = args
                self._kwargs = kwargs


def test_connect_injects_join_use_nulls_by_default():
    dbapi = AsyncAdapt_asynch_dbapi(FakeAsynch)
    with patch.object(dbapi.asynch.connection, "Connection") as mock_conn_cls:
        dbapi.connect("dsn", settings={"async_insert": 1})
        call_kwargs = mock_conn_cls.call_args.kwargs
        assert call_kwargs["settings"]["join_use_nulls"] == 1
        assert call_kwargs["settings"]["async_insert"] == 1


def test_connect_preserves_explicit_join_use_nulls():
    dbapi = AsyncAdapt_asynch_dbapi(FakeAsynch)
    with patch.object(dbapi.asynch.connection, "Connection") as mock_conn_cls:
        dbapi.connect("dsn", settings={"join_use_nulls": 0})
        call_kwargs = mock_conn_cls.call_args.kwargs
        assert call_kwargs["settings"]["join_use_nulls"] == 0
