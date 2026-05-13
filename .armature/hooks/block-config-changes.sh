#!/usr/bin/env bash
# Armature ConfigChange hook — prevents agents from modifying Claude Code
# configuration that could alter their own governance constraints.
# Wire to Claude Code's ConfigChange lifecycle event.
#
# Stdin: JSON object with a top-level "source" field identifying which
#        configuration store is being modified.
# Exit 2  = block the configuration change
# Exit 0  = allow the configuration change
#
# Blocked sources : user_settings, project_settings, local_settings, skills
# Allowed sources : policy_settings

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# ---------------------------------------------------------------------------
# Parse the source field from stdin JSON.
#
# Security: NUL bytes (0x00) MUST be rejected before any decode. Bash command
# substitution silently strips NUL bytes, so a payload where NUL corrupts the
# JSON causes SOURCE to be empty, and the empty branch fails open (allowing
# the change). This is lesson L001 in .armature/lessons.yaml — same bypass
# class fixed in block-dangerous-commands.sh.
#
# This is a fail-closed security gate, so NUL byte detection triggers BLOCK
# (exit 2), not fail-open with WARN.
# ---------------------------------------------------------------------------
PYTHON=""
if command -v python3 &>/dev/null; then PYTHON="python3"; elif command -v python &>/dev/null; then PYTHON="python"; fi

SOURCE=""
if [ -n "$PYTHON" ]; then
  SOURCE="$("$PYTHON" -c "$(cat <<'PYEOF'
import json, sys
raw = sys.stdin.buffer.read()
# L001: reject NUL bytes before any decode — bash strips them, masking bypass.
# This is a fail-closed security gate, so NUL-byte payloads BLOCK.
if b'\x00' in raw:
    sys.stderr.write('BLOCK: NUL bytes in ConfigChange payload (potential bypass attempt per L001)\n')
    sys.exit(2)
text = raw.decode('utf-8', errors='replace')
try:
    data = json.loads(text)
    print(data.get('source', ''))
except Exception:
    pass
PYEOF
)")"
  py_rc=$?
  if [ "$py_rc" -eq 2 ]; then
    # Python raised the NUL-byte BLOCK; propagate exit 2.
    exit 2
  fi
else
  # Python unavailable. Fail-CLOSED: refuse to evaluate without the NUL-byte
  # guard active; emit ADVISORY and allow.
  echo "ADVISORY: block-config-changes.sh requires python3 or python; allowing without check" >&2
  exit 0
fi

# ---------------------------------------------------------------------------
# Helper: emit block message and exit 2
# ---------------------------------------------------------------------------
block() {
  local source_value="$1"
  echo "BLOCK: Agents cannot modify governance configuration via ${source_value}" >&2
  exit 2
}

# ---------------------------------------------------------------------------
# Evaluate the source value (normalise to lowercase for case-insensitive match)
# ---------------------------------------------------------------------------
SOURCE_LOWER="${SOURCE,,}"
case "$SOURCE_LOWER" in
  user_settings|project_settings|local_settings|skills)
    block "$SOURCE"
    ;;
  policy_settings)
    # Explicitly allowed — fall through to exit 0
    ;;
  "")
    # Could not parse source; fail open to avoid false positives
    echo "WARN: block-config-changes.sh could not parse 'source' from stdin; allowing" >&2
    ;;
  *)
    # Unknown source — allow but warn so novel sources are visible in logs
    echo "WARN: block-config-changes.sh encountered unknown source '${SOURCE}'; allowing" >&2
    ;;
esac

exit 0
