# Bob Logbook

> Automatically capture IBM Bob session context into a git shadow branch — and browse it as a clean timeline in your browser.

---

## What it does

Every time you work with IBM Bob, valuable context accumulates: decisions made, prompts that worked, constraints discovered. That context normally lives only in the chat window and disappears when the session ends.

**Bob Logbook** solves this with two Bob lifecycle hooks that fire on every turn:

| Hook | What it captures |
|---|---|
| `UserPromptSubmit` | Your prompt, before it is sent to Bob |
| `Stop` | Bob's final response, after each turn |

Each captured event is appended as a timestamped Markdown entry to `chat/$USER.md` on a dedicated **shadow branch** (`bob-context`). The shadow branch shares no history with `main`, so there are never merge conflicts. Run `bob-log export-json` any time to produce a JSON snapshot, then open `viewer.html` in a browser to browse the full workspace as a colour-coded timeline.

---

## Why it exists

- **Zero manual effort** — install once, capture forever.
- **Dogfoods Bob** — the tool was built entirely using Bob; this README was written by Bob.
- **Team-friendly** — teammates can open the viewer and pick up exactly where someone left off, without reading the full chat history.
- **No external dependencies** — Python 3 stdlib only (`subprocess`, `pathlib`, `json`, `os`, `sys`). No pip installs, no accounts, no APIs.

---

## Install

### 1. Clone or copy the files

```sh
git clone <repo> ~/projects/ibmbob
cd ~/projects/ibmbob
```

The only files you need are:
```
bob_log.py          # Core CLI
bob-log-hook.py     # Bob hook wrapper
viewer.html         # Browser viewer
```

### 2. Initialise the shadow branch

```sh
python3 bob_log.py init
```

This creates the `bob-context` orphan branch with an initial `README.md` placeholder.
Running `init` again is safe — it is idempotent.

### 3. Configure the Bob hooks

Create (or extend) `.bob/settings.json` in your project root:

```json
{
  "hooks": [
    {
      "event": "Stop",
      "type": "command",
      "command": "python3 /path/to/ibmbob/bob-log-hook.py"
    },
    {
      "event": "UserPromptSubmit",
      "type": "command",
      "command": "python3 /path/to/ibmbob/bob-log-hook.py"
    }
  ]
}
```

Replace `/path/to/ibmbob/` with the absolute path to this repo.
Bob will now automatically call `bob-log-hook.py` on every turn.

---

## `bob-log` command reference

```
python3 bob_log.py <subcommand> [args]
```

| Subcommand | Syntax | Description |
|---|---|---|
| `init` | `bob_log.py init` | Idempotently creates the `bob-context` shadow branch |
| `read` | `bob_log.py read <path>` | Prints file contents from `bob-context` to stdout |
| `write` | `bob_log.py write <path> <content>` | Creates or overwrites a file on `bob-context` |
| `append` | `bob_log.py append <path> <content>` | Appends content to a file on `bob-context` (creates if absent) |
| `commit` | `bob_log.py commit <message>` | Creates a named commit on `bob-context` |
| `ls` | `bob_log.py ls [path]` | Lists files/directories on `bob-context` at the given path |
| `export` | `bob_log.py export <path> <dest>` | Copies a single file from `bob-context` to the working tree |
| `export-json` | `bob_log.py export-json [dest.json]` | Dumps all files to a JSON snapshot for the viewer |
| `log` | `bob_log.py log [--since <sha>] [path]` | Shows commit history; optionally filtered by SHA range or path |
| `diff` | `bob_log.py diff <path>` | Shows unified diff between the last two commits touching a file |
| `serve` | `bob_log.py serve [--port N]` | Starts a local HTTP server at `localhost:4242` with live SSE updates |

All paths are relative to the shadow-branch root. Absolute paths and `..` traversals are rejected.

**Examples:**

```sh
# See what's on the shadow branch
python3 bob_log.py ls

# Read back your session log
python3 bob_log.py read chat/jaminleod.md

# Write a decision note
python3 bob_log.py write decisions.md "# Decisions\n\n## 2026-11-24 — Use Python\nChosen Python 3 stdlib over shell.\n"

# Export everything to a JSON file for the viewer
python3 bob_log.py export-json bob-context-export.json
```

---

## Viewer usage

### Live mode (recommended)

```sh
python3 bob_log.py serve
# Open http://localhost:4242 in your browser
```

The viewer auto-loads and updates in real time via SSE — no manual export needed.

### Static mode

1. Export a snapshot: `python3 bob_log.py export-json bob-context-export.json`
2. Open `viewer.html` in any browser and click **Load export** (bottom-right), or drag-and-drop the JSON file.

### What you see

- **Brand bar** — `Bob Logbook` title + tab bar + file/message counts + export timestamp
- **Left sidebar** — file tree; hover to expand, click to open a tab; active file highlighted
- **Tab bar** — `💬 All Chats (N)` always first; per-author chat tabs; file tabs; history tabs
- **Chat view** — ChatGPT-style bubbles (user right/blue, Bob left/grey); filter by author or session, or open filtered view as a new tab
- **File view** — Markdown-rendered file; `🕐 History (N)` button opens a diff timeline if the file has multiple revisions
- **History / diff view** — each commit shown as a card with green/red line-level diff against the prior version

---

## Running the tests

```sh
python3 test_bob_log.py
```

The test suite uses Python's `unittest` and `tempfile`:
- Creates a fresh `git init` temp directory per test case
- Exercises `init`, `write`, `read`, `append`, `ls`, `export`, path-jail, and idempotency
- Asserts working-tree isolation — shadow-branch writes never appear in the working tree
- Zero external dependencies — runs anywhere Python 3 + git exist

---

## How the git plumbing works

All shadow-branch operations use git plumbing commands so the working tree is **never switched**:

```
content → git hash-object -w --stdin → blob SHA
blob SHA + current tree → git mktree → new tree SHA
new tree SHA + parent commit → git commit-tree → commit SHA
commit SHA → git update-ref refs/heads/bob-context → branch pointer advances
```

The `-c core.autocrlf=false` flag is passed to every git call to ensure consistent binary behaviour on Windows.

---

## How entries look

Each hook invocation appends a block like this to `chat/$USER.md`:

```markdown
## Entry-035 - bob-response
**Timestamp:** 2026-11-24T17:00:00Z
**Author:** jaminleod
**Type:** bob-response
**Session:** abc123def456

Bob's response text goes here.

---
```

The viewer parses the `## Entry-NNN` blocks and renders them as chat bubbles.

---

## Repo structure

```
.
├── bob_log.py              # Core CLI — all shadow-branch operations
├── bob-log-hook.py         # Bob hook wrapper — reads JSON stdin, calls bob_log.py
├── bob-log                 # Convenience symlink (unix) → bob_log.py
├── viewer.html             # Single-file browser workspace viewer
├── test_bob_log.py         # Python unittest integration suite
├── bob-context-export.json # Sample export (for viewer demo)
├── .bob/
│   └── settings.json       # Bob hook configuration
├── CONTEXT.md              # Append-only decision log (main branch)
└── README.md               # This file
```

---

## Team

- **jaminleod** — Python CLI (`bob_log.py`), hook wrapper, git shadow-branch plumbing, planning session with Bob
- **alexvu31** — HTML viewer (`viewer.html`), Python test suite (`test_bob_log.py`), README, PDF layout

Built in 4 hours for the CIPS × IBM Virtual Hackathon (2026). The planning session, the CLI, the viewer, the tests, and this README were all written using IBM Bob.
