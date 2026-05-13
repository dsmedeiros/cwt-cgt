#!/usr/bin/env bash
# Armature SubagentStop hook — task-completion
# Event: SubagentStop
# Invariant: TASK-002
#
# Purpose:
#   Advisory-only heuristic verification that the subagent deliverable
#   addresses each acceptance criterion recorded in the matching
#   correlation file (written by task-readiness.sh on PASS).
#
# Advisory-only contract:
#   This hook ALWAYS exits 0.  It never blocks work.  It emits
#   PASS: or ADVISORY: to stdout so the orchestrator can choose to
#   act (or not) on the signal.
#
# Threshold env var:
#   TASK_002_MATCH_THRESHOLD  (default: 0.7)
#   Set to a float in [0.0, 1.0] to tune keyword-coverage threshold.
#   0.0 → always PASS; 1.0 → all criteria must have a keyword match.
#
# Correlation file lifecycle (D3):
#   1. Written by task-readiness.sh on PASS into
#      .armature/session/active-delegations/<hash>.json
#   2. This hook reads the MOST RECENTLY MODIFIED .json in that dir.
#   3. This hook DELETES the file after evaluation (regardless of result).
#   4. If directory absent or empty → ADVISORY emitted, hook exits 0.
#
# Known limitations:
#   R2 (race): most-recently-modified heuristic is wrong when multiple
#     subagents run concurrently (atypical in Armature single-threaded model).
#     Deferred until Claude Code exposes a stable subagent_id field.
#   R3 (field uncertainty): exact SubagentStop payload field names vary
#     by Claude Code version.  Ordered field search (D2) is best-effort.
#     If deliverable text is not found → ADVISORY with "deliverable text not
#     found" is emitted; hook exits 0.
#
# Hotfix bypass:
#   If .armature/session/phase == "Hotfix" (ASCII strip only),
#   emit ADVISORY to stderr and exit 0 immediately.
#
# NUL-byte guard:
#   If stdin payload contains a NUL byte, emit WARN to stderr and exit 0.
#   This is defense-in-depth; Claude Code does not generate NUL bytes.
#
# Cross-platform: bash + Git Bash (Windows) compatible.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve Python interpreter (python3 preferred, python fallback).
# If neither is available, fail-open immediately.
# ---------------------------------------------------------------------------
PY=""
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
fi

[ -z "$PY" ] && exit 0  # fail-open: no Python

# ---------------------------------------------------------------------------
# Get REPO_ROOT — fail-open if not in a git repo
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
[ -z "$REPO_ROOT" ] && exit 0

# ---------------------------------------------------------------------------
# Main Python logic.
#
# Python code avoids single quotes so it can be embedded in a bash
# single-quoted heredoc variable (same pattern as task-readiness.sh).
# Values needing dynamic substitution are passed via environment variables.
# Always exits 0.
# ---------------------------------------------------------------------------
_PYTHON_MAIN='
import json, os, re, sys
from pathlib import Path

REPO_ROOT = os.environ.get("_TC_REPO_ROOT", "")
PHASE_FILE = os.path.join(REPO_ROOT, ".armature", "session", "phase")

# ---- 1. Read stdin bytes (preserve NUL for detection) ----
try:
    raw = sys.stdin.buffer.read()
except Exception:
    print("ADVISORY: TASK-002 — could not read stdin, skipping evaluation")
    sys.exit(0)

# ---- 2. NUL-byte rejection (defense-in-depth) ----
if b"\x00" in raw:
    sys.stderr.write("WARN [TASK-002]: stdin payload contains NUL byte — skipping.\n")
    sys.exit(0)

# ---- 3. Decode and parse JSON (fail-open on invalid JSON) ----
data = None
try:
    payload_str = raw.decode("utf-8", errors="replace")
    data = json.loads(payload_str)
except Exception:
    print("ADVISORY: TASK-002 — invalid JSON payload, skipping criteria evaluation")
    sys.exit(0)

# ---- 4. Hotfix bypass ----
# ASCII-only strip (M3 CP3 lesson: Unicode whitespace bypass via .strip() without
# args is a known attack vector).
if os.path.isfile(PHASE_FILE):
    try:
        with open(PHASE_FILE, "rb") as _pf:
            _phase_raw = _pf.read()
        if not any(b < 32 and b not in (9, 10, 13) for b in _phase_raw):
            _phase_val = _phase_raw.decode("utf-8", errors="replace").strip(" \t\n\r")
            if _phase_val == "Hotfix":
                sys.stderr.write(
                    "ADVISORY: Hotfix phase active — TASK-002 bypass per TASK-002\n"
                )
                sys.exit(0)
    except Exception:
        pass

# ---- 5. Deliverable extraction (D2) — ordered field search ----
deliverable_text = None

# 5a. tool_result.content (may be string or list of content blocks)
tr = data.get("tool_result")
if isinstance(tr, dict):
    content = tr.get("content")
    if isinstance(content, str):
        deliverable_text = content
    elif isinstance(content, list):
        # Join text-type blocks
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_val = block.get("text", "")
                    if isinstance(text_val, str):
                        parts.append(text_val)
            elif isinstance(block, str):
                parts.append(block)
        if parts:
            deliverable_text = " ".join(parts)

# 5b. output
if deliverable_text is None:
    v = data.get("output")
    if isinstance(v, str):
        deliverable_text = v

# 5c. result
if deliverable_text is None:
    v = data.get("result")
    if isinstance(v, str):
        deliverable_text = v

# 5d. subagent_output
if deliverable_text is None:
    v = data.get("subagent_output")
    if isinstance(v, str):
        deliverable_text = v

# 5e. message
if deliverable_text is None:
    v = data.get("message")
    if isinstance(v, str):
        deliverable_text = v

if deliverable_text is None:
    print("ADVISORY: TASK-002 — deliverable text not found in payload")
    sys.exit(0)

# ---- 6. Correlation file lookup (D3) — most-recently-modified .json ----
delegations_dir = os.path.join(REPO_ROOT, ".armature", "session", "active-delegations")
if not os.path.isdir(delegations_dir):
    print("ADVISORY: TASK-002 — no active delegation found (active-delegations/ absent)")
    sys.exit(0)

json_files = [
    os.path.join(delegations_dir, f)
    for f in os.listdir(delegations_dir)
    if f.endswith(".json")
]
if not json_files:
    print("ADVISORY: TASK-002 — no active delegation found (active-delegations/ empty)")
    sys.exit(0)

# Pick most recently modified
corr_file = max(json_files, key=os.path.getmtime)

# ---- 7. Parse correlation file ----
try:
    with open(corr_file, encoding="utf-8") as _cf:
        corr_data = json.load(_cf)
except Exception as exc:
    print("ADVISORY: TASK-002 — could not parse correlation file: " + str(exc))
    # Still attempt to delete it
    try:
        os.remove(corr_file)
    except Exception:
        pass
    sys.exit(0)

criteria_items = corr_data.get("criteria_items", [])
if not isinstance(criteria_items, list):
    criteria_items = []

# ---- 8. Keyword-anchor scan (D2) ----
STOPWORDS = {
    "a", "an", "the", "is", "are", "must", "should", "will",
    "of", "to", "for", "with", "in", "on", "at", "and", "or", "not",
}
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

deliverable_lower = deliverable_text.lower()

def _has_keyword_match(criterion):
    tokens_raw = PUNCT_RE.sub(" ", criterion).lower().split()
    keywords = [t for t in tokens_raw if t and t not in STOPWORDS]
    if not keywords:
        return False
    return any(kw in deliverable_lower for kw in keywords)

if not criteria_items:
    # No criteria to check; treat as PASS with zero-item note
    matched = 0
    total = 0
else:
    matched = sum(1 for item in criteria_items if _has_keyword_match(item))
    total = len(criteria_items)

# ---- 9. Threshold evaluation ----
try:
    threshold = float(os.environ.get("TASK_002_MATCH_THRESHOLD", "0.7"))
except ValueError:
    threshold = 0.7

threshold_pct = int(threshold * 100)

if total == 0:
    # Zero criteria: advisory, no meaningful check possible
    ratio = 1.0
    print("ADVISORY: TASK-002 criteria coverage = 0/0 (no criteria items found)")
else:
    ratio = matched / total
    pct = int(ratio * 100)
    if ratio >= threshold:
        print(
            "PASS: TASK-002 criteria coverage = {}/{} ({}%)".format(
                matched, total, pct
            )
        )
    else:
        print(
            "ADVISORY: TASK-002 criteria coverage = {}/{} ({}%) below threshold {}%".format(
                matched, total, pct, threshold_pct
            )
        )

# ---- 10. Delete correlation file (regardless of pass/fail) ----
try:
    os.remove(corr_file)
except Exception as exc:
    sys.stderr.write("WARN [TASK-002]: Could not delete correlation file: " + str(exc) + "\n")

sys.exit(0)
'

export _TC_REPO_ROOT="$REPO_ROOT"
_MAIN_RC=0
if command -v python3 >/dev/null 2>&1; then
    python3 -c "$_PYTHON_MAIN" || _MAIN_RC=$?
elif command -v python >/dev/null 2>&1; then
    python -c "$_PYTHON_MAIN" || _MAIN_RC=$?
fi
# Always exit 0 — advisory-only hook
exit 0
