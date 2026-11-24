# Bob Logbook

> Automatically capture IBM Bob session context into an append-only git log — and render it as a clean browser timeline.

---

## What it does

Every time you work with IBM Bob, valuable context accumulates: decisions made, prompts that worked, constraints discovered. That context normally lives only in the chat window and disappears when the session ends.

**Bob Logbook** solves this with two Bob lifecycle hooks:

| Hook | What it captures |
|---|---|
| `UserPromptSubmit` | Your prompt, before it is sent to Bob |
| `Stop` | Bob's final response, after each turn |

Each captured event is appended as a timestamped Markdown entry to `bob-context.md` on a dedicated **shadow branch** (`bob-context`). The shadow branch shares no history with `main`, so there are never merge conflicts. Run `bob-log export` any time to pull the full log into your working directory, then open `viewer.html` in a browser to see a colour-coded session timeline.

---

## Why it exists

- **Zero manual effort** — install once, capture forever.
- **Dogfoods Bob** — the tool was built entirely using Bob.
- **Team-friendly** — teammates can open the viewer and pick up exactly where someone left off, without reading the full chat history.
- **No external dependencies** — pure shell + git + a single HTML file. Runs anywhere git runs.

---

## Install

### 1. Copy the scripts into your project

```sh
# From the Bob Logbook repo root:
cp bob-log.sh      /path/to/your/project/
cp bob-log-hook.sh /path/to/your/project/
cp viewer.html     /path/to/your/project/
```

### 2. Initialise the shadow branch

```sh
cd /path/to/your/project
sh bob-log.sh init
```

This creates the `bob-context` orphan branch with an empty `bob-context.md`.  
Running `init` again is safe — it is idempotent.

### 3. Configure the Bob hooks

Create (or extend) `.bob/settings.json` in your project root:

```json
{
  "hooks": [
    {
      "event": "Stop",
      "type": "command",
      "command": "sh bob-log-hook.sh"
    },
    {
      "event": "UserPromptSubmit",
      "type": "command",
      "command": "sh bob-log-hook.sh"
    }
  ]
}
```

Bob will now automatically call `bob-log-hook.sh` on every turn. The hook reads the JSON payload from stdin and routes it to `bob-log add`.

---

## `bob-log` command reference

```
sh bob-log.sh <subcommand> [args]
```

| Subcommand | Syntax | Description |
|---|---|---|
| `init` | `bob-log.sh init` | Idempotently creates the `bob-context` shadow branch |
| `add` | `bob-log.sh add <type> <author> <message>` | Appends a timestamped entry to the shadow branch |
| `export` | `bob-log.sh export` | Writes the full log to `bob-context-export.md` in the working directory |

**Event types:** `prompt`, `stop`, `manual`, `decision` — any string is accepted.

**Examples:**

```sh
# Capture a manual note
sh bob-log.sh add manual Alex "Decided to use the shadow branch approach"

# Export the log to the working directory
sh bob-log.sh export

# View what's on the shadow branch without exporting
git show bob-context:bob-context.md
```

---

## Viewer usage

Open `viewer.html` in any browser — no server required.

1. Click **Choose file** (or drag and drop) and select `bob-context-export.md`.
2. The timeline renders immediately: each entry is a colour-coded card showing author, event type, timestamp, and message.
3. Use **Print / Save PDF** (top-right) to generate a print-ready version for documentation or the submission PDF.

**Demo mode:** Open `viewer.html?demo` to see sample data without loading a file.

---

## Running the tests

```sh
sh test-bob-log.sh
# or, if bob-log.sh is in a different location:
sh test-bob-log.sh /path/to/bob-log.sh
```

The test script:
- Creates a fresh `git init` temp directory
- Runs `init`, `add` (prompt, stop, manual, edge-case types), and `export`
- Asserts branch creation, entry content, working-tree cleanliness, and file output
- Cleans up on exit (pass or fail)
- Exits `0` on success, `1` on any failure

No test framework is required — pure POSIX shell.

---

## Repo structure

```
.
├── bob-log.sh              # Core CLI (init / add / export)
├── bob-log-hook.sh         # Bob hook wrapper (reads stdin JSON)
├── viewer.html             # Single-file browser timeline viewer
├── test-bob-log.sh         # Integration test suite
├── .bob/
│   └── settings.json       # Bob hook configuration
├── CONTEXT.md              # Append-only decision log (main branch)
└── README.md               # This file
```

---

## How entries look

Each `bob-log add` call produces a section like this in `bob-context.md`:

```markdown
## Entry-NNN — <event-type>
**Timestamp:** 2026-11-24T16:05:23Z
**Author:** Jamin
**Type:** prompt

The user's prompt text goes here.

---
```

The viewer parses these sections and renders them as timeline cards.

---

## Team

- **Jamin** — CLI shell script, hook wiring, git shadow-branch plumbing  
- **Alex** — HTML viewer, test suite, README, PDF layout  

Built in 4 hours for the CIPS × IBM Virtual Hackathon (2026).
