"""Tests for sherlock_project.notify.QueryNotifyPrint."""
import io
import sys

import pytest

from sherlock_project import notify as notify_module
from sherlock_project.notify import QueryNotifyPrint
from sherlock_project.result import QueryResult, QueryStatus


@pytest.fixture(autouse=True)
def _reset_globvar():
    """Reset the module-level globvar between tests so they don't bleed."""
    notify_module.globvar = 0
    yield
    notify_module.globvar = 0


def _result(site: str, status: QueryStatus) -> QueryResult:
    return QueryResult(
        username="alice",
        site_name=site,
        site_url_user=f"https://example.com/{site}",
        status=status,
    )


def _capture_finish(n: QueryNotifyPrint) -> str:
    buf = io.StringIO()
    old, sys.stdout = sys.stdout, buf
    try:
        n.finish()
    finally:
        sys.stdout = old
    return buf.getvalue()


def test_finish_does_not_double_increment_globvar(capsys):
    """finish() must not mutate the claim counter as a side effect.

    Before the fix, finish() called self.countResults() which incremented
    globvar, then subtracted 1 in the print line. That works for a single
    call, but it leaks the side effect: if start()/update()/finish() are
    ever called again (e.g. a future batch mode that searches several
    usernames in one process), the printed count is off by the number of
    finish() calls.
    """
    n = QueryNotifyPrint()
    for i in range(3):
        n.update(_result(f"site{i}", QueryStatus.CLAIMED))
    assert notify_module.globvar == 3
    output = _capture_finish(n)
    assert notify_module.globvar == 3, "finish() must not increment globvar"
    assert "3" in output
    assert "results" in output


def test_finish_reports_zero_when_no_claims(capsys):
    n = QueryNotifyPrint()
    output = _capture_finish(n)
    assert "0" in output
    assert notify_module.globvar == 0


def test_finish_ignores_non_claimed_updates(capsys):
    n = QueryNotifyPrint()
    for i in range(5):
        n.update(_result(f"site{i}", QueryStatus.AVAILABLE))
    output = _capture_finish(n)
    assert "0" in output
    assert notify_module.globvar == 0


def test_finish_works_across_repeated_cycles(capsys):
    """Re-running start/update/finish in one process must keep counts accurate."""
    n = QueryNotifyPrint()
    for cycle in range(2):
        n.start(f"user{cycle}")
        for i in range(2):
            n.update(_result(f"site{cycle}_{i}", QueryStatus.CLAIMED))
        _capture_finish(n)
    assert notify_module.globvar == 4
