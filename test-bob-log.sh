#!/usr/bin/env sh
# test-bob-log.sh — integration tests for bob-log.sh
# Usage: sh test-bob-log.sh [path/to/bob-log.sh]
# Requires: git, sh
# Runs in a fresh temp directory; cleans up on exit.
# Note: no set -e — we capture exit codes manually in assert helpers.

# ── Locate bob-log.sh ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOB_LOG="${1:-$SCRIPT_DIR/bob-log.sh}"

if [ ! -f "$BOB_LOG" ]; then
  echo "ERROR: bob-log.sh not found at: $BOB_LOG"
  echo "Usage: sh test-bob-log.sh [path/to/bob-log.sh]"
  exit 1
fi

BOB_LOG="$(cd "$(dirname "$BOB_LOG")" && pwd)/$(basename "$BOB_LOG")"

# ── Helpers ──────────────────────────────────────────────────────────────────
PASS=0
FAIL=0
TOTAL=0

pass() { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); printf "  \033[32m✓\033[0m %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); printf "  \033[31m✗\033[0m %s\n" "$1"; }

assert_zero() {
  # assert_zero <description> <command...>
  desc="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "$desc"; else fail "$desc"; fi
}

assert_nonzero() {
  desc="$1"; shift
  if ! "$@" >/dev/null 2>&1; then pass "$desc"; else fail "$desc"; fi
}

assert_contains() {
  # assert_contains <description> <pattern> <string>
  desc="$1"; pattern="$2"; value="$3"
  if printf '%s' "$value" | grep -qF "$pattern"; then
    pass "$desc"
  else
    fail "$desc  (expected to find: $pattern)"
  fi
}

assert_file_exists() {
  desc="$1"; file="$2"
  if [ -f "$file" ]; then pass "$desc"; else fail "$desc  (missing: $file)"; fi
}

# ── Setup temp repo ──────────────────────────────────────────────────────────
TEST_REPO="$(mktemp -d)"
cleanup() { rm -rf "$TEST_REPO"; }
trap cleanup EXIT INT TERM

cd "$TEST_REPO"
git init -q
git config user.email "test@test.local"
git config user.name  "Test"

# Create a dummy initial commit on main so the repo is valid
echo "# test repo" > README.md
git add README.md
git commit -q -m "initial"

echo ""
echo "Bob Logbook — test suite"
echo "========================"
echo "Temp repo: $TEST_REPO"
echo "Script:    $BOB_LOG"
echo ""

# ── Test group 1: init ───────────────────────────────────────────────────────
echo "[ init ]"

assert_zero "bob-log init exits with code 0" sh "$BOB_LOG" init

# The shadow branch must now exist
BRANCH="$(git branch | grep bob-context | tr -d ' *' || echo '')"
assert_contains "bob-context branch was created" "bob-context" "$BRANCH"

# bob-context.md must exist on that branch
BOB_MD="$(git show bob-context:bob-context.md 2>&1)"
assert_contains "bob-context.md exists on shadow branch" "Bob Logbook" "$BOB_MD"

# init is idempotent — running again must not error
assert_zero "bob-log init is idempotent (second run)" sh "$BOB_LOG" init

echo ""

# ── Test group 2: add ────────────────────────────────────────────────────────
echo "[ add ]"

assert_zero "bob-log add prompt exits 0" \
  sh "$BOB_LOG" add prompt Jamin "test prompt message"

AFTER_ADD="$(git show bob-context:bob-context.md 2>&1)"
assert_contains "add: event-type written" "prompt" "$AFTER_ADD"
assert_contains "add: author written"     "Jamin"  "$AFTER_ADD"
assert_contains "add: message written"    "test prompt message" "$AFTER_ADD"

# Add a second entry with a different author and type
assert_zero "bob-log add stop exits 0" \
  sh "$BOB_LOG" add stop Bob "assistant response text"

AFTER_STOP="$(git show bob-context:bob-context.md 2>&1)"
assert_contains "add: second entry written" "Bob"  "$AFTER_STOP"
assert_contains "add: stop type present"    "stop" "$AFTER_STOP"

# Working tree must NOT contain bob-context.md (stays on shadow branch only)
assert_nonzero "add: working tree is not dirtied" \
  test -f "$TEST_REPO/bob-context.md"

echo ""

# ── Test group 3: export ─────────────────────────────────────────────────────
echo "[ export ]"

assert_zero "bob-log export exits 0" sh "$BOB_LOG" export

assert_file_exists "bob-context-export.md was created" "$TEST_REPO/bob-context-export.md"

EXPORT="$(cat "$TEST_REPO/bob-context-export.md" 2>&1)"
assert_contains "export: contains prompt entry"  "test prompt message" "$EXPORT"
assert_contains "export: contains stop entry"    "assistant response text" "$EXPORT"
assert_contains "export: contains both authors"  "Jamin" "$EXPORT"

echo ""

# ── Test group 4: edge cases ─────────────────────────────────────────────────
echo "[ edge cases ]"

# Message with spaces and special chars
assert_zero "add: message with special chars" \
  sh "$BOB_LOG" add manual Alex "message with 'quotes' & symbols"

SPECIAL="$(git show bob-context:bob-context.md 2>&1)"
assert_contains "add: special chars preserved" "quotes" "$SPECIAL"

# Unknown event type should still write (graceful)
assert_zero "add: unknown event type accepted" \
  sh "$BOB_LOG" add custom-type SomeUser "custom event"

echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo "Results: $PASS/$TOTAL passed"
if [ "$FAIL" -gt 0 ]; then
  printf "\033[31m%d test(s) FAILED\033[0m\n" "$FAIL"
  exit 1
else
  printf "\033[32mAll tests passed.\033[0m\n"
  exit 0
fi
