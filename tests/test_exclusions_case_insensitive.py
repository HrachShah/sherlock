"""Tests for case-insensitive do_not_exclude matching in SitesInformation."""

import json
import os
from unittest import mock

import pytest

from sherlock_project.sites import SitesInformation


@pytest.fixture
def data_path():
    return os.path.join(os.path.dirname(__file__), "..", "sherlock_project", "resources", "data.json")


def _mock_exclusions_response(exclusions_list):
    response = mock.MagicMock()
    response.status_code = 200
    response.text = "\n".join(exclusions_list)
    return response


def test_do_not_exclude_is_case_insensitive(data_path):
    """--site github should un-exclude 'GitHub' the same as --site GitHub would."""
    with open(data_path) as f:
        data = json.load(f)
    assert "GitHub" in data
    github_url = data["GitHub"]["url"]

    exclusions_response = _mock_exclusions_response(["GitHub", "Twitter", "Reddit"])
    with mock.patch("sherlock_project.sites.requests.get", return_value=exclusions_response):
        # Lowercase user input
        sites = SitesInformation(data_file_path=data_path, honor_exclusions=True, do_not_exclude=["github"])

    assert "GitHub" in [s.name for s in sites]
    assert all(s.name != "Twitter" for s in sites)
    assert all(s.name != "Reddit" for s in sites)
    assert github_url == next(s.information["url"] for s in sites if s.name == "GitHub")


def test_do_not_exclude_exact_case_still_works(data_path):
    """The original behavior must keep working when the user types the exact case."""
    exclusions_response = _mock_exclusions_response(["GitHub", "Twitter", "Reddit"])
    with mock.patch("sherlock_project.sites.requests.get", return_value=exclusions_response):
        sites = SitesInformation(data_file_path=data_path, honor_exclusions=True, do_not_exclude=["GitHub"])

    assert "GitHub" in [s.name for s in sites]
    assert all(s.name != "Twitter" for s in sites)
    assert all(s.name != "Reddit" for s in sites)


def test_empty_do_not_exclude_removes_all_excluded(data_path):
    """No --site flag means every excluded site is removed as before."""
    exclusions_response = _mock_exclusions_response(["GitHub", "Twitter", "Reddit"])
    with mock.patch("sherlock_project.sites.requests.get", return_value=exclusions_response):
        sites = SitesInformation(data_file_path=data_path, honor_exclusions=True, do_not_exclude=[])

    assert all(s.name not in {"GitHub", "Twitter", "Reddit"} for s in sites)


def test_do_not_exclude_mixed_case(data_path):
    """A mix of case-folded inputs should still un-exclude the right site."""
    exclusions_response = _mock_exclusions_response(["GitHub", "Twitter", "Reddit"])
    with mock.patch("sherlock_project.sites.requests.get", return_value=exclusions_response):
        sites = SitesInformation(
            data_file_path=data_path,
            honor_exclusions=True,
            do_not_exclude=["github", "TWITTER", "Reddit"],
        )

    names = [s.name for s in sites]
    assert "GitHub" in names
    assert "Twitter" in names
    assert "Reddit" in names
