"""Tests for QueryNotifyPrint result counter and finish() reporting.

These tests pin the contract that:

* :meth:`QueryNotifyPrint.countResults` is a pure read — it must not
  mutate the underlying counter.
* :meth:`QueryNotifyPrint._recordClaimedResult` is the only method that
  increments the counter, and it should be called once per CLAIMED
  result inside :meth:`update`.
* :meth:`QueryNotifyPrint.finish` reports the exact count of claimed
  results it has been given, and is safe to call multiple times.

The pre-refactor code conflated the increment and the read inside
``countResults``, so ``finish()`` had to call ``countResults() - 1`` to
undo the increment caused by the read itself. That hid an off-by-one
any time ``finish()`` was called more than once, and it made the
"Search completed with N results" line sensitive to a side effect in a
function whose name suggested it was a pure getter.
"""
import re

import pytest

from sherlock_project import notify
from sherlock_project.notify import QueryNotifyPrint
from sherlock_project.result import QueryResult, QueryStatus


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


@pytest.fixture(autouse=True)
def _reset_counter():
    """Reset the module-level globvar between tests so each test starts at 0."""
    notify.globvar = 0
    yield
    notify.globvar = 0


def _make_claimed(site_name: str = "ExampleSite") -> QueryResult:
    return QueryResult(
        username="alice",
        site_name=site_name,
        site_url_user=f"https://example.com/{site_name}/alice",
        status=QueryStatus.CLAIMED,
        query_time=0.123,
    )


def _make_available(site_name: str = "OtherSite") -> QueryResult:
    return QueryResult(
        username="alice",
        site_name=site_name,
        site_url_user=f"https://example.com/{site_name}/alice",
        status=QueryStatus.AVAILABLE,
        query_time=0.050,
    )


def test_count_results_is_a_pure_read():
    notifier = QueryNotifyPrint()

    assert notifier.countResults() == 0
    # A second call must still return 0 — countResults must not bump the counter.
    assert notifier.countResults() == 0
    assert notifier.countResults() == 0


def test_record_claimed_result_increments_and_returns_new_total():
    notifier = QueryNotifyPrint()

    assert notifier._recordClaimedResult() == 1
    assert notifier._recordClaimedResult() == 2
    assert notifier._recordClaimedResult() == 3
    assert notifier.countResults() == 3


def test_update_with_claimed_result_increments_counter(capsys):
    notifier = QueryNotifyPrint()

    notifier.update(_make_claimed("Alpha"))
    notifier.update(_make_claimed("Beta"))
    notifier.update(_make_claimed("Gamma"))

    assert notifier.countResults() == 3
    # The status banner should still print normally for each claimed result.
    out = _strip_ansi(capsys.readouterr().out)
    assert "Alpha: https://example.com/Alpha/alice" in out
    assert "Beta: https://example.com/Beta/alice" in out
    assert "Gamma: https://example.com/Gamma/alice" in out


def test_update_with_non_claimed_result_does_not_increment_counter(capsys):
    notifier = QueryNotifyPrint(verbose=True, print_all=True)

    notifier.update(_make_available("First"))
    notifier.update(_make_claimed("Second"))
    notifier.update(_make_available("Third"))

    # Only the CLAIMED result should bump the counter.
    assert notifier.countResults() == 1


def test_finish_reports_exact_claimed_count(capsys):
    notifier = QueryNotifyPrint()

    for site_name in ("Reddit", "Twitter", "Mastodon", "GitHub"):
        notifier.update(_make_claimed(site_name))
    notifier.finish()

    out = _strip_ansi(capsys.readouterr().out)
    # The "Search completed with N results" line should reflect exactly 4.
    assert "Search completed with 4 results" in out


def test_finish_with_zero_claimed_results(capsys):
    notifier = QueryNotifyPrint()
    notifier.finish()

    out = _strip_ansi(capsys.readouterr().out)
    # With no claimed results, the counter must read 0, not -1 or 1.
    assert "Search completed with 0 results" in out


def test_finish_does_not_increment_counter(capsys):
    """finish() used to call countResults() which incremented the counter.

    Calling finish() twice must give the same result both times — the
    second call should not push the reported number up by one.
    """
    notifier = QueryNotifyPrint()

    notifier.update(_make_claimed("Alpha"))
    notifier.update(_make_claimed("Beta"))

    notifier.finish()
    first_count = notifier.countResults()
    capsys.readouterr()  # discard output from first finish

    notifier.finish()
    second_count = notifier.countResults()
    second_output = _strip_ansi(capsys.readouterr().out)

    # The reported number is stable across multiple finish() calls.
    assert first_count == 2
    assert second_count == 2
    assert "Search completed with 2 results" in second_output
