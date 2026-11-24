# Bob Logbook — Hackathon Context File

> **APPEND-ONLY.** Do not edit existing entries. Add new entries at the bottom.
> If a decision changes, add a new entry marked `[SUPERSEDES entry-NNN]`.
> This file lives on the main branch so both teammates can read it.
> The shadow branch `bob-context` will hold the auto-captured hook log.

---

## Entry-001 — Project Setup
**Date:** 2026-11-24
**Author:** Jamin
**Type:** decision

CIPS × IBM Virtual Hackathon. Build from 11 AM to 3 PM ET. Submit one PDF (4 pages max, 11-pt minimum). Optional video up to 10 min.

Scoring: Innovation & Creativity 25 pts · Relevance to Challenge 25 pts · Practicality & Feasibility 25 pts · Overall Quality & Presentation 25 pts. Must score ≥ 50/100 to qualify. Tie-break order: relevance → feasibility → innovation → quality. Prize: $1,400 CAD split equally among the winning team.

Resources: 4 hours, 300 Bobcoins, dev environment provided.

---

## Entry-002 — Idea Selection
**Date:** 2026-11-24
**Author:** Jamin (via Bob planning session)
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
**Author:** Jamin
**Type:** decision

**Jamin:** Bob Logbook CLI / hook script
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
**Author:** Jamin (via Bob docs search)
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
**Author:** Jamin
**Type:** reminder

The PDF must show how we meaningfully used IBM Bob. Evidence to capture:
1. This planning conversation — Bob helped us brainstorm, evaluate, and scope the idea
2. Bob used to write the hook script (Jamin's workstream)
3. Bob used to generate the viewer HTML (Alex's workstream)
4. Bob used to write tests and the README
5. Screenshots of Bob in action during the build
6. The exported `bob-context.md` itself is proof — it was generated by the tool we built

---

