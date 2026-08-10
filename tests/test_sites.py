from unittest import mock

from sherlock_project.sites import SiteInformation


def test_site_information_preserves_explicit_unclaimed_username():
    with mock.patch("sherlock_project.sites.secrets.token_urlsafe", return_value="generated"):
        site = SiteInformation("Example", "https://example.test", "https://example.test/{}", "claimed", {}, False, "known")

    assert site.username_unclaimed == "known"
