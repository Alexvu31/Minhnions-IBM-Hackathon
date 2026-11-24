# Bob Logbook — Hackathon MVP Plan

## Overview

**Goal:** Build "Bob Logbook" — a tool that automatically captures IBM Bob session context (user prompts + Bob responses) into an append-only Markdown log on a dedicated git shadow branch (`bob-context`), and renders it as a clean HTML timeline.

**Why this wins:** It dogfoods Bob (we use Bob to build a tool for Bob), demonstrates the full challenge workflow (plan → build → test → document), introduces a novel git shadow-branch technique, and directly addresses a real pain point IBM's own developers will recognise.

**Deliverables:**
1. `bob-log` shell script (CLI: `init`, `add`, `export` subcommands)
2. `.bob/settings.json` hook configuration wiring the script to `Stop` and `UserPromptSubmit` events
3. `viewer.html` — single-file timeline viewer for the log
4. `README.md` — setup and usage guide
5. PDF submission (4 pages, 11-pt minimum)

**Division of labour:**
- **Jamin:** Tasks 1–3 (hook script + git plumbing)
- **Alex:** Tasks 4–5 (viewer + PDF layout)
- **Both:** Task 6 (README + PDF content)

---

## Sub-Task 1 — Repo & Shadow Branch Init

**Status:** [ ] pending

**Intent:** Establish the git repo and create the `bob-context` orphan branch so the shadow branch exists before any hook tries to write to it.

**Expected Outcomes:**
- `git init` run in `/home/jaminleod/projects/ibmbob`
- An orphan branch `bob-context` exists with an empty initial commit
- The working tree returns to `main` after setup
- A `.gitignore` excludes any build artifacts

**Todo List:**
1. Run `git init` if not already initialised
2. Create the orphan branch: `git checkout --orphan bob-context`
3. Clear the index: `git rm -rf .`
4. Create a minimal `bob-context.md` placeholder with a header
5. Commit it as the branch root: `git add bob-context.md && git commit -m "init: shadow branch"`
6. Return to main: `git checkout main` (or `git checkout -b main` if first run)
7. Add `.gitignore`

**Relevant Context:**
- Orphan branch means zero shared history with `main` — no merge conflicts possible on context entries
- See Entry-004 in `CONTEXT.md` for the git strategy rationale

---

## Sub-Task 2 — `bob-log` Shell Script (Core CLI)

**Status:** [ ] pending

**Intent:** Write the shell script that implements the three subcommands the hook and teammates will call.

**Expected Outcomes:**
- `bob-log init` — idempotent; creates the shadow branch if it doesn't exist
- `bob-log add <event-type> <author> <message>` — appends a formatted Markdown entry to `bob-context.md` on the shadow branch without touching the working tree
- `bob-log export` — writes the full contents of `bob-context.md` from the shadow branch into `bob-context-export.md` in the working directory
- Script is executable and has no external dependencies beyond `git`, `date`, and standard POSIX shell

**Todo List:**
1. Create `bob-log.sh` in the repo root
2. Implement `init` subcommand using `git worktree` or git plumbing to avoid branch switching
3. Implement `add` subcommand:
   - Accept event type (`stop`, `prompt`, `manual`), author, and message text
   - Format entry as a Markdown section with timestamp, author, type badge, and message
   - Append to `bob-context.md` on the shadow branch via `git show` + append + `git hash-object` + `git update-index` + `git commit-tree` + `git update-ref` (pure plumbing — no worktree switch)
4. Implement `export` subcommand using `git show bob-context:bob-context.md > bob-context-export.md`
5. Add `--help` output for each subcommand
6. Make executable: `chmod +x bob-log.sh`

**Relevant Context:**
- Using git plumbing (`hash-object`, `update-index`, `commit-tree`, `update-ref`) lets the script write to the shadow branch from any working-tree state — Jamin's systems background applies directly here
- The script must be safe to call from a hook (non-interactive, no prompts, fast)

---

## Sub-Task 3 — Bob Hook Configuration

**Status:** [ ] pending

**Intent:** Wire the `bob-log` script into Bob's lifecycle so context is captured automatically on every turn, with zero developer interaction.

**Expected Outcomes:**
- `.bob/settings.json` exists with `Stop` and `UserPromptSubmit` hooks configured
- After each Bob turn, `Stop` fires and appends the `last_assistant_message` to the log (author: Bob, type: stop)
- When a user submits a prompt, `UserPromptSubmit` fires and appends the prompt to the log (author: derived from `$USER`, type: prompt)
- Hook script reads JSON from stdin using `jq` or basic shell parsing

**Todo List:**
1. Create `.bob/` directory if not present
2. Write `.bob/settings.json` with the hook configuration:
   - `Stop` → `command: "sh bob-log-hook.sh"` (wrapper that reads stdin JSON and calls `bob-log add`)
   - `UserPromptSubmit` → same wrapper
3. Write `bob-log-hook.sh` — reads stdin JSON, extracts `hook_event_name`, routes to the right `bob-log add` call
4. Test by running Bob and confirming entries appear on the shadow branch after a turn
5. Document the hook setup in `README.md`

**Relevant Context:**
- `Stop` hook stdin: `{ session_id, cwd, hook_event_name, last_assistant_message }`
- `UserPromptSubmit` hook stdin: `{ session_id, cwd, hook_event_name, prompt }`
- Hook stdout for `Stop` is IGNORED — write directly to git, do not print to stdout for logging
- Hook stdout for `UserPromptSubmit` is injected into the model context — do NOT print the log entry to stdout in this hook
- See Entry-004 in `CONTEXT.md` for full hook reference

---

## Sub-Task 4 — HTML Viewer (Alex)

**Status:** [ ] pending

**Intent:** Build a single-file HTML viewer that renders `bob-context-export.md` (produced by `bob-log export`) as a human-readable session timeline.

**Expected Outcomes:**
- `viewer.html` — opens in any browser with no server, no build step
- Reads the Markdown file contents (via a file input or fetch from same directory)
- Renders each entry as a timeline card: timestamp, author badge (colour-coded per author), event-type tag, message body
- Clean, minimal design — legible in a screenshot for the PDF

**Todo List:**
1. Create `viewer.html` with inline CSS and JS (no external dependencies)
2. Add a file picker or drag-and-drop input to load `bob-context-export.md`
3. Parse the Markdown entries (simple string splitting on the entry header pattern)
4. Render cards in a vertical timeline layout
5. Assign a consistent colour per author name (hash-based or hardcoded for the two authors)
6. Add a "Export as PNG" or print-friendly CSS for screenshot use in the PDF
7. Test with a real exported log

**Relevant Context:**
- The Markdown entry format is defined by `bob-log add` in Sub-Task 2 — coordinate with Jamin on the exact header pattern
- No external API, no npm, no bundler — pure HTML/CSS/JS so it works in the VS Code simple browser panel too

---

## Sub-Task 5 — Tests & README

**Status:** [ ] pending

**Intent:** Add basic tests for the CLI script and write the README so the judges can reproduce the tool.

**Expected Outcomes:**
- A test script `test-bob-log.sh` that exercises `init`, `add`, and `export` in a temp git repo and asserts the outputs
- `README.md` covering: what it does, why it exists, install steps, hook setup, `bob-log` command reference, viewer usage
- Tests pass cleanly

**Todo List:**
1. Write `test-bob-log.sh`:
   - Create a temp dir + `git init`
   - Run `bob-log init` and assert `bob-context` branch exists
   - Run `bob-log add prompt Jamin "test prompt"` and assert the entry appears in `git show bob-context:bob-context.md`
   - Run `bob-log export` and assert `bob-context-export.md` exists and contains the entry
   - Clean up temp dir
2. Write `README.md` with the sections above
3. Run tests and fix any failures

**Relevant Context:**
- Tests are shell scripts — no test framework needed
- Keep the README short; judges read fast

---

## Sub-Task 6 — PDF Submission

**Status:** [ ] pending

**Intent:** Produce the 4-page PDF submission that demonstrates how we used Bob and what we built.

**Expected Outcomes:**
- PDF is 4 pages max, 11-pt minimum font
- Page 1: Problem statement + user story + solution overview
- Page 2: Architecture diagram (hook → script → shadow branch → viewer) + Bob usage evidence (screenshots)
- Page 3: Code walkthrough — hook config, `bob-log add` plumbing, viewer rendering
- Page 4: Testing + how to run + team reflection on using Bob

**Todo List:**
1. Take screenshots of Bob in action during the build (Jamin + Alex)
2. Export the final `bob-context.md` using `bob-log export` — this is live evidence
3. Alex drafts the PDF layout (Canva, Google Slides → PDF, or LaTeX)
4. Jamin reviews and fills in technical accuracy
5. Final PDF export — confirm font size ≥ 11pt and page count ≤ 4
6. Attach PDF to submission email

**Relevant Context:**
- Judges score on Innovation, Relevance, Practicality, and Quality — the PDF must address all four
- The `CONTEXT.md` file in this repo (Entry-005) lists all the Bob usage evidence to include
- Optional: record a short demo video (up to 10 min) showing the full workflow

---

## Scoring Checklist

| Criterion | How we address it |
|---|---|
| Innovation & Creativity | Shadow-branch git technique is novel; tool dogfoods Bob itself |
| Relevance to Challenge | Directly extends IBM Bob; complete workflow from hook install to viewer |
| Practicality & Feasibility | Pure shell + HTML, no accounts, no external APIs, runs anywhere git runs |
| Overall Quality & Presentation | Clean viewer, working tests, clear README, well-structured PDF |
