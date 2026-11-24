# Project Status — 2026-11-24T18:58:15Z
**Author:** jaminleod

## What's done

- Sub-Tasks 1–3: shadow branch init, `bob_log.py` CLI, hook config ✅
- Sub-Task 7: viewer entry format aligned, Markdown rendering in bubbles, All Contributors view ✅
- Sub-Task 7b: full IBM Carbon chat UI redesign (bubble layout, tabs, filters, collapsed sidebar) ✅
- Sub-Task 7c: `bob-log serve` live server with SSE (auto-loads, pushes new-data within 1s) ✅

## What's next (Sub-Tasks 8 & 9)

- **Sub-Task 8:** Add `bob-log log [--since <sha>] [path]` and `bob-log diff <path>` to `bob_log.py`
- **Sub-Task 9:** SessionStart hook (pull → log since cursor → summarise → push), `bob-log pull/push`, Bob skill SKILL.md

## How to run the viewer right now

```sh
python3 bob_log.py serve
# open http://localhost:4242
```

The viewer auto-loads from the shadow branch live — no JSON export needed.
SSE pushes updates within 1 second of any new hook entry.

## Key files

| File | Purpose |
|---|---|
| `bob_log.py` | Core CLI — init/read/write/append/ls/export-json/serve |
| `bob-log-hook.py` | Hook wrapper — writes Entry-NNN format to chat/$USER.md |
| `.bob/settings.json` | Wires Stop + UserPromptSubmit to hook wrapper |
| `viewer.html` | IBM Carbon chat UI, served by bob-log serve |
| `hackathon-plan.md` | Full plan — all sub-task status and todo lists |
| `CONTEXT.md` | Append-only decision log — read this for full history |

## Entry format (for your viewer to parse correctly)

Each hook entry looks like:

```
## Entry-NNN - <type>
**Timestamp:** 2026-11-24T18:00:00Z
**Author:** alexvu31
**Type:** user-prompt
**Session:** <session-id>

<message body>

---
```

Type is either `user-prompt` or `bob-response`.
Your Bob session will auto-write to `chat/alexvu31.md` once the hooks are running.
