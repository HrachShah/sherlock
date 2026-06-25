"""Regression tests for the xlsx export.

The --xlsx branch in sherlock_project.sherlock.main() used to write
f"{username}.xlsx" into the current working directory regardless of
whether the user supplied --folderoutput. Every other output format
(txt, csv) honors --folderoutput, so a user who ran
'sherlock --xlsx --folderoutput reports alice bob' would get
alice.txt / bob.txt under reports/ but alice.xlsx / bob.xlsx dumped
into the cwd. These tests run main() with a fully-mocked network layer
so they do not need internet access, and they assert where the xlsx
file is actually written.
"""
import os
import sys

import pandas as pd
import pytest
import requests_mock

from sherlock_project import sherlock as sherlock_mod
from sherlock_project.notify import QueryNotifyPrint
from sherlock_project.result import QueryResult, QueryStatus


FORGE_LATEST_RELEASE_URL = sherlock_mod.forge_api_latest_release
EXCLUSIONS_URL = (
    "https://raw.githubusercontent.com/sherlock-project/sherlock/"
    "refs/heads/exclusions/false_positive_exclusions.txt"
)
MANIFEST_URL = "https://data.sherlockproject.xyz"


def _stub_network(m, sites, version="v0.16.0"):
    """Stub every URL main() would otherwise hit on startup."""
    # Forge latest-release ping (update-notice block).
    m.get(FORGE_LATEST_RELEASE_URL, json={"tag_name": version, "html_url": "x"})
    # Exclusions list used by SitesInformation.
    m.get(EXCLUSIONS_URL, text="")
    # Live manifest served from MANIFEST_URL when --local is not set.
    m.get(MANIFEST_URL, json={})


def _stub_sherlock_lookup(monkeypatch):
    """Skip the per-site network probe by replacing sherlock() with a stub.

    The stub returns a single fake 'Claimed' result for one site, so the
    output-writer code paths in main() are exercised without hitting
    the real Sherlock site data.
    """
    def fake_sherlock(username, site_data, query_notify, **kwargs):
        return {
            "GitHub": {
                "url_main": "https://github.com",
                "url_user": f"https://github.com/{username}",
                "http_status": 200,
                "status": QueryResult(
                    username=username,
                    site_name="GitHub",
                    site_url_user=f"https://github.com/{username}",
                    status=QueryStatus.CLAIMED,
                    query_time=0.42,
                ),
            }
        }
    monkeypatch.setattr("sherlock_project.sherlock.sherlock", fake_sherlock)


def _stub_xlsx_writer(monkeypatch, captured):
    """Capture the path passed to pd.DataFrame.to_excel()."""
    real_to_excel = pd.DataFrame.to_excel

    def fake_to_excel(self, path, *args, **kwargs):
        captured["path"] = path
        # Don't actually write a file; we only care about the path arg.
        return None

    monkeypatch.setattr("sherlock_project.sherlock.pd.DataFrame.to_excel", fake_to_excel)
    return real_to_excel


def _run_main_with_args(monkeypatch, tmp_path, *, folderoutput, extra_args):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    with requests_mock.Mocker() as m:
        _stub_network(m, sites=None)
        _stub_sherlock_lookup(monkeypatch)

        captured = {}
        _stub_xlsx_writer(monkeypatch, captured)

        argv = ["sherlock", "--xlsx", "--print-all", "alice"]
        if folderoutput is not None:
            argv.insert(-1, f"--folderoutput={folderoutput}")

        monkeypatch.setattr(sys, "argv", argv)
        try:
            sherlock_mod.main()
        except SystemExit as exc:
            # main() can call sys.exit() on argparse errors; treat those
            # as test failures because the test's argv should be valid.
            raise AssertionError(f"main() exited with {exc.code}")
    return captured


def test_xlsx_branch_writes_to_cwd_when_no_folderoutput(monkeypatch, tmp_path):
    captured = _run_main_with_args(monkeypatch, tmp_path, folderoutput=None, extra_args=[])
    assert captured.get("path") == "alice.xlsx"


def test_xlsx_branch_writes_under_folderoutput_when_supplied(monkeypatch, tmp_path):
    target = str(tmp_path / "reports")
    captured = _run_main_with_args(
        monkeypatch, tmp_path, folderoutput=target, extra_args=[]
    )
    assert captured.get("path") == os.path.join(target, "alice.xlsx")
