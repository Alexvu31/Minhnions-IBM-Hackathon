# Bob Logbook — Hackathon MVP Plan

## Overview

**Goal:** Build "Bob Logbook" — a git shadow-branch workspace that lets IBM Bob (and developers) read, write, and commit arbitrary files on a dedicated branch (`bob-context`) that never touches the developer's working tree. Auto-hooks capture chat turns. A companion HTML viewer renders the workspace as a browsable timeline. A coordination layer lets multiple Bob agents see each other's work in near-real-time via the shared shadow branch.

**Why this wins:** It treats the shadow branch as shared AI working memory across sessions and teammates. Bob can leave notes, read back prior context, and collaborate across machines — all governed by git. Multiple agents working simultaneously each see what the other is doing through the branch. It dogfoods Bob, introduces a novel architectural pattern, and directly addresses a pain point IBM's own developers will recognise.

**Deliverables:**
1. `bob_log.py` — Python 3 CLI (stdlib only): `init`, `read`, `write`, `append`, `commit`, `ls`, `export`, `export-json`, `log`, `diff`, `serve`
2. `bob-log-hook.py` — hook wrapper wiring `Stop`, `UserPromptSubmit`, and `SessionStart` to the shadow branch
3. `.bob/settings.json` — hook config
4. `viewer.html` — single-file HTML workspace viewer: IBM Carbon blue, ChatGPT-style chat bubbles, tabbed layout, filter panel, SSE live updates via `bob-log serve`
5. `.bob/skills/bob-log/SKILL.md` — Bob skill teaching agents to use `bob-log` commands proactively
6. `README.md` — setup, command reference, hook install guide
7. PDF submission (4 pages, 11-pt minimum)

**Tech stack:** Python 3 stdlib only, git plumbing (no branch switching), pure HTML/CSS/JS for viewer, SSE for live updates.

**Division of labour:**
- **jaminleod:** Sub-Tasks 1–3, 7–9 (shadow branch + CLI + hooks + coordination layer + skill)
- **alexvu31:** Sub-Task 4 (viewer fixes)
- **Both:** Sub-Tasks 5–6, 7b–7c (viewer redesign + serve + PDF)

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

**Status:** [x] done

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

**Status:** [x] done

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

**Status:** [x] done

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

**Status:** [x] done

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

**Status:** [x] done

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

---

## Sub-Task 7 — Viewer Fixes

**Status:** [x] done

**Intent:** Fix the three issues identified in Alex's viewer: (1) the entry format the hook writes does not match what the viewer parser expects, causing cards to render as raw plaintext; (2) card bodies render as escaped text instead of Markdown; (3) there is no combined view across all contributors.

**Expected Outcomes:**
- Hook and viewer agree on a single entry format — `## Entry-NNN` heading with `**Timestamp:**`, `**Author:**`, `**Type:**`, `**Session:**` metadata keys
- `bob-log-hook.py` updated to write entries in the `## Entry-NNN` format with a global counter per file
- Card bodies in the viewer render as full Markdown (headers, bullets, code fences, bold/italic) using the existing `renderMarkdown()` function
- A virtual "💬 All Contributors" entry appears at the top of the sidebar chat group, synthesised in the viewer from all `chat/` files sorted by timestamp — no data duplication, no hook change required
- The demo data in `viewer.html` updated to match the new format so `?demo` still works

**Todo List:**
1. Update `bob-log-hook.py` `format_entry()` to write `## Entry-NNN` format:
   - Track a per-file entry counter by reading the existing file and counting existing `## Entry-` headings
   - Write: `## Entry-NNN - <event-type>\n**Timestamp:** <iso>\n**Author:** <author>\n**Type:** <type>\n**Session:** <session>\n\n<message>\n\n---\n`
2. In `viewer.html` `renderTimeline()`, replace `escH(e.body)` with `renderMarkdown(e.body)` and remove `white-space: pre-wrap` from `.card-body`, replacing it with `.card-body .md-view` styling
3. Add an "All Contributors" virtual view: after `buildTree()`, insert a `💬 All Contributors` sidebar item at the top of the chat group; when selected, merge all `chat/` file entries, sort by `entry.timestamp`, and render as a single unified timeline
4. Update the demo data object in `viewer.html` to use the `## Entry-NNN` format so `?demo` renders correctly
5. Smoke-test: open `viewer.html?demo` and verify cards show rendered Markdown, the All Contributors view shows all entries interleaved by timestamp, and per-author views are unchanged

**Relevant Context:**
- `parseTimeline()` in `viewer.html` already expects the `## Entry-NNN` format — only the hook needs updating on the Python side
- The `renderMarkdown()` function is already defined in `viewer.html` and handles all required syntax
- The All Contributors view is purely a JS merge at load time — no changes to `bob_log.py` or `export-json` needed
- Entry counter: `len([l for l in existing_content.splitlines() if l.startswith("## Entry-")])` gives the current count

---

## Sub-Task 8 — Coordination CLI Commands

**Status:** [ ] pending

**Intent:** Add `bob-log log` and `bob-log diff` to `bob_log.py` so agents have primitives to discover what changed on the shadow branch and by whom. These are the building blocks for agent-to-agent async coordination.

**Expected Outcomes:**
- `bob-log log [--since <sha>] [path]` — prints the commit history of `bob-context`, optionally filtered to commits after a given SHA and/or touching a given path; each line shows short SHA, author, timestamp, message
- `bob-log diff <path>` — prints the unified diff of `path` between its last two commits on `bob-context`; prints a "no prior version" message if fewer than two commits touch the file
- Both commands exit cleanly with a friendly message if the branch does not exist

**Todo List:**
1. Implement `cmd_log`:
   - Run `git log bob-context --oneline --format="%h %ae %ai %s"` with optional `-- <path>` filter
   - Accept `--since <sha>` flag: pass `<sha>..bob-context` as the range if provided
   - Print each line to stdout formatted as `<sha>  <date>  <author>  <message>`
2. Implement `cmd_diff`:
   - Find the last two commits touching `path`: `git log bob-context --format="%H" -2 -- <path>`
   - If fewer than two, print "No prior version of '<path>' to diff against." and exit 0
   - Run `git diff <older> <newer> -- <path>` and print to stdout
3. Wire both into `build_parser()` and `HANDLERS`
4. Add path sanitisation to `diff` (reuses `_check_path`)
5. Test manually: write a file twice, run `bob-log diff`, confirm the diff shows the change; run `bob-log log`, confirm the commit list appears

**Relevant Context:**
- `git log --format="%H" -2 -- <path>` returns the two most recent commits that touched `path` — first line is newest
- `git diff <sha1> <sha2> -- <path>` produces a standard unified diff
- `--since <sha>` is implemented as a git revision range: `<sha>..bob-context` — not a date filter

---

## Sub-Task 9 — SessionStart Hook + Bob Skill

**Status:** [ ] pending

**Intent:** Wire a `SessionStart` hook that injects a compact summary of recent shadow-branch changes into the model context at the start of every session. Write a Bob skill that teaches agents to use `bob-log` commands proactively — completing the agent coordination loop.

**Expected Outcomes:**
- `SessionStart` hook added to `.bob/settings.json` and handled in `bob-log-hook.py`
- At session start, the hook fetches the remote shadow branch first so it always reads the true latest state across all contributors, then runs `bob-log log --since <last-seen-sha>` to find new commits, formats a compact summary, and returns it as `additionalContext` via structured JSON output on stdout
- After producing the summary, the hook pushes the updated `state/$USER.json` cursor back to the remote so other agents can see when this author's session started
- The last-seen SHA is persisted in a small state file on the shadow branch (`state/$USER.json`) so each author tracks their own cursor independently
- If no remote is configured, fetch and push steps are silently skipped — the hook still works in a local-only setup
- If no new commits exist since last session, the hook outputs nothing (clean context window)
- `bob-log log` itself accepts an optional `--fetch` flag that runs `git fetch` before reading the log, for callers who want on-demand fresh data during a session
- `.bob/skills/bob-log/SKILL.md` exists and teaches Bob: what commands are available, when to call them proactively (before architectural decisions, when asked about prior work, when another agent's changes are relevant), and the coordination conventions (reading `state/`, writing notes to `notes/`)

**Todo List:**
1. Add `bob-log push` and `bob-log pull` commands to `bob_log.py`:
   - `pull`: `git fetch origin bob-context:bob-context` — fast-forward the local ref from remote; skip silently if no remote
   - `push`: `git push origin bob-context` — push local ref to remote; skip silently if no remote
   - Both detect "no remote" via `git remote` exit code and print a friendly message rather than erroring
2. Add `--fetch` flag to `cmd_log`: if present, run `bob-log pull` before reading the log
3. Add `SessionStart` handler to `bob-log-hook.py`:
   - Run `bob-log pull` first (fetches latest from remote; no-op if no remote)
   - Read `state/$USER.json` from the shadow branch to get `last_seen_sha` (empty string if absent — first session)
   - Run `bob-log log --since <last_seen_sha>` to get new commits
   - If no new commits: update state cursor, push, exit 0 with no stdout
   - If new commits exist: format a compact Markdown summary listing each commit (sha, author, timestamp, message)
   - Write current HEAD sha to `state/$USER.json` on the shadow branch
   - Run `bob-log push` (syncs state cursor back to remote; no-op if no remote)
   - Print structured JSON to stdout: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "<summary>"}}`
4. Add `SessionStart` to `.bob/settings.json` hooks
5. Create `.bob/skills/bob-log/SKILL.md`:
   - Frontmatter: `name: bob-log`, `description: ...`
   - Sections: Available Commands, When to Use Them Proactively, Coordination Conventions, Entry Format
   - Key instructions: check `bob-log log --fetch` before making decisions that might conflict with another agent's recent work; write structured notes to `notes/<topic>.md` when making non-trivial decisions; read `chat/<author>.md` when asked about another contributor's context
6. Test `SessionStart`: start a new Bob session, confirm the summary appears in the first turn context (or nothing appears if no new commits)
7. Update README with coordination workflow section

**Relevant Context:**
- `SessionStart` stdout IS injected into the model as context — the structured `additionalContext` JSON is the right pattern (see hook skill)
- Fetch/push must be fire-and-forget when no remote exists: `git remote` returns non-zero if no remotes are configured — check this before running fetch/push
- State file format: `{"last_seen_sha": "<sha>", "updated_at": "<iso>"}` — stored at `state/$USER.json` on `bob-context`
- The skill file location must be `.bob/skills/bob-log/SKILL.md` for Bob to discover it
- `bob-log log --since ""` (empty string) should return all commits — handle the empty-string case as "no filter"
- `git fetch origin bob-context:bob-context` fast-forwards the local ref without switching branches — consistent with the no-checkout plumbing pattern used throughout

---

## Sub-Task 7b — Viewer Chat UI Redesign

**Status:** [x] done

**Intent:** Replace the stacked card layout with a proper chat interface styled with IBM Carbon Design. The viewer should feel like a real AI chat product, not a file printer.

**Expected Outcomes:**
- IBM Carbon palette throughout: `#0F62FE` (Blue 60) for user bubbles and primary actions, `#001141` dark navy for the header, `#F4F4F4` for AI response bubbles, white for the main background
- User (`user-prompt`) messages: right-aligned, `#0F62FE` background, white text, rounded bubble (border-radius 18px 18px 4px 18px)
- AI (`bob-response`) messages: left-aligned, `#F4F4F4` background, dark text, avatar icon on left, rounded bubble (border-radius 18px 18px 18px 4px)
- No card borders — clean and minimal, messages separated by whitespace only
- Tabbed layout: a persistent tab bar at the top of the main area; first tab is always "💬 All Chats", additional tabs are auto-generated per author from loaded data, plus any file tabs opened from the sidebar
- Each chat tab has a filter button (funnel icon) that opens a dropdown with checkboxes for author and session ID — filtering is dynamic, applied without reloading
- Multiple instances of the same tab type are allowed (e.g. two "All Chats" tabs with different filters)
- File tree in sidebar becomes a narrow icon-only panel; hovering expands it; clicking a file opens it as a new closeable tab
- Tabs are closeable (× button) except the first "All Chats" tab
- Timestamps shown as relative ("2 hours ago") with absolute ISO on hover

**Todo List:**
1. Restructure `viewer.html` layout: remove the existing two-panel layout, introduce a tab bar above the main content area and a collapsed icon sidebar on the left
2. Replace `.card` / `.card-header` / `.card-body` CSS with chat bubble CSS: `.msg-row` (flex row), `.bubble` (the message itself), `.bubble.user` (right-aligned IBM blue), `.bubble.ai` (left-aligned grey), `.bubble .md-view` for body content
3. Implement tab bar: `createTab(id, label, closeable)`, `selectTab(id)`, `closeTab(id)` — tabs stored in a JS `Map`; active tab highlighted with IBM blue underline
4. Implement filter panel: clicking the funnel icon on a chat tab opens a `<details>`-based dropdown listing all authors and session IDs found in the current tab's data; unchecking hides those messages without re-parsing
5. Implement collapsed sidebar: file tree icons only by default; CSS `width` transition on hover to reveal labels; clicking a file calls `openFileTab(path)`
6. Add relative timestamp formatting (`formatRelative(iso)`) with `title` attribute for absolute ISO on hover
7. Preserve All Contributors merge logic and per-author tab generation from Sub-Task 7
8. Update `@media print` to hide the tab bar and sidebar, print only the active tab content

**Relevant Context:**
- IBM Carbon Design tokens: Blue 60 `#0F62FE`, Blue 80 `#002D9C` (hover), Gray 10 `#F4F4F4`, Gray 100 `#161616`, Cool Gray 10 `#F2F4F8`, White `#FFFFFF`
- The existing `renderMarkdown()`, `parseTimeline()`, `authorColour()`, `renderAllContributors()` functions are reusable — do not rewrite them
- The bubble shape mirrors ChatGPT: user messages align right with the rounded corner on the bottom-right cut flat; AI messages align left with the bottom-left corner cut flat
- Filter state lives in a per-tab JS object `{ authors: Set, sessions: Set }` — the render function reads this before emitting message rows

---

## Sub-Task 7c — `bob-log serve` Live Server

**Status:** [x] done

**Intent:** Add a `bob-log serve` subcommand that starts a local HTTP server so the viewer updates in real time as new commits land on the shadow branch — no manual re-export and file reload required.

**Expected Outcomes:**
- `bob-log serve [--port N]` starts a Python `http.server`-based server on `localhost:N` (default 4242)
- `GET /` — serves `viewer.html` from the same directory as `bob_log.py`
- `GET /api/export` — returns the live `export-json` payload (JSON, `Content-Type: application/json`)
- `GET /api/stream` — SSE endpoint; polls `bob-context` HEAD SHA every second, pushes `data: new-data\n\n` when it changes; keeps connection alive with `: ping\n\n` comments every 15 s
- `viewer.html` detects if loaded via HTTP (checks `location.protocol === 'http:'`): if so, connects `new EventSource('/api/stream')` and re-fetches `/api/export` on `new-data` event, merging new data without losing the active tab or filter state
- If loaded as a local file (`file:` protocol), falls back to the existing JSON file picker — no behaviour change for the static use case
- Server prints the URL on start: `Bob Logbook server running at http://localhost:4242 — open in your browser`
- Ctrl+C shuts down cleanly

**Todo List:**
1. Add `cmd_serve` to `bob_log.py`:
   - Subclass `http.server.BaseHTTPRequestHandler` with `do_GET`
   - Route `/` → read and serve `viewer.html` bytes, `Content-Type: text/html`
   - Route `/api/export` → call `export-json` logic inline (reuse `cmd_export_json` internals), return JSON bytes
   - Route `/api/stream` → set headers `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`; enter a loop reading HEAD SHA every second, writing `data: new-data\n\n` on change and `: ping\n\n` every 15 s; exit loop on `BrokenPipeError`
   - Start `http.server.HTTPServer(('localhost', port), Handler)` and call `serve_forever()`
   - Catch `KeyboardInterrupt`, print shutdown message, exit 0
2. Wire into `build_parser()` and `HANDLERS` with `--port` optional arg (default 4242)
3. In `viewer.html`, add startup detection block: if `location.protocol` is `http:` or `https:`, skip the file picker on first load and immediately fetch `/api/export`; connect `EventSource('/api/stream')` and on `message` event re-fetch `/api/export` and call `loadExport()` with the result, preserving active tab
4. Add `openUrl` call in `cmd_serve` after server starts: `webbrowser.open(f'http://localhost:{port}')` — stdlib `webbrowser` module, no dependency
5. Test: run `bob-log serve`, open browser, write a file via `bob-log write`, confirm the viewer updates within 2 seconds

**Relevant Context:**
- SSE response format: `Content-Type: text/event-stream`; each event is `data: <payload>\n\n`; keep-alive comments are `: <anything>\n\n`
- `BrokenPipeError` is the correct exception to catch when the browser closes the SSE connection
- `http.server.HTTPServer` is single-threaded; SSE loop blocks the thread — use `ThreadingHTTPServer` from `http.server` to handle the export endpoint concurrently while SSE is streaming
- HEAD SHA polling: `_git("rev-parse", BRANCH, check=False).stdout.strip()` — returns empty string if branch absent
- `webbrowser.open()` is a stdlib call; wrap in `try/except` so a headless server environment doesn't crash serve

---

## Stretch Goals

- **Remote sync:** `bob-log push` / `bob-log pull` are now core commands; a future enhancement is `bob-log sync` that does pull + push in one step with conflict detection
