#!/usr/bin/env python3
"""bob_log.py — Bob Logbook CLI

Operates on the `bob-context` shadow branch using git plumbing.
The working tree is never switched; all reads and writes go directly
through git object/ref manipulation.

Usage:
    bob-log init
    bob-log read <path>
    bob-log write <path> <content>
    bob-log append <path> <content>
    bob-log commit <message>
    bob-log ls [path]
    bob-log export <path> <dest>
"""

import argparse
import json
import os
import sys
import subprocess
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath

BRANCH = "bob-context"


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

def _check_path(path: str) -> None:
    """Raise ValueError if path would escape the shadow branch root or violate flat-structure rules.

    Allowed paths:
      - Any single-component filename at the root (e.g. 'notes.md', 'decisions.md')
      - chat/<username>.md — the one permitted subdirectory, used by the hook

    Everything else (arbitrary subdirectories) is rejected.
    """
    if path.startswith("/"):
        raise ValueError(f"Path must be relative, got: {path!r}")
    parts = PurePosixPath(path).parts
    if not parts:
        raise ValueError("Path must not be empty.")
    if ".." in parts:
        raise ValueError(f"Path must not contain '..': {path!r}")
    # Enforce flat structure: allow root files and chat/* only
    if len(parts) > 1:
        if parts[0] != "chat":
            raise ValueError(
                f"Subdirectories are not allowed (only root files and chat/* are permitted): {path!r}"
            )
        if len(parts) > 2:
            raise ValueError(f"Path inside chat/ must be a single filename: {path!r}")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(*args: str, input: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command, return CompletedProcess. Raises on non-zero exit when check=True."""
    # Use binary I/O so the OS never converts \n → \r\n in stdin/stdout regardless of platform
    # settings (Windows core.autocrlf, locale, etc.).  We decode stdout/stderr ourselves.
    raw_input = input.encode("utf-8") if input is not None else None
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false"] + list(args),
        capture_output=True,
        input=raw_input,
    )
    # Expose decoded strings on the result so callers work identically to the text=True API.
    result.stdout = result.stdout.decode("utf-8", errors="replace")
    result.stderr = result.stderr.decode("utf-8", errors="replace")
    if check and result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)!r} failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )
    return result


def _branch_exists() -> bool:
    """Return True if the bob-context branch ref exists."""
    result = _git("rev-parse", "--verify", BRANCH, check=False)
    return result.returncode == 0


def _current_tree_sha() -> str:
    """Return the tree SHA currently pointed to by bob-context HEAD."""
    return _git("rev-parse", f"{BRANCH}^{{tree}}").stdout.strip()


def _current_commit_sha() -> str:
    """Return the commit SHA of bob-context HEAD."""
    return _git("rev-parse", BRANCH).stdout.strip()


# ---------------------------------------------------------------------------
# Core plumbing
# ---------------------------------------------------------------------------

def _read_blob(path: str) -> str:
    """Read file content from bob-context:<path>. Returns empty string if absent."""
    result = _git("show", f"{BRANCH}:{path}", check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def _write_blob(path: str, content: str) -> None:
    """
    Write `content` to `path` on the bob-context branch.

    Flow:
      1. hash-object -w  → blob SHA
      2. mktree patches  → tree SHA  (rebuild full tree with new/updated entry)
      3. commit-tree     → commit SHA
      4. update-ref      → move branch pointer
    """
    # 1. Store the blob
    blob_sha = _git("hash-object", "-w", "--stdin", input=content).stdout.strip()

    # 2. Build the new tree
    new_tree_sha = _make_tree_with(path, blob_sha)

    # 3. Create commit
    parent_sha = _current_commit_sha() if _branch_exists() else None
    commit_sha = _commit_tree(new_tree_sha, f"write: {path}", parent_sha)

    # 4. Advance the branch pointer
    _git("update-ref", f"refs/heads/{BRANCH}", commit_sha)


def _make_tree_with(file_path: str, blob_sha: str) -> str:
    """
    Return a new root tree SHA that is identical to the current bob-context tree
    except that `file_path` now points to `blob_sha`.

    Handles nested directories by rebuilding each intermediate tree bottom-up.
    """
    parts = PurePosixPath(file_path).parts  # e.g. ("chat", "alice.md")

    # Collect existing entries for every tree level we'll need to rebuild.
    # We work from the root down, gathering existing ls-tree lines per directory.
    def existing_entries(tree_prefix: str) -> list:
        """Return ls-tree lines for tree_prefix on bob-context, or [] if absent."""
        ref = f"{BRANCH}:{tree_prefix}" if tree_prefix else BRANCH
        if tree_prefix:
            result = _git("ls-tree", f"{BRANCH}:{tree_prefix}", check=False)
        else:
            result = _git("ls-tree", BRANCH, check=False)
        if result.returncode != 0:
            return []
        return [line for line in result.stdout.splitlines() if line.strip()]

    def rebuild(parts_remaining: tuple, current_prefix: str) -> str:
        """
        Recursively rebuild the tree.
        `parts_remaining` is the path components still to descend into.
        `current_prefix` is the directory path from root (empty = root).
        Returns the SHA of the rebuilt tree.
        """
        entries = existing_entries(current_prefix)

        # Parse existing entries into a dict keyed by name
        # Format: "<mode> <type> <sha>\t<name>"
        entry_map = {}
        for line in entries:
            meta, name = line.split("\t", 1)
            mode, obj_type, sha = meta.split()
            entry_map[name] = (mode, obj_type, sha)

        name = parts_remaining[0]

        if len(parts_remaining) == 1:
            # Leaf: insert/replace blob entry
            entry_map[name] = ("100644", "blob", blob_sha)
        else:
            # Intermediate directory: recurse
            sub_prefix = f"{current_prefix}/{name}" if current_prefix else name
            sub_tree_sha = rebuild(parts_remaining[1:], sub_prefix)
            entry_map[name] = ("040000", "tree", sub_tree_sha)

        # Serialise back to mktree input
        mktree_input = "\n".join(
            f"{mode} {obj_type} {sha}\t{entry_name}"
            for entry_name, (mode, obj_type, sha) in entry_map.items()
        )
        if mktree_input:
            mktree_input += "\n"

        return _git("mktree", input=mktree_input).stdout.strip()

    return rebuild(parts, "")


def _commit_tree(tree_sha: str, message: str, parent_sha: str = None) -> str:
    """Create a new commit object and return its SHA."""
    args = ["commit-tree", tree_sha, "-m", message]
    if parent_sha:
        args += ["-p", parent_sha]
    return _git(*args).stdout.strip()


def _list_tree(path: str) -> str:
    """Return raw ls-tree output for `path` on bob-context."""
    if path:
        result = _git("ls-tree", f"{BRANCH}:{path}", check=False)
    else:
        result = _git("ls-tree", BRANCH, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    """Idempotently create the bob-context shadow branch."""
    if _branch_exists():
        print(f"Branch '{BRANCH}' already exists — nothing to do.")
        return

    # Create an empty tree
    empty_tree_sha = _git("mktree", input="").stdout.strip()

    # Create a README blob
    readme_content = "# Bob Logbook — AI Workspace\n"
    readme_sha = _git("hash-object", "-w", "--stdin", input=readme_content).stdout.strip()

    # Build a tree containing the README
    mktree_input = f"100644 blob {readme_sha}\tREADME.md\n"
    tree_sha = _git("mktree", input=mktree_input).stdout.strip()

    # Initial commit (no parent)
    commit_sha = _commit_tree(tree_sha, "init: bob-context shadow branch")

    # Create the branch ref
    _git("update-ref", f"refs/heads/{BRANCH}", commit_sha)
    print(f"Initialised shadow branch '{BRANCH}' (commit {commit_sha[:8]}).")


def cmd_read(args) -> None:
    """Print file content from bob-context to stdout."""
    _check_path(args.path)
    content = _read_blob(args.path)
    if not content and not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(content)


def cmd_write(args) -> None:
    """Create or overwrite a file on bob-context."""
    _check_path(args.path)
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)
    _write_blob(args.path, args.content)


def cmd_append(args) -> None:
    """Append content to a file on bob-context (creates if absent)."""
    _check_path(args.path)
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)
    existing = _read_blob(args.path)
    _write_blob(args.path, existing + args.content)


def cmd_commit(args) -> None:
    """
    Commit all pending shadow-branch changes with the given message.

    Because _write_blob already creates a commit per write, this command
    is a no-op in the typical single-write flow. It is provided for cases
    where a caller has staged changes via lower-level calls and wants an
    explicit named commit, or simply as a semantic marker.
    """
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)
    # Re-commit the current tree with a new message (amend-style without touching history)
    tree_sha = _current_tree_sha()
    parent_sha = _current_commit_sha()
    commit_sha = _commit_tree(tree_sha, args.message, parent_sha)
    _git("update-ref", f"refs/heads/{BRANCH}", commit_sha)
    print(f"Committed tree {tree_sha[:8]} as {commit_sha[:8]}: {args.message}")


def cmd_ls(args) -> None:
    """List files/directories on bob-context at the given path."""
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)
    path = args.path or ""
    output = _list_tree(path)
    if not output:
        prefix = f"'{path}'" if path else "root"
        print(f"(empty or path not found: {prefix})")
        return
    for line in output.splitlines():
        # Format: "<mode> <type> <sha>\t<name>"
        meta, name = line.split("\t", 1)
        mode, obj_type, sha = meta.split()
        marker = "/" if obj_type == "tree" else ""
        print(f"{name}{marker}")


def cmd_export(args) -> None:
    """Copy a file from bob-context into the working tree at dest."""
    _check_path(args.path)
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)
    content = _read_blob(args.path)
    if content == "" :
        # Distinguish "empty file" from "not found"
        result = _git("cat-file", "-e", f"{BRANCH}:{args.path}", check=False)
        if result.returncode != 0:
            print(f"Error: '{args.path}' not found on branch '{BRANCH}'.", file=sys.stderr)
            sys.exit(1)
    dest = Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    print(f"Exported '{args.path}' -> '{dest}'")


def cmd_delete(args) -> None:
    """Delete a file from bob-context."""
    _check_path(args.path)
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)

    # Check the file exists first
    result = _git("cat-file", "-e", f"{BRANCH}:{args.path}", check=False)
    if result.returncode != 0:
        print(f"Error: '{args.path}' not found on branch '{BRANCH}'.", file=sys.stderr)
        sys.exit(1)

    # Rebuild the root tree without the target entry
    parts = PurePosixPath(args.path).parts

    def _remove_from_tree(parts_remaining: tuple, current_prefix: str) -> str:
        """Recursively rebuild the tree with the target entry removed."""
        if current_prefix:
            result = _git("ls-tree", f"{BRANCH}:{current_prefix}", check=False)
        else:
            result = _git("ls-tree", BRANCH, check=False)
        lines = [l for l in result.stdout.splitlines() if l.strip()]

        entry_map = {}
        for line in lines:
            meta, name = line.split("\t", 1)
            mode, obj_type, sha = meta.split()
            entry_map[name] = (mode, obj_type, sha)

        name = parts_remaining[0]
        if len(parts_remaining) == 1:
            # Leaf: remove it
            entry_map.pop(name, None)
        else:
            # Intermediate dir: recurse
            sub_prefix = f"{current_prefix}/{name}" if current_prefix else name
            if entry_map.get(name):
                sub_tree_sha = _remove_from_tree(parts_remaining[1:], sub_prefix)
                if sub_tree_sha:
                    entry_map[name] = ("040000", "tree", sub_tree_sha)
                else:
                    # Empty subtree — remove the directory entry too
                    entry_map.pop(name, None)

        if not entry_map:
            return ""
        mktree_input = "\n".join(
            f"{mode} {obj_type} {sha}\t{entry_name}"
            for entry_name, (mode, obj_type, sha) in entry_map.items()
        ) + "\n"
        return _git("mktree", input=mktree_input).stdout.strip()

    new_tree_sha = _remove_from_tree(parts, "")
    if not new_tree_sha:
        print("Error: resulting tree would be empty.", file=sys.stderr)
        sys.exit(1)

    parent_sha = _current_commit_sha()
    commit_sha = _commit_tree(new_tree_sha, f"delete: {args.path}", parent_sha)
    _git("update-ref", f"refs/heads/{BRANCH}", commit_sha)
    print(f"Deleted '{args.path}' from '{BRANCH}'.")


# ---------------------------------------------------------------------------
# Sub-Task 8 — log and diff commands
# ---------------------------------------------------------------------------

def cmd_log(args) -> None:
    """Print commit history of bob-context, optionally filtered by path and/or --since <sha>."""
    if not _branch_exists():
        print(f"Branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)

    rev_range = f"{args.since}..{BRANCH}" if getattr(args, "since", None) else BRANCH
    log_args = ["log", rev_range, "--format=%h\t%ae\t%ai\t%s"]
    if getattr(args, "path", None):
        _check_path(args.path)
        log_args += ["--", args.path]

    result = _git(*log_args, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        print("(no commits)")
        return
    for line in result.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            sha, author, date, msg = parts
            print(f"{sha}  {date[:19]}  {author}  {msg}")
        else:
            print(line)


def cmd_diff(args) -> None:
    """Print unified diff of the last two commits touching <path> on bob-context."""
    _check_path(args.path)
    if not _branch_exists():
        print(f"Branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)

    result = _git("log", BRANCH, "--format=%H", "-2", "--", args.path, check=False)
    commits = [c for c in result.stdout.splitlines() if c.strip()]
    if len(commits) < 2:
        print(f"No prior version of '{args.path}' to diff against.")
        return

    newer, older = commits[0], commits[1]
    diff = _git("diff", older, newer, "--", args.path, check=False)
    sys.stdout.write(diff.stdout)


# ---------------------------------------------------------------------------
# Export helpers (shared between cmd_export_json and cmd_serve)
# ---------------------------------------------------------------------------

def _file_history(path: str, limit: int = 20) -> list:
    """Return the last `limit` commits touching `path`, each with content at that revision."""
    result = _git(
        "log", BRANCH, f"--format=%H\t%ae\t%ai\t%s", f"-{limit}", "--", path,
        check=False,
    )
    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) == 4:
            sha, author, date, msg = parts
            blob = _git("show", f"{sha}:{path}", check=False).stdout
            commits.append({"sha": sha[:8], "author": author, "date": date, "message": msg, "content": blob})
    return commits


def _build_export_payload() -> dict:
    """Build the full export dict (files + history) used by both cmd_export_json and cmd_serve."""
    import datetime
    if not _branch_exists():
        return {"exported_at": "", "branch": BRANCH, "files": {}, "history": {}}

    result = _git("ls-tree", "-r", "--name-only", BRANCH)
    paths = [p for p in result.stdout.splitlines() if p.strip()]
    files = {path: _read_blob(path) for path in paths}

    # Include per-file commit history so the viewer can show a "History" diff view
    history = {}
    for path in paths:
        commits = _file_history(path)
        if len(commits) >= 2:
            history[path] = commits

    exported_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"exported_at": exported_at, "branch": BRANCH, "files": files, "history": history}


def cmd_export_json(args) -> None:
    """Dump every file on bob-context to a JSON file for the HTML viewer.

    Output format:
        {
          "exported_at": "<ISO8601>",
          "branch": "bob-context",
          "files": { "<path>": "<content>", ... },
          "history": { "<path>": [ { sha, author, date, message, content }, ... ], ... }
        }
    """
    if not _branch_exists():
        print(f"Error: branch '{BRANCH}' does not exist. Run `bob-log init` first.", file=sys.stderr)
        sys.exit(1)

    payload_dict = _build_export_payload()
    payload = json.dumps(payload_dict, ensure_ascii=True, indent=2)

    if args.dest:
        dest = Path(args.dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(payload, encoding="utf-8")
        print(f"Exported {len(payload_dict['files'])} file(s) -> '{dest}'")
    else:
        sys.stdout.buffer.write((payload + "\n").encode("utf-8"))


# ---------------------------------------------------------------------------
# Serve command
# ---------------------------------------------------------------------------

def _export_json_bytes() -> bytes:
    """Return the export-json payload as UTF-8 bytes (for the HTTP server)."""
    payload = json.dumps(_build_export_payload(), ensure_ascii=True, indent=2)
    return payload.encode("utf-8")


def cmd_serve(args) -> None:
    """Start a local HTTP server that serves viewer.html with live SSE updates."""
    port = args.port
    viewer_path = Path(__file__).parent / "viewer.html"

    if not viewer_path.exists():
        print(f"Error: viewer.html not found at {viewer_path}", file=sys.stderr)
        sys.exit(1)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *a):
            pass  # suppress default access log

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._serve_file(viewer_path.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/export":
                data = _export_json_bytes()
                self._serve_bytes(data, "application/json")
            elif self.path == "/api/stream":
                self._serve_sse()
            else:
                self.send_response(404)
                self.end_headers()

        def _serve_file(self, data: bytes, ctype: str):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_bytes(self, data: bytes, ctype: str):
            self._serve_file(data, ctype)

        def _serve_sse(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            last_sha = ""
            ping_counter = 0
            try:
                while True:
                    current_sha = _git("rev-parse", BRANCH, check=False).stdout.strip()
                    if current_sha != last_sha:
                        last_sha = current_sha
                        self.wfile.write(b"data: new-data\n\n")
                        self.wfile.flush()
                    ping_counter += 1
                    if ping_counter >= 15:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        ping_counter = 0
                    time.sleep(1)
            except (BrokenPipeError, ConnectionResetError):
                pass  # client disconnected

    url = f"http://localhost:{port}"
    print(f"Bob Logbook server running at {url}")
    print(f"Open in your browser: {url}")
    print("Press Ctrl+C to stop.\n")

    server = ThreadingHTTPServer(("localhost", port), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bob-log",
        description="Bob Logbook — git shadow-branch AI workspace CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # init
    sub.add_parser("init", help="Idempotently create the bob-context shadow branch")

    # read
    p_read = sub.add_parser("read", help="Print file contents from bob-context")
    p_read.add_argument("path", help="Relative path within bob-context")

    # write
    p_write = sub.add_parser("write", help="Create or overwrite a file on bob-context")
    p_write.add_argument("path", help="Relative path within bob-context")
    p_write.add_argument("content", help="File content to write")

    # append
    p_append = sub.add_parser("append", help="Append content to a file on bob-context")
    p_append.add_argument("path", help="Relative path within bob-context")
    p_append.add_argument("content", help="Content to append")

    # commit
    p_commit = sub.add_parser("commit", help="Create a named commit on bob-context")
    p_commit.add_argument("message", help="Commit message")

    # ls
    p_ls = sub.add_parser("ls", help="List files on bob-context")
    p_ls.add_argument("path", nargs="?", default="", help="Directory path (default: root)")

    # export
    p_export = sub.add_parser("export", help="Copy a file from bob-context to the working tree")
    p_export.add_argument("path", help="Relative path within bob-context")
    p_export.add_argument("dest", help="Destination path in the working tree")

    # export-json
    p_export_json = sub.add_parser(
        "export-json",
        help="Dump all bob-context files to a JSON file for the HTML viewer",
    )
    p_export_json.add_argument(
        "dest",
        nargs="?",
        default="",
        help="Destination .json path (omit to print to stdout)",
    )

    # delete
    p_delete = sub.add_parser("delete", help="Delete a file from bob-context")
    p_delete.add_argument("path", help="Relative path within bob-context")

    # log
    p_log = sub.add_parser("log", help="Show commit history of bob-context")
    p_log.add_argument("path", nargs="?", default=None, help="Filter to commits touching this path")
    p_log.add_argument("--since", metavar="SHA", default=None, help="Show only commits after this SHA")

    # diff
    p_diff = sub.add_parser("diff", help="Show unified diff of last two commits touching a file")
    p_diff.add_argument("path", help="Relative path within bob-context")

    # serve
    p_serve = sub.add_parser(
        "serve",
        help="Start a local HTTP server with live SSE updates (default port 4242)",
    )
    p_serve.add_argument(
        "--port", "-p",
        type=int,
        default=4242,
        help="Port to listen on (default: 4242)",
    )

    return parser


HANDLERS = {
    "init": cmd_init,
    "read": cmd_read,
    "write": cmd_write,
    "append": cmd_append,
    "commit": cmd_commit,
    "ls": cmd_ls,
    "export": cmd_export,
    "export-json": cmd_export_json,
    "delete": cmd_delete,
    "log": cmd_log,
    "diff": cmd_diff,
    "serve": cmd_serve,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        HANDLERS[args.command](args)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
