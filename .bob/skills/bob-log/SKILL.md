---
name: bob-log
description: Use when you want to read, write, or record something to the Bob Logbook shadow branch — covers reading context from prior sessions, appending notes or decisions, checking what files are on the branch, and exporting a JSON snapshot for the viewer.
---

# Bob Logbook — Shadow Branch Commands

Bob Logbook stores files on a dedicated `bob-context` git branch that never touches the working tree.
Every command goes through `bob_log.py` using git plumbing only.

## When to use this skill

Activate when the user (or you, proactively) needs to:
- Record a decision, note, or finding to the shadow branch
- Read back prior session context from `chat/$USER.md` or another file
- Check what files currently exist on the shadow branch
- Export the full workspace to JSON for the viewer

## Setup check

Before any command, verify the shadow branch exists:

```
python3 bob_log.py ls
```

If you see `Error: branch 'bob-context' does not exist`, run init first:

```
python3 bob_log.py init
```

## Command reference

### Read a file
```
python3 bob_log.py read <path>
```
Example — read your own session log:
```
python3 bob_log.py read chat/jaminleod.md
```

### Write a file (create or overwrite)
```
python3 bob_log.py write <path> "<content>"
```
Use for structured files like `decisions.md`. Content is a single string argument.

### Append to a file (most common for logging)
```
python3 bob_log.py append <path> "<content>"
```
Creates the file if it does not exist. Use for incremental notes and decision logs.

### List files
```
python3 bob_log.py ls           # root
python3 bob_log.py ls chat/     # subdirectory
```

### Export all files to JSON (for the viewer)
```
python3 bob_log.py export-json bob-context-export.json
```
Then open `viewer.html` and drag the JSON file onto it.

### Copy one file into the working tree
```
python3 bob_log.py export <shadow-path> <dest-path>
```

## Path rules

- All paths are relative to the shadow-branch root (e.g. `chat/alice.md`, `decisions.md`)
- Absolute paths (`/etc/...`) and traversals (`../../...`) are rejected
- Author logs live under `chat/<username>.md` — use `$USER` or the author's login

## Proactive use

During a session you may proactively:
1. **Append a decision** after the user confirms a direction: `append decisions.md "## <date> — <title>\n<rationale>\n"`
2. **Read prior context** at session start: `read chat/<author>.md` to see what was decided last time
3. **Export** before the session ends so the viewer is up to date

Always use `append`, never `write`, for chat logs — `write` overwrites the entire file.
