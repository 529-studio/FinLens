#!/usr/bin/env bash
# ==============================================================================
# FinSight: Sprint Boundary Closer & Conversation Handoff Validator
# ==============================================================================
# Usage:
#   tools/sprint/close.sh                 # validate handoff + print bootstrap prompt
#   tools/sprint/close.sh --launch        # validate + start fresh agy conversation
#   tools/sprint/close.sh --sprint 1      # explicit sprint number
#   tools/sprint/close.sh --init          # write handoff & report skeletons
# ==============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SPRINT=""
LAUNCH=0
INIT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --sprint) SPRINT="${2:?--sprint needs a number}"; shift 2 ;;
    --launch) LAUNCH=1; shift ;;
    --init) INIT=1; shift ;;
    -h|--help)
      echo "Usage: tools/sprint/close.sh [--sprint <N>] [--init] [--launch]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Infer sprint number from branch (e.g. feat/s1-..., docs/s1-handoff) or latest handoff
if [ -z "$SPRINT" ]; then
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  SPRINT="$(printf '%s' "$branch" | sed -n 's/.*[/_-]s\([0-9][0-9]*\)[/_.-].*/\1/p' | head -1)"
fi
if [ -z "$SPRINT" ]; then
  latest="$( (ls -1 docs/HANDOFF-s*.md 2>/dev/null || true) \
    | sed -n 's/.*HANDOFF-s\([0-9][0-9]*\)\.md/\1/p' | sort -n | tail -1)"
  SPRINT="${latest:-1}"
fi

HANDOFF="docs/HANDOFF-s${SPRINT}.md"
REPORT="docs/reports/sprint${SPRINT}_report.md"
HANDOFF_TEMPLATE="docs/templates/handoff.md"
REPORT_TEMPLATE="docs/reports/templates/sprint_report_template.md"

if [ "$INIT" -eq 1 ]; then
  mkdir -p docs/reports
  if [ ! -f "$HANDOFF" ]; then
    today=$(date +%Y-%m-%d)
    sed -e "s/<N>/${SPRINT}/g" -e "s/<N+1>/$((SPRINT + 1))/g" -e "s/<YYYY-MM-DD>/${today}/g" "$HANDOFF_TEMPLATE" > "$HANDOFF"
    echo "  [Created] $HANDOFF from template."
  else
    echo "  [Exists] $HANDOFF already exists."
  fi

  if [ ! -f "$REPORT" ]; then
    today=$(date +%Y-%m-%d)
    sed -e "s/<N>/${SPRINT}/g" -e "s/<N+1>/$((SPRINT + 1))/g" -e "s/<YYYY-MM-DD>/${today}/g" "$REPORT_TEMPLATE" > "$REPORT"
    echo "  [Created] $REPORT from template."
  else
    echo "  [Exists] $REPORT already exists."
  fi

  echo "Fill in the details, verify your work, and run tools/sprint/close.sh again."
  exit 0
fi

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -f "$HANDOFF" ] || fail "$HANDOFF is missing - run tools/sprint/close.sh --init or sprint-close skill"

size=$(wc -c < "$HANDOFF" | tr -d ' ')
[ "$size" -ge 700 ] || fail "$HANDOFF is only ${size} B - a handoff that short cannot carry the sprint state (min 700 B)"
[ "$size" -le 12288 ] || fail "$HANDOFF is ${size} B, over the 12 KB ceiling"

if grep -q '<YYYY-MM-DD>' "$HANDOFF"; then
  fail "$HANDOFF is still an unfilled template skeleton"
fi

sections=$(grep -c '^## ' "$HANDOFF" || true)
[ "$sections" -ge 4 ] || fail "$HANDOFF has only ${sections} sections - expected at least 4 numbered sections"

if ! grep -qi '^## .*\(next\|horizon\)' "$HANDOFF"; then
  fail "$HANDOFF has no next-sprint / horizon section - the next conversation has nowhere to start"
fi

git ls-files --error-unmatch "$HANDOFF" >/dev/null 2>&1 \
  || fail "$HANDOFF is untracked in git - commit it with the sprint close"

if [ -n "$(git status --porcelain -- "$HANDOFF")" ]; then
  fail "$HANDOFF has uncommitted changes - commit it before closing the sprint"
fi

if [ ! -f "$REPORT" ]; then
  echo "WARN: Sprint report $REPORT not found - author it before closing" >&2
fi

PROMPT="Read AGENTS.md (rules 1, 11, 12), then ${HANDOFF}. This conversation starts Sprint $((SPRINT + 1)) for FinSight. Confirm in one short paragraph: current branch, what Sprint ${SPRINT} shipped, and the first task from the handoff's next-sprint section. Do not re-plan Sprint ${SPRINT} and do not re-derive decisions recorded in the handoff; if a fact looks wrong, say so instead of assuming."

printf '\n======================================================================\n'
printf ' Sprint %s handoff OK (%s B, %s sections, tracked & committed).\n' "$SPRINT" "$size" "$sections"
printf '======================================================================\n\n'
printf 'Bootstrap prompt for the next conversation:\n\n%s\n\n' "$PROMPT"
printf 'Start next conversation with:\n  tools/sprint/close.sh --launch\n'
printf 'Or manually:\n  agy -i "%s"\n\n' "$PROMPT"

if [ "$LAUNCH" -eq 1 ]; then
  command -v agy >/dev/null 2>&1 || fail "agy CLI is not installed or not in PATH"
  exec agy -i "$PROMPT"
fi
