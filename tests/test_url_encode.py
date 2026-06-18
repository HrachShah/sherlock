"""Tests for sherlock_project.sherlock.encode_username_for_url.

These verify that usernames are percent-encoded for safe inclusion in
URL paths/query strings. The prior implementation used
``username.replace(' ', '%20')`` which only handled spaces.
"""
from sherlock_project.sherlock import encode_username_for_url


def test_plain_username_unchanged():
    assert encode_username_for_url("alice") == "alice"


def test_dot_and_dash_preserved():
    # unreserved chars from RFC 3986 must not be percent-encoded
    assert encode_username_for_url("john.doe") == "john.doe"
    assert encode_username_for_url("john-doe") == "john-doe"


def test_space_encoded_to_percent_20():
    assert encode_username_for_url("john doe") == "john%20doe"


def test_question_mark_encoded():
    # a raw '?' would be parsed as a query-string delimiter by the server
    assert encode_username_for_url("bob?admin") == "bob%3Fadmin"


def test_hash_encoded():
    # a raw '#' would be parsed as a fragment delimiter
    assert encode_username_for_url("bob#frag") == "bob%23frag"


def test_ampersand_encoded():
    # a raw '&' would be parsed as a new query parameter
    assert encode_username_for_url("bob&jane") == "bob%26jane"


def test_plus_encoded():
    # a raw '+' is decoded as a space by form/urlencoded parsers
    assert encode_username_for_url("bob+test") == "bob%2Btest"


def test_percent_encoded():
    # a raw '%' would corrupt the prior percent-encoding in the URL
    assert encode_username_for_url("100%done") == "100%25done"


def test_slash_encoded():
    # a raw '/' would be parsed as a new path segment
    assert encode_username_for_url("bob/x") == "bob%2Fx"


def test_non_ascii_encoded():
    # non-ASCII characters must be percent-encoded so the URL is well-formed
    assert encode_username_for_url("naïve") == "na%C3%AFve"


def test_emoji_encoded():
    # emoji are 4-byte UTF-8 sequences; each byte must be percent-encoded
    result = encode_username_for_url("a😀b")
    assert result == "a%F0%9F%98%80b"


def test_underscore_and_tilde_preserved():
    # '_' and '~' are in the unreserved set per RFC 3986
    assert encode_username_for_url("a_b~c") == "a_b~c"


def test_empty_string():
    assert encode_username_for_url("") == ""


def test_only_unsafe_chars():
    assert encode_username_for_url("?&=#+%") == "%3F%26%3D%23%2B%25"
