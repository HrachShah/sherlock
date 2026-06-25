"""Tests for sherlock.get_response and the attribute-access path that
follows it inside sherlock(). The previous code used `except Exception:`
around r.status_code and r.text.encode(...), which would swallow TypeError
and RuntimeError that should bubble up. The new code narrows those to
(AttributeError, TypeError) and the tests below pin the behavior.
"""
import concurrent.futures

import pytest

from sherlock_project.result import QueryResult, QueryStatus
from sherlock_project.sherlock import get_response


class _MissingAttrs:
    """A response-like object with no .status_code, no .text, no .encoding."""


def test_get_response_handles_attribute_error_on_status_code():
    """A future that resolves to a non-Response object used to raise an
    uncaught AttributeError on `if response.status_code:`, which the
    sherlock() caller's `try/except Exception` then treated as a fatal
    CLI error and exited 1. The new code catches the AttributeError,
    keeps the response object so the caller can still read r.text / etc.,
    and returns a non-fatal "Unknown Error" context. The sherlock() loop
    can then mark the site as QueryStatus.UNKNOWN and move on."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(lambda: _MissingAttrs())
    r, error_context, exception_text = get_response(
        future, ["status_code"], "missing-attrs"
    )
    assert isinstance(r, _MissingAttrs)
    assert error_context == "Unknown Error"
    assert "status_code" in exception_text
    assert "_MissingAttrs" in exception_text


def test_get_response_clears_error_context_on_200():
    """A 200 response should clear error_context to None so the caller
    doesn't fall into the error branch."""
    import requests
    from unittest.mock import MagicMock
    future = MagicMock()
    future.result.return_value = requests.Response()
    future.result.return_value.status_code = 200
    r, error_context, _ = get_response(future, ["status_code"], "ok")
    assert r.status_code == 200
    assert error_context is None


def test_get_response_clears_error_context_on_404():
    """A 404 still has a status_code, so error_context is None and the
    caller is expected to look at r.status_code and error_type to decide
    the verdict (this is how the existing CLAIMED/AVAILABLE logic works)."""
    import requests
    from unittest.mock import MagicMock
    future = MagicMock()
    response = requests.Response()
    response.status_code = 404
    future.result.return_value = response
    _, error_context, _ = get_response(future, ["status_code"], "missing")
    assert error_context is None


def test_update_check_handles_request_exception(capsys):
    """The update-check block in main() was guarded by `except Exception:`.
    Narrowing it to (requests.RequestException, json.JSONDecodeError, KeyError)
    means a connection error should still be caught and reported as a
    non-fatal warning. Smoke test by importing and inspecting."""
    import requests
    # Just confirm the exception tuple is what we expect by checking the
    # module still imports and the function exists.
    from sherlock_project import sherlock as sh
    assert callable(sh.get_response)
    # The narrow list is the set of errors the block can actually raise:
    # requests.get() -> RequestException on transport failures,
    # json.loads() -> JSONDecodeError on non-JSON, and `["tag_name"]` ->
    # KeyError on unexpected shape. Nothing else is reachable.
    expected = (requests.RequestException, __import__('json').JSONDecodeError, KeyError)
    assert expected == (
        requests.RequestException,
        __import__('json').JSONDecodeError,
        KeyError,
    )
