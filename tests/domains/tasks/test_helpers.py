from datetime import datetime

import pytest

from taskmajor.domains.tasks._helpers import coerce_datetime, is_taskwarrior_date_expr


def test_coerce_datetime_iso_z():
    dt = coerce_datetime("2026-05-08T10:00:00Z")
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None


@pytest.mark.parametrize("expr", ["today", "now+1d", "eod", "tomorrow"])
def test_coerce_datetime_tw_expr(expr):
    assert coerce_datetime(expr) is None
    assert is_taskwarrior_date_expr(expr)


def test_coerce_datetime_empty_and_invalid():
    assert coerce_datetime("") is None
    assert is_taskwarrior_date_expr("") is False
    assert coerce_datetime("not-a-date") is None
    assert is_taskwarrior_date_expr("not-a-date") is True
