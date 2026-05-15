from datetime import datetime, time

from asynch.proto.utils.escape import escape_param


def test_escape_param_datetime_includes_microseconds():
    value = datetime(2026, 1, 1, 0, 0, 0, 123000)
    escaped = escape_param(value)
    assert escaped == "'2026-01-01 00:00:00.123000'"


def test_escape_param_time_includes_microseconds():
    value = time(12, 34, 56, 789000)
    escaped = escape_param(value)
    assert escaped == "'12:34:56.789000'"


def test_escape_param_datetime_no_microseconds():
    value = datetime(2026, 1, 1, 0, 0, 0)
    escaped = escape_param(value)
    assert escaped == "'2026-01-01 00:00:00.000000'"
