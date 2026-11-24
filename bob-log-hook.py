#!/usr/bin/env python3
"""bob-log-hook.py — Bob lifecycle hook wrapper for Bob Logbook.

Reads the Bob hook JSON payload from stdin and appends a log entry to
chat/$USER.md on the bob-context shadow branch.

Supported events:
  Stop              — appends Bob's last assistant message
  UserPromptSubmit  — appends the user's prompt

IMPORTANT: UserPromptSubmit stdout IS injected into the model context.
This script never writes to stdout so the model is not polluted.
All diagnostic output goes to stderr only.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BOB_LOG = os.path.join(SCRIPT_DIR, "bob_log.py")


def bob_log(*args: str) -> int:
    """Call bob_log.py with the given arguments. Returns exit code."""
    result = subprocess.run(
        [sys.executable, BOB_LOG] + list(args),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[bob-log-hook] bob_log error: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode


def _push_shadow_branch() -> None:
    """Push bob-context to origin in the background — fire and forget.

    Runs detached so it never blocks Bob. Silently skipped if there is no
    remote or no network — the local branch is always the source of truth.
    """
    # Check a remote named 'origin' exists before attempting push
    has_remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
    ).returncode == 0
    if not has_remote:
        return
    # Detach the push completely — stdout/stderr discarded, no wait
    subprocess.Popen(
        ["git", "push", "origin", "bob-context"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def _bob_log_read(path: str) -> str:
    """Read a file from the shadow branch and return its content, or '' if absent."""
    result = subprocess.run(
        [sys.executable, BOB_LOG, "read", path],
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else ""


def _count_entries(content: str) -> int:
    """Count existing ## Entry- headings in a file's content."""
    return sum(1 for line in content.splitlines() if line.startswith("## Entry-"))


def format_entry(event: str, author: str, session_id: str, message: str, entry_num: int) -> str:
    """Format a single log entry in ## Entry-NNN format expected by the viewer parser."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    num = str(entry_num).zfill(3)
    return (
        f"\n## Entry-{num} - {event}\n"
        f"**Timestamp:** {ts}\n"
        f"**Author:** {author}\n"
        f"**Type:** {event}\n"
        f"**Session:** {session_id}\n"
        f"\n{message}\n"
        f"\n---\n"
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"[bob-log-hook] Failed to parse stdin JSON: {exc}", file=sys.stderr)
        sys.exit(0)  # fail open — never block Bob

    event = payload.get("hook_event_name", "")
    session_id = payload.get("session_id", "unknown")
    author = os.environ.get("USER", "unknown")
    chat_path = f"chat/{author}.md"

    if event == "Stop":
        message = payload.get("last_assistant_message") or ""
        if not message:
            sys.exit(0)
        existing = _bob_log_read(chat_path)
        entry_num = _count_entries(existing) + 1
        entry = format_entry("bob-response", author, session_id, message, entry_num)
        bob_log("append", chat_path, entry)
        _push_shadow_branch()

    elif event == "UserPromptSubmit":
        message = payload.get("prompt") or ""
        if not message:
            sys.exit(0)
        existing = _bob_log_read(chat_path)
        entry_num = _count_entries(existing) + 1
        entry = format_entry("user-prompt", author, session_id, message, entry_num)
        # NOTE: stdout must stay empty — it would be injected into the model.
        bob_log("append", chat_path, entry)
        _push_shadow_branch()

    # Any other event: silently ignore.
    sys.exit(0)


if __name__ == "__main__":
    main()
