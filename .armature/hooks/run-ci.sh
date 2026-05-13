#!/usr/bin/env bash
# Armature Stop hook — run-ci.sh
# Event: Stop
# Invariant: CI-001
#
# Behavior:
#   Reads .armature/ci.yaml; executes configured steps in order
#   (invariants -> test -> types -> lint) via Python subprocess with
#   per-step timeout. Advisory mode by default (exit 0 even on failure).
#   ARMATURE_CI_BLOCK=1 env shifts to fail-closed (exit 2 on any failure).
#
# Trust model:
#   Commands in ci.yaml are trusted as configured by the repo owner.
#   This hook does NOT sanitize command content. Repo write access is the
#   trust boundary. The threat model is equivalent to package.json scripts.
#   Shell injection via ci.yaml is intentional (commands run as bash -c);
#   list-typed command values are rejected (only strings are executed).
#
# Escape valve:
#   ARMATURE_CI_BLOCK=1 -> exit 2 on any step failure (fail-closed mode)
#
# Known limitations:
#   Shell injection via ci.yaml command values is intentional by design.
#   Commands run as bash -c <command> where <command> comes from the
#   YAML-parsed string value. List-typed commands are rejected gracefully.
#   No eval usage anywhere in this hook.
#
# Exit codes:
#   0  always (advisory mode default)
#   2  only when ARMATURE_CI_BLOCK=1 and at least one step failed
#
# Skip conditions (checked in order):
#   1. Phase == "Hotfix" (exact ASCII match) -> exit 0 + ADVISORY
#   2. .armature/.code-dirty absent -> exit 0 + ADVISORY
#   3. .armature/session/skip-ci present -> exit 0 + ADVISORY
#   4. .armature/ci.yaml absent -> exit 0 + ADVISORY
#   5. Python unavailable -> exit 0 + ADVISORY
#
# Dirty marker:
#   Removed on full pipeline success; preserved on any failure.
#
# Cross-platform:
#   Uses Python subprocess.run(timeout=N) not GNU timeout shell command.
#   Compatible with Git Bash on Windows and bash on Linux.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve Python interpreter (python3 preferred, python fallback).
# ---------------------------------------------------------------------------
PYTHON=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

if [ -z "$PYTHON" ]; then
    echo "ADVISORY: Python not available; CI-001 skipped" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# Resolve REPO_ROOT via git, fall back to current directory.
# ---------------------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# ---------------------------------------------------------------------------
# Hotfix bypass — Python inline block (heredoc, NOT command substitution).
# ASCII-only strip (M3 lesson: Unicode whitespace bypass via .strip() without
# args is a known attack vector).
# ---------------------------------------------------------------------------
export CI_REPO_ROOT="$REPO_ROOT"

IS_HOTFIX="$("$PYTHON" - <<'PYEOF'
import os
p = os.path.join(os.environ.get("CI_REPO_ROOT", "."), ".armature", "session", "phase")
try:
    with open(p, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="replace").strip(" \t\n\r")
    print("yes" if text == "Hotfix" else "no")
except OSError:
    print("no")
PYEOF
)"

if [ "$IS_HOTFIX" = "yes" ]; then
    echo "ADVISORY: Hotfix phase active — CI-001 bypass per CI-001" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# Dirty marker check: skip if no application code has changed.
# ---------------------------------------------------------------------------
DIRTY_MARKER="${REPO_ROOT}/.armature/.code-dirty"
if [ ! -f "$DIRTY_MARKER" ]; then
    echo "ADVISORY: No dirty marker found; skipping CI run" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# skip-ci marker check: allow manual bypass via sentinel file.
# ---------------------------------------------------------------------------
SKIP_CI_MARKER="${REPO_ROOT}/.armature/session/skip-ci"
if [ -f "$SKIP_CI_MARKER" ]; then
    echo "ADVISORY: skip-ci marker present; CI bypassed" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# ci.yaml existence check.
# ---------------------------------------------------------------------------
CI_YAML="${REPO_ROOT}/.armature/ci.yaml"
if [ ! -f "$CI_YAML" ]; then
    echo "ADVISORY: .armature/ci.yaml not found; skipping CI run" >&2
    exit 0
fi

# ---------------------------------------------------------------------------
# Main CI execution block — Python inline.
#
# Capture exit code with || pattern so set -e doesn't terminate the hook
# before we can propagate the exit code. ARMATURE_CI_BLOCK=1 causes
# sys.exit(2) when any step fails; otherwise sys.exit(0).
# ---------------------------------------------------------------------------
export CI_YAML_PATH="$CI_YAML"
export CI_DIRTY_MARKER="$DIRTY_MARKER"

MAIN_RC=0
"$PYTHON" - <<'PYEOF' || MAIN_RC=$?
import io
import os
import subprocess
import sys
import yaml

# Reconfigure stdout/stderr to use errors="replace" so that replacement
# characters (U+FFFD) from non-UTF8 subprocess output do not cause a
# UnicodeEncodeError when written to a platform stream whose codec
# (e.g. cp1252 on Windows) cannot encode U+FFFD — see m7-plan.md A5b.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding=sys.stdout.encoding or "utf-8", errors="replace"
    )
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding=sys.stderr.encoding or "utf-8", errors="replace"
    )

CI_YAML_PATH = os.environ.get("CI_YAML_PATH", "")
CI_DIRTY_MARKER = os.environ.get("CI_DIRTY_MARKER", "")
ARMATURE_CI_BLOCK = os.environ.get("ARMATURE_CI_BLOCK", "")

# Default timeouts per step (seconds)
DEFAULTS = {
    "invariants": 120,
    "test": 600,
    "types": 120,
    "lint": 120,
}

# Execution order per D2
STEP_ORDER = ["invariants", "test", "types", "lint"]

# ---- Read ci.yaml bytes; check for NUL bytes before decode ----
try:
    with open(CI_YAML_PATH, "rb") as fh:
        raw = fh.read()
except OSError as exc:
    sys.stderr.write("ADVISORY: Could not read .armature/ci.yaml: {}\n".format(exc))
    sys.exit(0)

if b"\x00" in raw:
    sys.stderr.write("ADVISORY: .armature/ci.yaml contains NUL bytes; skipping CI run\n")
    sys.exit(0)

# ---- Parse YAML ----
try:
    ci = yaml.safe_load(raw.decode("utf-8", errors="replace"))
except yaml.YAMLError as exc:
    sys.stderr.write("ADVISORY: ci.yaml parse error: {}; skipping CI run\n".format(exc))
    sys.exit(0)

if not isinstance(ci, dict):
    # Empty file or non-mapping YAML
    if ci is None:
        sys.stderr.write("ADVISORY: .armature/ci.yaml is empty; skipping CI run\n")
    else:
        sys.stderr.write("ADVISORY: .armature/ci.yaml must be a YAML mapping; skipping CI run\n")
    sys.exit(0)

# ---- Execute steps in order ----
passed = 0
skipped = 0
failed = 0
failed_steps = []

for step_name in STEP_ORDER:
    step_config = ci.get(step_name, {})

    # Resolve command
    if isinstance(step_config, dict):
        command = step_config.get("command")
    elif step_config is None:
        command = None
    else:
        # step_config is a scalar or other non-dict type
        command = None

    if command is None:
        print("SKIP: {}".format(step_name))
        skipped += 1
        continue

    if not isinstance(command, str):
        sys.stderr.write(
            "WARN: {} command must be string, got {}; skipping\n".format(
                step_name, type(command).__name__
            )
        )
        skipped += 1
        continue

    if command.strip() == "":
        print("SKIP: {} (empty command)".format(step_name))
        skipped += 1
        continue

    # Resolve timeout
    timeout_val = None
    if isinstance(step_config, dict):
        timeout_val = step_config.get("timeout_seconds")
    if not isinstance(timeout_val, int) or timeout_val <= 0:
        timeout_val = DEFAULTS.get(step_name, 120)

    # Execute via bash -c (trust model: command from YAML, no secondary sanitization)
    try:
        proc = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            timeout=timeout_val,
        )
        # Decode bytes manually with errors="replace" — see m7-plan.md A5b
        # (subprocess text=True uses locale codec; cp1252 on Windows, ascii on
        # LANG=C Linux; non-UTF8 bytes from CI steps would crash the reader
        # thread and leak a traceback to the orchestrator transcript).
        captured_stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
        captured_stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
        if proc.returncode == 0:
            print("PASS: {}".format(step_name))
            passed += 1
        else:
            sys.stderr.write(
                "FAIL: {} exited {}\n".format(step_name, proc.returncode)
            )
            # Emit captured output (truncated to first 200 lines)
            if captured_stdout:
                lines = captured_stdout.splitlines()
                for line in lines[:200]:
                    sys.stdout.write(line + "\n")
                if len(lines) > 200:
                    sys.stdout.write("[... {} lines truncated ...]\n".format(len(lines) - 200))
            if captured_stderr:
                lines = captured_stderr.splitlines()
                for line in lines[:200]:
                    sys.stderr.write(line + "\n")
                if len(lines) > 200:
                    sys.stderr.write("[... {} lines truncated ...]\n".format(len(lines) - 200))
            failed += 1
            failed_steps.append(step_name)
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "FAIL: {} timed out after {}s\n".format(step_name, timeout_val)
        )
        failed += 1
        failed_steps.append(step_name)
    except subprocess.SubprocessError as exc:
        sys.stderr.write(
            "FAIL: {} subprocess error: {}\n".format(step_name, exc)
        )
        failed += 1
        failed_steps.append(step_name)

# ---- Summary ----
print("Summary: passed={} skipped={} failed={}".format(passed, skipped, failed))

# ---- Dirty marker management ----
if failed == 0 and CI_DIRTY_MARKER:
    try:
        os.remove(CI_DIRTY_MARKER)
    except OSError:
        pass  # Marker already gone; not an error

# ---- Fail-closed mode ----
if failed > 0 and ARMATURE_CI_BLOCK == "1":
    sys.exit(2)

sys.exit(0)
PYEOF

# Propagate block mode exit code; advisory mode always exits 0
if [ "$MAIN_RC" -eq 2 ]; then
    exit 2
fi
exit 0
