#!/usr/bin/env python3
"""test_bob_log.py — Integration tests for bob_log.py

Each test case operates in an isolated temporary git repository so the
real repo is never touched.  Tests call the command functions directly
(bypassing argparse) to avoid shell quoting concerns.

Run with:
    python3 test_bob_log.py
"""

import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Point bob_log.py at the temp repo rather than cwd
# ---------------------------------------------------------------------------
# bob_log uses subprocess.run(["git", ...]) without a cwd argument, so we
# patch it to inject cwd=REPO for every git call during each test.

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import bob_log  # noqa: E402  (import after path manipulation)


def _make_ns(**kwargs) -> types.SimpleNamespace:
    """Build a minimal argparse-style Namespace from keyword args."""
    return types.SimpleNamespace(**kwargs)


class TestBobLog(unittest.TestCase):
    """Full integration suite — every test gets a fresh git repo."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def setUp(self) -> None:
        self.repo_dir = tempfile.mkdtemp(prefix="bob_log_test_")
        env = {**os.environ, "GIT_DIR": os.path.join(self.repo_dir, ".git")}

        def _run(*args):
            subprocess.run(
                list(args),
                cwd=self.repo_dir,
                check=True,
                capture_output=True,
            )

        _run("git", "init")
        _run("git", "config", "user.email", "test@test.local")
        _run("git", "config", "user.name", "Test")

        # Redirect bob_log's _git() calls into our temp repo
        orig_git = bob_log._git

        def _patched_git(*args, input=None, check=True):
            # Mirror bob_log._git exactly, but redirect to self.repo_dir.
            # Strip the "-c core.autocrlf=false" prefix that bob_log._git already prepends
            # so we don't duplicate it when we re-add it below.
            clean_args = list(args)
            if len(clean_args) >= 2 and clean_args[0] == "-c" and clean_args[1] == "core.autocrlf=false":
                clean_args = clean_args[2:]
            raw_input = input.encode("utf-8") if input is not None else None
            result = subprocess.run(
                ["git", "-c", "core.autocrlf=false"] + clean_args,
                cwd=self.repo_dir,
                capture_output=True,
                input=raw_input,
            )
            result.stdout = result.stdout.decode("utf-8", errors="replace")
            result.stderr = result.stderr.decode("utf-8", errors="replace")
            if check and result.returncode != 0:
                raise RuntimeError(
                    f"git {' '.join(clean_args)!r} failed (exit {result.returncode}):\n"
                    f"{result.stderr.strip()}"
                )
            return result

        self._orig_git = orig_git
        bob_log._git = _patched_git

    def tearDown(self) -> None:
        bob_log._git = self._orig_git
        import shutil
        shutil.rmtree(self.repo_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Sub-Task 2 tests
    # ------------------------------------------------------------------

    def test_init_creates_branch(self) -> None:
        """bob-log init should create the bob-context branch."""
        bob_log.cmd_init(_make_ns())
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "bob-context"],
            cwd=self.repo_dir,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, "bob-context branch should exist after init")

    def test_init_is_idempotent(self) -> None:
        """Running init twice should not raise or corrupt the branch."""
        bob_log.cmd_init(_make_ns())
        sha1 = subprocess.run(
            ["git", "rev-parse", "bob-context"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        ).stdout.strip()
        bob_log.cmd_init(_make_ns())  # second call
        sha2 = subprocess.run(
            ["git", "rev-parse", "bob-context"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(sha1, sha2, "Second init should leave branch pointer unchanged")

    def test_write_then_read(self) -> None:
        """Write a file and read it back — content must match exactly."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="notes.md", content="hello world\n"))
        out = bob_log._read_blob("notes.md")
        self.assertIn("hello world", out)

    def test_write_overwrites(self) -> None:
        """A second write to the same path should replace the content."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="file.md", content="original\n"))
        bob_log.cmd_write(_make_ns(path="file.md", content="replaced\n"))
        out = bob_log._read_blob("file.md")
        self.assertIn("replaced", out)
        self.assertNotIn("original", out)

    def test_append_accumulates(self) -> None:
        """Append should add to, not replace, existing content."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="log.md", content="line1\n"))
        bob_log.cmd_append(_make_ns(path="log.md", content="line2\n"))
        out = bob_log._read_blob("log.md")
        self.assertIn("line1", out)
        self.assertIn("line2", out)

    def test_append_creates_if_absent(self) -> None:
        """Append to a non-existent file should create it."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_append(_make_ns(path="new.md", content="fresh content\n"))
        out = bob_log._read_blob("new.md")
        self.assertIn("fresh content", out)

    def test_working_tree_untouched(self) -> None:
        """Writing to the shadow branch must NOT create files in the working tree."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="secret.md", content="sensitive data\n"))
        self.assertFalse(
            (Path(self.repo_dir) / "secret.md").exists(),
            "shadow-branch write must not create a file in the working tree",
        )

    def test_ls_lists_files(self) -> None:
        """ls at the root should show written files."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="alpha.md", content="a\n"))
        bob_log.cmd_write(_make_ns(path="beta.md", content="b\n"))
        output = bob_log._list_tree("")
        self.assertIn("alpha.md", output)
        self.assertIn("beta.md", output)

    def test_ls_subdirectory(self) -> None:
        """ls should work on a subdirectory path."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="chat/alice.md", content="hi\n"))
        output = bob_log._list_tree("chat")
        self.assertIn("alice.md", output)

    def test_export_writes_file(self) -> None:
        """export should copy the shadow-branch file into the working tree."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="data.md", content="exported content\n"))
        dest = str(Path(self.repo_dir) / "out" / "data.md")
        bob_log.cmd_export(_make_ns(path="data.md", dest=dest))
        self.assertTrue(Path(dest).exists(), "export destination file should exist")
        self.assertIn("exported content", Path(dest).read_text())

    def test_path_jail_rejects_absolute(self) -> None:
        """Absolute paths must be rejected."""
        with self.assertRaises((ValueError, SystemExit)):
            bob_log._check_path("/etc/passwd")

    def test_path_jail_rejects_dotdot(self) -> None:
        """Paths containing '..' must be rejected."""
        with self.assertRaises((ValueError, SystemExit)):
            bob_log._check_path("../../escape")

    def test_commit_command(self) -> None:
        """commit should create a new commit on top of the existing HEAD."""
        bob_log.cmd_init(_make_ns())
        bob_log.cmd_write(_make_ns(path="x.md", content="x\n"))
        sha_before = subprocess.run(
            ["git", "rev-parse", "bob-context"],
            cwd=self.repo_dir, capture_output=True, text=True,
        ).stdout.strip()
        bob_log.cmd_commit(_make_ns(message="manual checkpoint"))
        sha_after = subprocess.run(
            ["git", "rev-parse", "bob-context"],
            cwd=self.repo_dir, capture_output=True, text=True,
        ).stdout.strip()
        self.assertNotEqual(sha_before, sha_after, "commit should advance branch pointer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
