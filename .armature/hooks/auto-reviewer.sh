#!/usr/bin/env bash
# Armature SubagentStop hook — auto-reviewer
# Event: SubagentStop
# Invariant: TASK-003
#
# Purpose:
#   Emit a structured HTML comment advisory directing the orchestrator to
#   dispatch the reviewer persona.  When red-team trigger conditions are met,
#   set red-team=true so the orchestrator also dispatches the red-team reviewer.
#
# Advisory emission contract (D4 — Orchestrator contract):
#   - The orchestrator reads the <!-- AUTO-REVIEW-REQUIRED --> HTML comment
#     from this hook's stdout as injected context.
#   - On seeing this marker, the orchestrator MUST spawn the reviewer before
#     accepting the deliverable.
#   - If red-team=true, the orchestrator MUST also spawn the red-team reviewer
#     after standard reviewer PASS.
#   - The orchestrator transcribes the advisory into .armature/session/state.md
#     under ## Pending Reviews.
#   - This hook does NOT itself spawn sub-agents — Claude Code hooks cannot do
#     that.  The hook emits a structured advisory; the orchestrator acts on it.
#   - If the orchestrator cannot find the <!-- AUTO-REVIEW-REQUIRED --> marker
#     in its context (e.g., hook output was not injected), the orchestrator
#     persona directive (TASK-003) serves as behavioral backstop.
#
# Red-team trigger conditions (D4) — red-team=true when ANY of:
#   - payload severity field equals "critical" (exact match)
#   - deliverable text contains any of (case-sensitive):
#       CRITICAL, cross-cutting, new invariant, new ADR, schema change
#   - environment variable FORCE_RED_TEAM == "1" (or "true")
#
# Always exits 0 — advisory emission hook, never blocks work.
#
# NUL-byte guard:
#   If stdin payload contains a NUL byte, emit WARN to stderr; still emit
#   the fallback HTML comment with implementer=unknown, exit 0.
#
# Hotfix bypass:
#   If .armature/session/phase == "Hotfix" (ASCII strip only),
#   emit ADVISORY to stderr but STILL emit the HTML comment (the orchestrator
#   may still need to dispatch review).  Exit 0.
#
# HTML comment sanitization:
#   Values are sanitized before emission: -- replaced with - - (cannot appear
#   inside an HTML comment), newlines stripped, values capped at 200 chars.
#
# Cross-platform: bash + Git Bash (Windows) compatible.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve Python interpreter (python3 preferred, python fallback).
# If neither is available, emit fallback comment and exit 0.
# ---------------------------------------------------------------------------
PY=""
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
elif command -v python >/dev/null 2>&1; then
    PY="python"
fi

if [ -z "$PY" ]; then
    printf '<!-- AUTO-REVIEW-REQUIRED\nimplementer=unknown\nscope=unknown\nred-team=false\nreason=no-python\n-->\n'
    exit 0
fi

# ---------------------------------------------------------------------------
# Get REPO_ROOT — fallback to pwd if not in a git repo
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# ---------------------------------------------------------------------------
# Main Python logic.
#
# Python code avoids single quotes so it can be embedded in a bash
# single-quoted heredoc variable (same pattern as task-readiness.sh).
# Always exits 0.
# ---------------------------------------------------------------------------
_PYTHON_MAIN='
import json, os, re, sys

REPO_ROOT = os.environ.get("_AR_REPO_ROOT", "")
PHASE_FILE = os.path.join(REPO_ROOT, ".armature", "session", "phase")

# ---- Sanitize helper ----
def _sanitize(val, max_len=200):
    """Strip newlines, replace -- with - -, cap length."""
    val = str(val)
    val = val.replace("\n", " ").replace("\r", " ")
    val = val.replace("--", "- -")
    return val[:max_len]

# ---- Emit HTML comment ----
def _emit(implementer, scope, red_team, reason):
    print("<!-- AUTO-REVIEW-REQUIRED")
    print("implementer=" + _sanitize(implementer))
    print("scope=" + _sanitize(scope))
    print("red-team=" + ("true" if red_team else "false"))
    print("reason=" + _sanitize(reason))
    print("-->")

# ---- 1. Read stdin bytes (preserve NUL for detection) ----
try:
    raw = sys.stdin.buffer.read()
except Exception:
    _emit("unknown", "unknown", False, "stdin-read-error")
    sys.exit(0)

# ---- 2. NUL-byte rejection ----
if b"\x00" in raw:
    sys.stderr.write("WARN [TASK-003]: stdin payload contains NUL byte — emitting fallback advisory.\n")
    _emit("unknown", "unknown", False, "nul-byte-payload")
    sys.exit(0)

# ---- 3. Decode and parse JSON (fail-open: emit fallback advisory) ----
data = None
try:
    payload_str = raw.decode("utf-8", errors="replace")
    data = json.loads(payload_str)
except Exception:
    _emit("unknown", "unknown", False, "invalid-payload")
    sys.exit(0)

# ---- 4. Hotfix bypass — emit ADVISORY but STILL emit HTML comment ----
hotfix_active = False
if os.path.isfile(PHASE_FILE):
    try:
        with open(PHASE_FILE, "rb") as _pf:
            _phase_raw = _pf.read()
        if not any(b < 32 and b not in (9, 10, 13) for b in _phase_raw):
            _phase_val = _phase_raw.decode("utf-8", errors="replace").strip(" \t\n\r")
            if _phase_val == "Hotfix":
                sys.stderr.write(
                    "ADVISORY: Hotfix phase active — TASK-003 bypass per TASK-003\n"
                )
                hotfix_active = True
    except Exception:
        pass

# ---- 5. Extract fields ----

# implementer: from subagent_type, agent_type, or subagent_name
implementer = (
    data.get("subagent_type")
    or data.get("agent_type")
    or data.get("subagent_name")
    or "unknown"
)
if not isinstance(implementer, str):
    implementer = "unknown"

# scope: from scope, tool_input.scope, or working_directory
scope = data.get("scope")
if not scope:
    ti = data.get("tool_input", {})
    if isinstance(ti, dict):
        scope = ti.get("scope")
if not scope:
    scope = data.get("working_directory")
if not scope or not isinstance(scope, str):
    scope = "unknown"

# severity
severity = data.get("severity")
if not isinstance(severity, str):
    severity = None

# deliverable_text — same ordered field search as task-completion.sh (D2).
# Order matters: `last_assistant_message` is the documented Claude Code
# SubagentStop payload field (per hooks.md / Agent SDK docs); the other
# fields are defensive fallbacks. PR #297 cycle-12 correction.
deliverable_text = None

# last_assistant_message (Claude Code SubagentStop primary field)
v = data.get("last_assistant_message")
if isinstance(v, str):
    deliverable_text = v

# tool_result.content (legacy/fallback)
if deliverable_text is None:
    tr = data.get("tool_result")
    if isinstance(tr, dict):
        content = tr.get("content")
        if isinstance(content, str):
            deliverable_text = content
        elif isinstance(content, list):
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

if deliverable_text is None:
    v = data.get("output")
    if isinstance(v, str):
        deliverable_text = v

if deliverable_text is None:
    v = data.get("result")
    if isinstance(v, str):
        deliverable_text = v

if deliverable_text is None:
    v = data.get("subagent_output")
    if isinstance(v, str):
        deliverable_text = v

if deliverable_text is None:
    v = data.get("message")
    if isinstance(v, str):
        deliverable_text = v

if deliverable_text is None:
    deliverable_text = ""

# ---- 6. Red-team trigger conditions (D4) ----
RED_TEAM_KEYWORDS = [
    "CRITICAL",
    "cross-cutting",
    "new invariant",
    "new ADR",
    "schema change",
]

force_env = os.environ.get("FORCE_RED_TEAM", "")
red_team = False
reason_parts = []

if force_env in ("1", "true"):
    red_team = True
    reason_parts.append("env:FORCE_RED_TEAM")

if severity == "critical":
    red_team = True
    reason_parts.append("severity=critical")

for kw in RED_TEAM_KEYWORDS:
    if kw in deliverable_text:
        red_team = True
        reason_parts.append("keyword:" + kw)

if red_team:
    reason = "; ".join(reason_parts) if reason_parts else "triggered"
else:
    reason = "standard-review"

# ---- 7. Emit ----
_emit(implementer, scope, red_team, reason)
sys.exit(0)
'

export _AR_REPO_ROOT="$REPO_ROOT"
_MAIN_RC=0
if command -v python3 >/dev/null 2>&1; then
    python3 -c "$_PYTHON_MAIN" || _MAIN_RC=$?
elif command -v python >/dev/null 2>&1; then
    python -c "$_PYTHON_MAIN" || _MAIN_RC=$?
fi
# Always exit 0 — advisory emission hook
exit 0
