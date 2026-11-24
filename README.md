# Bob Logbook

> Shared AI working memory for teams — automatically capture every IBM Bob session into a git shadow branch that any teammate can read, browse, and build on, in real time or asynchronously.

---

## What it does

When a team uses IBM Bob, context fractures: each developer has their own chat history, decisions get made in one session and forgotten in the next, and teammates have no way to see what Bob helped someone else figure out an hour ago.

**Bob Logbook** fixes this. Two Bob lifecycle hooks fire silently on every turn — no developer action required:

| Hook | What it captures |
|---|---|
| `UserPromptSubmit` | The developer's prompt, before it is sent to Bob |
| `Stop` | Bob's final response, after each turn |

Each event is appended as a timestamped Markdown entry to `chat/$USER.md` on a dedicated **shadow branch** (`bob-context`). Every developer on the team writes to their own file; the shadow branch accumulates a shared, append-only record of every AI-assisted decision the team has made.

The shadow branch is an **orphan branch** — it shares no history with `main` and can never cause a merge conflict. It is a git branch, so the full history is preserved, diffs are always available, and rollback is a single `git update-ref`.

Run `bob-log serve` to get a live browser dashboard. Any teammate — on any machine that has cloned the repo — can open it and see the entire team's session history, filtered by author, session, or time.

---

## Built for team collaboration

Bob Logbook is designed from the ground up for teams working together with AI, both in real time and across sessions:

**Asynchronous handoff**
- Developer A works with Bob at 9 AM and closes the session. Everything Bob said — decisions, code, rationale — is on the shadow branch.
- Developer B opens `bob-log serve` at 2 PM. They see Developer A's full session, can read the decisions file, and can pick up exactly where Developer A left off — without reading a chat transcript.

**Synchronous collaboration**
- Both developers run `bob-log serve` at the same time.
- As either developer works with Bob, new entries appear in the other's browser within one second via Server-Sent Events (SSE).
- The viewer's **All Chats** tab merges all authors' sessions into a single chronological timeline.

**Per-author attribution**
- Each developer writes to their own `chat/<username>.md` file, derived from `$USER` automatically.
- The viewer colour-codes authors and lets you filter to any author or session.

---

## This is not a chat UI

Bob Logbook looks like a chat interface but is architecturally different from any chat product:

| | Chat UI (ChatGPT, Claude, etc.) | Bob Logbook |
|---|---|---|
| **Where data lives** | Vendor's servers, per-account | Your git repo — owned by your team |
| **Who can read it** | Only the person who had the conversation | Anyone with repo access |
| **Multiple authors** | Separate accounts, no shared view | One shadow branch, all authors interleaved |
| **Writable by tools** | No | Yes — Bob, scripts, or CI can `bob-log write` |
| **History / diffs** | Not available | Every file has a full commit history with line-level diffs |
| **Survives session end** | Only if manually exported | Automatically, on every turn |
| **Works offline** | No | Yes — git is local |

The viewer is the read surface. The real product is the **shadow branch**: a git-native shared workspace where every AI-assisted decision is a commit, every file is diffable, and no context is ever lost.

---

## Why it exists

- **Zero manual effort** — install once, capture forever. Developers don't change how they work.
- **Dogfoods Bob** — the tool was built entirely using Bob. The shadow branch captured its own construction in real time.
- **No external dependencies** — Python 3 stdlib only. No pip installs, no accounts, no external APIs. Works anywhere Python 3 and git exist.
- **Git as the safety net** — no force-pushes, no branch deletion. Every write is a commit. The full history is always there.

---

## Install & team setup

### 1. Clone the repo

```sh
git clone https://github.com/alexvu31/minhnions-ibm-hackathon
cd minhnions-ibm-hackathon
```

### 2. Initialise the shadow branch

```sh
python3 bob_log.py init
```

This creates the `bob-context` orphan branch locally.
Running `init` again is safe — it is idempotent.

### 3. Push the shadow branch to GitHub

The shadow branch needs to be on GitHub so teammates can fetch it:

```sh
git push origin bob-context
```

> **First person to set up** does steps 1–3. Everyone else just clones and skips to step 4 — the shadow branch is already on GitHub.

### 4. Configure the Bob hooks

Create (or extend) `.bob/settings.json` in your project root:

```json
{
  "hooks": [
    {
      "event": "Stop",
      "type": "command",
      "command": "python3 /absolute/path/to/bob-log-hook.py"
    },
    {
      "event": "UserPromptSubmit",
      "type": "command",
      "command": "python3 /absolute/path/to/bob-log-hook.py"
    }
  ]
}
```

Replace `/absolute/path/to/` with the path to your clone. On the hackathon environment this is `/home/$USER/projects/ibmbob/`.

Bob will now capture every turn automatically.

### 5. That's it — the hook handles everything else

Once the hooks are configured, Bob Logbook runs itself:

- **Every prompt and response** is captured to `chat/$USER.md` on `bob-context`
- **After each turn**, the shadow branch is pushed to GitHub automatically — no manual `git push`
- **Your teammate** can run `bob-log serve` at any time to see your sessions, live or async

```sh
# See your own session live
python3 bob_log.py serve
# Open http://localhost:4242

# Your teammate (on their machine, after cloning)
git fetch origin bob-context:bob-context
python3 bob_log.py serve
# Their All Chats tab now includes your session, updated after every Bob turn
```

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
