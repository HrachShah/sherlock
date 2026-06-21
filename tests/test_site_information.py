"""Tests for sherlock_project.sites.SiteInformation."""

import pytest

from sherlock_project.sites import SiteInformation


class TestSiteInformation:
    def test_username_unclaimed_defaults_to_random_string(self):
        """When no username_unclaimed is passed, a random one is generated."""
        info = SiteInformation(
            "test", "https://example.com", "https://example.com/u/{}",
            "claimed_user", {}, False,
        )
        assert info.username_unclaimed
        assert info.username_unclaimed != "claimed_user"

    def test_username_unclaimed_defaults_are_unique_per_instance(self):
        """The default token_urlsafe() must be re-evaluated per instance.

        Previously the default was a function default argument, which is
        computed once at module import time — every SiteInformation() with
        no username_unclaimed got the SAME random string, defeating the
        point of a random "shouldn't exist" probe.
        """
        a = SiteInformation(
            "a", "https://example.com", "https://example.com/u/{}",
            "claimed", {}, False,
        )
        b = SiteInformation(
            "b", "https://example.com", "https://example.com/u/{}",
            "claimed", {}, False,
        )
        assert a.username_unclaimed != b.username_unclaimed

    def test_username_unclaimed_from_explicit_argument(self):
        """An explicit username_unclaimed is honoured, not overwritten.

        Previously the body unconditionally reassigned
        self.username_unclaimed = secrets.token_urlsafe(32), throwing away
        whatever the caller passed (and whatever the JSON data file
        supplied). This matters for tests and any tool that wants a
        deterministic unclaimed probe name.
        """
        info = SiteInformation(
            "test", "https://example.com", "https://example.com/u/{}",
            "claimed", {}, False,
            username_unclaimed="definitely-not-a-real-user-zzz",
        )
        assert info.username_unclaimed == "definitely-not-a-real-user-zzz"
