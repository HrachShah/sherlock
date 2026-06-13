"""Tests for sherlock_project.sherlock.output_path_for().

The helper centralizes how ``--output`` and ``--folderoutput`` resolve to a
concrete on-disk path for each output format. The behavior was previously
inlined three times (one per output format), with two of those copies
silently dropping the user's ``--output`` path on the floor whenever
``--csv`` or ``--xlsx`` was also given. These tests pin the new contract.
"""

import argparse
import os
import tempfile

from sherlock_project.sherlock import output_path_for


def _ns(**overrides):
    """Build a minimal argparse Namespace that mimics what main() sees."""
    defaults = {"output": None, "folderoutput": None}
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_no_output_no_folder_uses_cwd_relative_username():
    """When neither --output nor --folderoutput is set, return username + suffix."""
    assert output_path_for(_ns(), "alice", ".txt") == "alice.txt"
    assert output_path_for(_ns(), "alice", ".csv") == "alice.csv"
    assert output_path_for(_ns(), "alice", ".xlsx") == "alice.xlsx"


def test_output_with_extension_swaps_to_requested_suffix():
    """--output foo.txt with --csv should land at foo.csv, not foo.txt."""
    ns = _ns(output="foo.txt")
    assert output_path_for(ns, "alice", ".txt") == "foo.txt"
    assert output_path_for(ns, "alice", ".csv") == "foo.csv"
    assert output_path_for(ns, "alice", ".xlsx") == "foo.xlsx"


def test_output_without_extension_just_appends_suffix():
    """A bare --output path without an extension should get the suffix appended."""
    ns = _ns(output="reports/alice")
    assert output_path_for(ns, "alice", ".csv") == "reports/alice.csv"
    assert output_path_for(ns, "alice", ".xlsx") == "reports/alice.xlsx"


def test_output_in_nested_directory_keeps_directory():
    """--output with a directory prefix should be preserved across formats."""
    ns = _ns(output="out/run42/alice.txt")
    assert output_path_for(ns, "alice", ".csv") == "out/run42/alice.csv"
    assert output_path_for(ns, "alice", ".xlsx") == "out/run42/alice.xlsx"


def test_folderoutput_creates_directory_and_uses_username_basename():
    """--folderoutput should make the dir if missing and put <username><suffix> in it."""
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "new_subdir")
        ns = _ns(folderoutput=target)
        result = output_path_for(ns, "alice", ".csv")
        assert result == os.path.join(target, "alice.csv")
        assert os.path.isdir(target)


def test_output_takes_precedence_over_folderoutput():
    """When both are set the main() guard already rejects this, but if the
    helper is called with both, --output should still win (defensive)."""
    ns = _ns(output="foo.txt", folderoutput="ignored")
    assert output_path_for(ns, "alice", ".csv") == "foo.csv"


def test_tar_gz_extension_only_strips_last_suffix():
    """A multi-dot path like foo.tar.gz should only have the trailing .gz stripped."""
    ns = _ns(output="archives/foo.tar.gz")
    assert output_path_for(ns, "alice", ".csv") == "archives/foo.tar.csv"
