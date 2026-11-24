# Bob Logbook — Hackathon Context File

> **APPEND-ONLY.** Do not edit existing entries. Add new entries at the bottom.
> If a decision changes, add a new entry marked `[SUPERSEDES entry-NNN]`.
> This file lives on the main branch so both teammates can read it.
> The shadow branch `bob-context` will hold the auto-captured hook log.

---

## Entry-001 — Project Setup
**Date:** 2026-11-24
**Author:** jaminleod
**Type:** decision

CIPS × IBM Virtual Hackathon. Build from 11 AM to 3 PM ET. Submit one PDF (4 pages max, 11-pt minimum). Optional video up to 10 min.

Scoring: Innovation & Creativity 25 pts · Relevance to Challenge 25 pts · Practicality & Feasibility 25 pts · Overall Quality & Presentation 25 pts. Must score ≥ 50/100 to qualify. Tie-break order: relevance → feasibility → innovation → quality. Prize: $1,400 CAD split equally among the winning team.

Resources: 4 hours, 300 Bobcoins, dev environment provided.

---

## Entry-002 — Idea Selection
**Date:** 2026-11-24
**Author:** jaminleod (via Bob planning session)
**Type:** decision

**Chosen idea: Bob Logbook**

**Problem statement:**
When a developer uses IBM Bob, the valuable context — decisions made, prompts that worked, constraints discovered — lives only in the chat and disappears. The developer has to manually extract and document it. No one does this consistently, and teammates cannot pick up exactly where someone left off without reading the full chat history.

**Core idea:**
A Bob lifecycle hook that automatically captures each session turn (user prompt + Bob's final response) and appends it as a structured, timestamped entry to a log file on a dedicated git shadow branch (`bob-context`). A companion HTML viewer renders the log as a readable timeline. Zero manual effort from the developer — install once and forget it.

**What makes it novel:**
- Uses Bob's own hook system to capture context from Bob — the tool dogfoods itself
- The shadow branch technique keeps the log entirely out of the developer's working branch, preventing merge conflicts
- The viewer gives the team a shared, real-time history that any teammate can open in a browser

**User story:**
"As a developer using IBM Bob, I want my AI session context captured automatically in git so my teammate can pick up exactly where I left off — without reading the entire chat history."

---

## Entry-003 — Division of Labour
**Date:** 2026-11-24
**Author:** jaminleod
**Type:** decision

**jaminleod:** Bob Logbook CLI / hook script
- `bob-log init` — initialises the shadow branch `bob-context` in the current repo
- `bob-log add` — appends a structured Markdown entry to `bob-context.md` on the shadow branch
- `bob-log export` — merges the full log into a single Markdown file in the working directory (for PDF / Bob context paste)
- Bob `Stop` hook config — fires the hook script automatically after each turn, reading `last_assistant_message` from stdin
- Bob `UserPromptSubmit` hook config — captures the user's prompt before it is sent

**Alex:** HTML viewer + frontend polish
- Single-file `viewer.html` — reads `bob-context.md` (or the exported file) and renders a clean session timeline
- Author-coloured entries, timestamps, event-type badges
- Can be opened in any browser or in the VS Code simple browser panel (no extension needed)
- Owns the visual design and PDF layout for the submission

---

## Entry-004 — Technical Constraints & Key Facts
**Date:** 2026-11-24
**Author:** jaminleod (via Bob docs search)
**Type:** technical-note

Bob lifecycle hook API (confirmed from docs):

- `Stop` hook: fires after the final turn. Receives JSON on stdin:
  `{ session_id, cwd, hook_event_name, last_assistant_message }`
  stdout is IGNORED — write to files directly in the hook script.
- `UserPromptSubmit` hook: fires before each prompt is sent. Receives JSON on stdin:
  `{ session_id, cwd, hook_event_name, prompt }`
  stdout is injected as context into the model — write log file from the hook script, do NOT print to stdout for logging purposes.
- Hooks are `type: command` — a shell script path. No external server needed.
- Hooks run with full user permissions, no sandbox.
- Configuration lives in `.bob/settings.json` (workspace scope) or `~/.bob/settings.json` (global scope).

Shadow branch strategy:
- `bob-context` branch is created with `git checkout --orphan bob-context` so it has no shared history with main.
- The hook script uses `git worktree add` or direct git plumbing to write to the shadow branch without touching the working tree.
- Entries are plain Markdown — append-only — so concurrent appends from two teammates only ever add lines, never conflict.

---

## Entry-005 — What to Document for Bob Usage (PDF requirement)
**Date:** 2026-11-24
**Author:** jaminleod
**Type:** reminder

The PDF must show how we meaningfully used IBM Bob. Evidence to capture:
1. This planning conversation — Bob helped us brainstorm, evaluate, and scope the idea
2. Bob used to write the hook script (jaminleod's workstream)
3. Bob used to generate the viewer HTML (Alex's workstream)
4. Bob used to write tests and the README
5. Screenshots of Bob in action during the build
6. The exported `bob-context.md` itself is proof — it was generated by the tool we built

---


## Entry-006 — Environment & Access Status
**Date:** 2026-11-24
**Author:** jaminleod
**Type:** technical-note

- Git repo initialised at `/home/jaminleod/projects/ibmbob`
- alexvu31 has access to the `main` branch
- `jq` is available in the dev environment — hook scripts can use it for JSON parsing
- Author identifiers to use in log entries: `jaminleod` (Benjamin) and `alexvu31`
- Sub-Task 1 (repo init) is complete — git is live

---

## Entry-007 — Revised Scope: Shadow Branch as AI Workspace
**Date:** 2026-11-24
**Author:** jaminleod (via Bob planning session)
**Type:** decision
**Supersedes:** Entry-002 (partial — core idea unchanged, scope expanded)

The shadow branch is no longer just a chat log. It is a **shared AI workspace** — a git branch where Bob (and developers) can read, write, and commit arbitrary files without touching the working tree. Git itself provides the safety net: nothing is ever lost, no force-pushes, no branch deletion via CLI.

**What changed from Entry-002:**
- Single `bob-context.md` → arbitrary file structure on the `bob-context` branch
- Shell script → Python 3 (stdlib only) for robustness and cleaner git plumbing
- `add` command → separate `write`, `append`, `read`, `ls`, `commit`, `export` commands
- Auto-hooks now write to `chat/$USER.md` per-author, not a shared flat file
- Viewer becomes a workspace browser (file tree + content panel), not just a timeline
- Author detection via `$USER` env var — works for both jaminleod and alexvu31 without config

**Governance model:** CLI path-jails all writes to the shadow branch (no `../` escapes). No destructive commands exposed. Git history is the rollback mechanism.

**Key implementation decision:** Python 3 stdlib only. No pip installs. `jq` no longer needed — `json.load(sys.stdin)` handles hook payloads natively.

---

## Entry-008 — Export Format Agreement (jaminleod ↔ alexvu31 coordination)
**Date:** 2026-11-24
**Author:** jaminleod
**Type:** technical-note

The `bob-log export` command (when called without a specific path) will produce a JSON file for the viewer to consume. Format:

```json
{
  "exported_at": "<ISO8601 timestamp>",
  "branch": "bob-context",
  "files": {
    "chat/jaminleod.md": "<full file content>",
    "chat/alexvu31.md": "<full file content>",
    "decisions.md": "<full file content>"
  }
}
```

alexvu31: the viewer should accept a file with this exact shape. The keys under `"files"` are the relative paths on the shadow branch. Files under `chat/` get the timeline renderer; all others get the plain Markdown renderer.

---
