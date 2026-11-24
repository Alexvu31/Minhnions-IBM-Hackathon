# Bob Logbook — Hackathon MVP Plan

## Overview

**Goal:** Build "Bob Logbook" — a git shadow-branch workspace that lets IBM Bob (and developers) read, write, and commit arbitrary files on a dedicated branch (`bob-context`) that never touches the developer's working tree. Auto-hooks capture chat turns. A companion HTML viewer renders the workspace as a browsable timeline.

**Why this wins:** It treats the shadow branch as shared AI working memory across sessions and teammates. Bob can leave notes, read back prior context, and collaborate across machines — all governed by git. It dogfoods Bob, introduces a novel architectural pattern, and directly addresses a pain point IBM's own developers will recognise.

**Deliverables:**
1. `bob_log.py` — Python 3 CLI (stdlib only): `init`, `read`, `write`, `append`, `commit`, `ls`, `export`
2. `bob-log-hook.py` — thin hook wrapper that reads Bob's JSON stdin and calls `bob_log.py`
3. `.bob/settings.json` — hook config wiring `Stop` and `UserPromptSubmit` to the hook wrapper
4. `viewer.html` — single-file HTML workspace viewer (Alex)
5. `README.md` — setup, command reference, hook install guide
6. PDF submission (4 pages, 11-pt minimum)

**Tech stack:** Python 3 stdlib only, git plumbing (no branch switching), pure HTML/CSS/JS for viewer.

**Division of labour:**
- **jaminleod:** Sub-Tasks 1–3 (shadow branch + CLI + hooks)
- **alexvu31:** Sub-Task 4 (viewer)
- **Both:** Sub-Tasks 5–6 (README + PDF)

**Stretch (after MVP is working):** A Bob skill YAML that teaches Bob the available `bob-log` commands and when to call them autonomously.

---

## Sub-Task 1 — Repo & Shadow Branch Init

**Status:** [x] done

**Intent:** Establish the git repo and create the `bob-context` orphan branch as the AI workspace root.

**Expected Outcomes:**
- Git repo exists at `/home/jaminleod/projects/ibmbob`
- An orphan branch `bob-context` exists with an initial commit containing a `README.md` placeholder
- The working tree is on `main` after setup
- `.gitignore` excludes Python cache and export artifacts

**Todo List:**
1. Confirm `git init` already done (repo is live per Entry-006)
2. Create orphan branch: `git checkout --orphan bob-context && git rm -rf .`
3. Add `README.md` placeholder: `# Bob Logbook — AI Workspace`
4. Commit: `git add README.md && git commit -m "init: bob-context shadow branch"`
5. Return to main: `git checkout main`
6. Add `.gitignore` (Python cache: `__pycache__/`, `*.pyc`; exports: `bob-context-export/`)

**Relevant Context:**
- Orphan branch = zero shared history with `main`, no merge conflicts possible
- See Entry-004 and Entry-006 in `CONTEXT.md`

---

## Sub-Task 2 — `bob_log.py` Core CLI

**Status:** [ ] pending

**Intent:** Write the Python CLI that is the engine for all shadow-branch operations. All commands operate on the `bob-context` branch using git plumbing — the working tree is never switched.

**Expected Outcomes:**
- `bob-log init` — idempotent; creates the shadow branch if absent
- `bob-log read <path>` — prints the file contents from `bob-context` to stdout
- `bob-log write <path> <content>` — creates or overwrites a file on `bob-context`
- `bob-log append <path> <content>` — appends content to a file on `bob-context` (creates if absent)
- `bob-log commit <message>` — commits all pending shadow-branch changes
- `bob-log ls [path]` — lists files/directories on `bob-context` at the given path (default: root)
- `bob-log export <path> <dest>` — copies a file from `bob-context` into the working tree at `dest`
- All writes are path-jailed: paths may not start with `..` or `/` (prevents escaping the shadow branch)
- No external dependencies — Python 3 stdlib only (`subprocess`, `pathlib`, `json`, `os`, `sys`)

**Todo List:**
1. Create `bob_log.py` with an `argparse` CLI and subcommand dispatch
2. Implement `init`: check if `bob-context` ref exists via `git rev-parse`; if not, run the orphan branch setup non-interactively using `git` subprocess calls
3. Implement the git plumbing helpers:
   - `_read_blob(path)` — `git show bob-context:<path>`
   - `_write_blob(path, content)` — `git hash-object -w --stdin`, update the tree, `git commit-tree`, `git update-ref`
   - `_list_tree(path)` — `git ls-tree bob-context:<path>`
4. Implement `read`: call `_read_blob`, print to stdout
5. Implement `write`: call `_write_blob` with full content
6. Implement `append`: read existing content via `_read_blob` (empty string if file absent), concatenate, call `_write_blob`
7. Implement `commit`: resolve current shadow-branch HEAD, `git commit-tree` the current tree with the message, `git update-ref`
8. Implement `ls`: call `_list_tree`, format output
9. Implement `export`: call `_read_blob`, write to dest path in working tree
10. Add path sanitisation to all write operations
11. Add `--help` for each subcommand
12. Create a `bob-log` symlink or wrapper so it can be called without `python3`

**Relevant Context:**
- Git plumbing flow for a write: `hash-object` (content → blob SHA) → `mktree` or manual tree update → `commit-tree` (tree + parent → commit SHA) → `update-ref refs/heads/bob-context <commit SHA>`
- Python `subprocess.run(..., capture_output=True, text=True)` is the right pattern — no shell=True needed
- `git rev-parse --verify bob-context` exits non-zero if the branch doesn't exist — use this for `init` guard
- Path jail: `pathlib.PurePosixPath(path).parts[0] not in ('..', '')` and `not path.startswith('/')`

---

## Sub-Task 3 — Bob Hook Configuration

**Status:** [ ] pending

**Intent:** Wire `bob_log.py` into Bob's lifecycle so chat context is captured automatically on every turn, with zero developer interaction.

**Expected Outcomes:**
- `.bob/settings.json` exists with `Stop` and `UserPromptSubmit` hooks configured
- `Stop` fires after each Bob turn → appends Bob's response to `chat/$USER.md` on the shadow branch
- `UserPromptSubmit` fires before each prompt → appends the user's prompt to `chat/$USER.md`
- Author is derived from `$USER` environment variable — works for both jaminleod and alexvu31 without config
- Hook wrapper reads JSON from stdin using `json.load(sys.stdin)` — no `jq` dependency

**Todo List:**
1. Create `.bob/` directory
2. Write `.bob/settings.json`:
   - `Stop` → `command: "python3 /home/jaminleod/projects/ibmbob/bob-log-hook.py"`
   - `UserPromptSubmit` → same command
3. Write `bob-log-hook.py`:
   - Read JSON from stdin: `payload = json.load(sys.stdin)`
   - Branch on `payload["hook_event_name"]`
   - `Stop`: format entry with timestamp, author (`os.environ["USER"]`), type `bob-response`, message from `payload["last_assistant_message"]`; call `bob_log append chat/$USER.md <entry>`
   - `UserPromptSubmit`: same pattern, type `user-prompt`, message from `payload["prompt"]`; do NOT print to stdout (stdout is injected into model context)
4. Test: run a Bob session and confirm `chat/jaminleod.md` appears on the shadow branch
5. Document hook install in `README.md`

**Relevant Context:**
- `Stop` stdout is IGNORED — safe to write to git, nothing prints
- `UserPromptSubmit` stdout IS injected into the model — the hook wrapper must not print anything
- `session_id` from the payload can be included in each entry as a correlation ID
- See Entry-004 in `CONTEXT.md` for full hook payload schemas

---

## Sub-Task 4 — HTML Viewer (alexvu31)

**Status:** [ ] pending

**Intent:** Build a single-file HTML viewer that renders the `bob-context` shadow branch as a browsable workspace — file tree on the left, content panel on the right.

**Expected Outcomes:**
- `viewer.html` — opens in any browser with no server, no build step, no npm
- Accepts a JSON export of the shadow branch (produced by `bob-log export`) via file picker or drag-and-drop
- Left panel: file tree of the shadow branch
- Right panel: selected file rendered — `chat/*.md` files shown as a timestamped timeline, other `.md` files as plain Markdown
- Author badges are colour-coded: consistent colour per `$USER` value
- Print-friendly CSS for PDF screenshot

**Todo List:**
1. Define the JSON export format with jaminleod — `bob-log export` should produce a JSON object `{ "files": { "<path>": "<content>", ... } }` for the viewer to consume (coordinate on this before Sub-Task 2 step 9)
2. Create `viewer.html` with inline CSS and JS
3. Implement file tree renderer from the JSON keys
4. Implement content panel: detect `chat/` path prefix → timeline renderer; otherwise → Markdown renderer (can use a 50-line JS Markdown parser or just render as `<pre>`)
5. Implement author colour assignment (hash the author string to a hue, or hardcode for `jaminleod` and `alexvu31`)
6. Add print-friendly CSS (`@media print`)
7. Test with a real export from jaminleod's shadow branch

**Relevant Context:**
- Coordinate with jaminleod on the JSON export format before writing the parser (step 1 above is a blocker)
- No external dependencies — judges should be able to open the file and have it work immediately
- The VS Code simple browser panel can open local HTML files — no extension needed

---

## Sub-Task 5 — Tests & README

**Status:** [ ] pending

**Intent:** Verify the CLI works end-to-end in an isolated environment and write the README for judges and future users.

**Expected Outcomes:**
- `test_bob_log.py` — exercises `init`, `write`, `read`, `append`, `ls`, `commit`, `export` in a temp git repo
- All assertions pass with zero external dependencies
- `README.md` covers: what it does, install, hook setup, command reference, viewer usage

**Todo List:**
1. Write `test_bob_log.py` using Python's `unittest` and `tempfile`:
   - `setUp`: create a temp dir, `git init`, set git config `user.name` and `user.email`
   - Test `init`: assert `bob-context` branch ref exists after call
   - Test `write` + `read`: write a file, read it back, assert content matches
   - Test `append`: write then append, read back, assert both parts present
   - Test `ls`: write two files, assert both appear in ls output
   - Test `export`: write a file, export to temp path, assert file exists with correct content
   - `tearDown`: remove temp dir
2. Write `README.md` with sections: Overview, Install, Hook Setup, Command Reference, Viewer Usage, How We Built It With Bob
3. Run `python3 test_bob_log.py` and fix any failures

**Relevant Context:**
- Tests run against the actual `bob_log.py` — import it directly or call via subprocess
- The `git config user.name/email` setup in `setUp` is required for `git commit-tree` to work in a bare temp repo

---

## Sub-Task 6 — PDF Submission

**Status:** [ ] pending

**Intent:** Produce the 4-page PDF that demonstrates meaningful Bob usage and presents the project to judges.

**Expected Outcomes:**
- PDF ≤ 4 pages, font ≥ 11pt
- Page 1: Problem + user story + solution overview
- Page 2: Architecture diagram (hook → `bob_log.py` → shadow branch → viewer) + Bob usage evidence
- Page 3: Code highlights — hook config, `append` plumbing, viewer rendering
- Page 4: Testing + how to run + team reflection

**Todo List:**
1. jaminleod: take screenshots of Bob during the build (plan session, Sub-Task 2 build, hook test)
2. alexvu31: take screenshots of the viewer rendering a real log
3. Run `bob-log export` on the final shadow branch — include a snippet in the PDF as live evidence
4. alexvu31 drafts layout (Canva, Google Slides → PDF, or equivalent)
5. jaminleod reviews for technical accuracy
6. Confirm: font ≥ 11pt, pages ≤ 4
7. Attach PDF to submission email; optionally record a ≤10 min demo video

**Relevant Context:**
- Entry-005 in `CONTEXT.md` lists all Bob usage evidence to include
- Scoring: Innovation 25 · Relevance 25 · Practicality 25 · Quality 25 — PDF must address all four
- The `CONTEXT.md` file itself is evidence of the planning process

---

## Scoring Checklist

| Criterion | How we address it |
|---|---|
| Innovation & Creativity | Shadow branch as AI working memory is a novel pattern; tool dogfoods Bob |
| Relevance to Challenge | Extends IBM Bob directly; complete workflow from hook install to viewer |
| Practicality & Feasibility | Python stdlib only, no accounts, no APIs, runs anywhere Python 3 + git exist |
| Overall Quality & Presentation | Viewer, tests, README, structured PDF — all four deliverables present |

---

## Stretch Goals (only if time permits after Sub-Task 5)

- **Bob skill:** A `SKILL.md` that teaches Bob the available `bob-log` commands and instructs it to use them proactively during sessions
- **`bob-log diff <path>`:** Show git diff of a file between the last two commits on the shadow branch
- **Remote sync:** `bob-log push` / `bob-log pull` to sync the shadow branch with a remote — enables true cross-machine AI collaboration
