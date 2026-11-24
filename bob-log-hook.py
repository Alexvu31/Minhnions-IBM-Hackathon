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


def format_entry(event: str, author: str, session_id: str, message: str) -> str:
    """Format a single log entry in a consistent Markdown block."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    divider = "---"
    return (
        f"\n{divider}\n"
        f"**{event}** | {ts} | author: `{author}` | session: `{session_id}`\n\n"
        f"{message}\n"
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
        entry = format_entry("bob-response", author, session_id, message)
        bob_log("append", chat_path, entry)

    elif event == "UserPromptSubmit":
        message = payload.get("prompt") or ""
        if not message:
            sys.exit(0)
        entry = format_entry("user-prompt", author, session_id, message)
        # NOTE: stdout must stay empty — it would be injected into the model.
        bob_log("append", chat_path, entry)

    # Any other event: silently ignore.
    sys.exit(0)


if __name__ == "__main__":
    main()
