from sherlock_project.sites import SiteInformation


def test_site_information_preserves_supplied_unclaimed_username():
    site = SiteInformation(
        "Example",
        "https://example.com",
        "https://example.com/{}",
        "claimed",
        {},
        False,
        username_unclaimed="known-to-be-free",
    )

    assert site.username_unclaimed == "known-to-be-free"
