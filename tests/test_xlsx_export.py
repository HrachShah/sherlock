"""Tests for the ``.xlsx`` export logic in :mod:`sherlock_project.sherlock`.

The pre-fix code in :func:`sherlock_project.sherlock.main` initialised
``response_time_s = []`` and then immediately gated on
``if response_time_s is None:`` — a condition that could never be true
because the list had just been set to a fresh empty list. The intent,
matching the CSV branch immediately above, was to write an empty string
when the site's ``QueryResult.query_time`` was ``None`` and the float
otherwise. Without the fix, ``response_time_s`` always held a mixed
list of floats and ``None`` values, and the resulting DataFrame column
became a pandas ``object`` dtype carrying ``None`` values, which both
confused downstream consumers and silently lost the information that
the request did not complete normally (the original meaning of the
empty-string sentinel).

These tests pin the per-site column-building helper so the contract
survives further refactors.
"""
import pytest

from sherlock_project.result import QueryResult, QueryStatus
from sherlock_project.sherlock import _build_xlsx_dataframe


def _result(site_name, status, query_time):
    return QueryResult(
        username="hrach",
        site_name=site_name,
        site_url_user=f"https://example.com/{site_name}/hrach",
        status=status,
        query_time=query_time,
    )


def _row(site_name, status, query_time, http_status=200):
    return {
        "status": _result(site_name, status, query_time),
        "url_main": f"https://example.com/{site_name}",
        "url_user": f"https://example.com/{site_name}/hrach",
        "http_status": http_status,
    }


def test_xlsx_dataframe_keeps_float_query_time():
    results = {"github": _row("github", QueryStatus.CLAIMED, 0.123)}
    df = _build_xlsx_dataframe("hrach", results, print_found=False, print_all=True)
    assert list(df["response_time_s"]) == [0.123]
    assert list(df["name"]) == ["github"]


def test_xlsx_dataframe_uses_empty_string_for_missing_query_time():
    """query_time is None for the request that never completed; the xlsx
    column should carry an empty string sentinel, not None."""
    results = {"github": _row("github", QueryStatus.UNKNOWN, None)}
    df = _build_xlsx_dataframe("hrach", results, print_found=False, print_all=True)
    assert list(df["response_time_s"]) == [""]
    # An empty string is the explicit choice: the type stays consistent
    # with the float case and downstream tools (Excel) treat it as
    # blank rather than a broken cell.
    assert "" in list(df["response_time_s"])
    assert None not in list(df["response_time_s"])


def test_xlsx_dataframe_mixes_present_and_missing_query_times():
    results = {
        "github": _row("github", QueryStatus.CLAIMED, 0.5),
        "gitlab": _row("gitlab", QueryStatus.UNKNOWN, None),
        "bitbucket": _row("bitbucket", QueryStatus.CLAIMED, 1.25),
    }
    df = _build_xlsx_dataframe("hrach", results, print_found=False, print_all=True)
    response_times = list(df["response_time_s"])
    assert len(response_times) == 3
    assert 0.5 in response_times
    assert 1.25 in response_times
    assert "" in response_times
    # No None leaking through (this is the regression guard for the
    # original `if response_time_s is None` dead-code bug).
    assert None not in response_times


def test_xlsx_dataframe_respects_print_found_filter():
    results = {
        "github": _row("github", QueryStatus.CLAIMED, 0.5),
        "gitlab": _row("gitlab", QueryStatus.AVAILABLE, 0.25),
    }
    df = _build_xlsx_dataframe(
        "hrach", results, print_found=True, print_all=False
    )
    # When --print-found is set without --print-all, only CLAIMED sites
    # make it into the spreadsheet.
    assert list(df["name"]) == ["github"]
    assert list(df["response_time_s"]) == [0.5]


def test_xlsx_dataframe_url_columns_use_hyperlink_formula():
    results = {"github": _row("github", QueryStatus.CLAIMED, 0.1)}
    df = _build_xlsx_dataframe("hrach", results, print_found=False, print_all=True)
    assert list(df["url_main"]) == ['=HYPERLINK("https://example.com/github")']
    assert list(df["url_user"]) == [
        '=HYPERLINK("https://example.com/github/hrach")'
    ]


def test_xlsx_dataframe_empty_results_yields_empty_dataframe():
    df = _build_xlsx_dataframe("hrach", {}, print_found=False, print_all=True)
    expected_columns = {
        "username",
        "name",
        "url_main",
        "url_user",
        "exists",
        "http_status",
        "response_time_s",
    }
    assert set(df.columns) == expected_columns
    assert len(df) == 0
