#!/usr/bin/env bash
# Armature post-stop hook
# Runs deterministic checks after a Claude Code session or subagent completes.
# Wire to Claude Code's Stop and SubagentStop lifecycle events, or run manually
# from other runtimes such as Codex before handoff.
#
# These are mechanical checks — no LLM judgment. They validate structural
# integrity of the governance scaffold and basic code hygiene.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ARMATURE_DIR="${REPO_ROOT}/.armature"
REGISTRY="${ARMATURE_DIR}/invariants/registry.yaml"
EXIT_CODE=0

# Resolve python command (python3 preferred, fall back to python)
PYTHON=""
if command -v python3 &>/dev/null; then
  PYTHON="python3"
elif command -v python &>/dev/null; then
  PYTHON="python"
fi

echo "=== Armature Post-Stop Validation ==="

check_adapter_routes() {
  local adapter_name="$1"
  local adapter_path="$2"
  local found_refs=0
  local route_fail=0

  if [ ! -f "$adapter_path" ]; then
    return
  fi

  while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    found_refs=1
    agents_path="${REPO_ROOT}/${ref}"
    if [ ! -f "$agents_path" ]; then
      echo "FAIL: ${adapter_name} references ${ref} but file does not exist"
      EXIT_CODE=1
      route_fail=1
    fi
  done < <(grep -oEi '`[^`]*agents\.md`' "$adapter_path" | tr -d '`' | sort -u)

  if [ "$found_refs" -eq 1 ] && [ "$route_fail" -eq 0 ]; then
    echo "PASS: ${adapter_name} routing references resolve"
  else
    if [ "$found_refs" -eq 0 ]; then
      echo "SKIP: ${adapter_name} has no routed agents.md references"
    fi
  fi
}

# 1. Check that all agents.md files referenced in tool adapters exist
check_adapter_routes "CLAUDE.md" "${REPO_ROOT}/CLAUDE.md"
check_adapter_routes "CODEX.md" "${REPO_ROOT}/CODEX.md"

# 2. Check that the invariant registry is valid YAML (if python is available)
if [ -f "$REGISTRY" ]; then
  if [ -n "$PYTHON" ]; then
    export _POSTSTOP_REGISTRY="$REGISTRY"
    $PYTHON - <<'PYEOF' || EXIT_CODE=1
import yaml, sys, os
registry = os.environ["_POSTSTOP_REGISTRY"]
try:
    with open(registry) as f:
        yaml.safe_load(f)
    print('PASS: Invariant registry is valid YAML')
except Exception as e:
    print(f'FAIL: Invariant registry has invalid YAML: {e}')
    sys.exit(1)
PYEOF
  else
    echo "SKIP: No python available to validate registry YAML"
  fi
fi

# 3. Validate disciplines/triggers.yaml (if it exists and python is available)
TRIGGERS_YAML="${ARMATURE_DIR}/disciplines/triggers.yaml"
if [ -f "$TRIGGERS_YAML" ] && [ -n "$PYTHON" ]; then
  export _POSTSTOP_TRIGGERS_YAML="$TRIGGERS_YAML"
  export _POSTSTOP_DISCIPLINES_DIR="${ARMATURE_DIR}/disciplines"
  # Note: this block intentionally uses EXIT_CODE=2 (not 1) to signal a
  # blocking governance error distinct from ordinary validator failures
  # (which use EXIT_CODE=1). The disciplines validator's Python explicitly
  # uses sys.exit(2) to preserve the distinction. Callers that want a
  # uniform non-zero check should test `[ $? -ne 0 ]`; callers that want
  # to distinguish blocking from warning failures can test for the exact
  # exit code. See PR dsmedeiros/cwt-cgt#297 cycle-3 review for context.
  $PYTHON - <<'PYEOF' || EXIT_CODE=2
import yaml, sys, os, re

triggers_path = os.environ["_POSTSTOP_TRIGGERS_YAML"]
disciplines_dir = os.environ["_POSTSTOP_DISCIPLINES_DIR"]
exit_code = 0

VALID_SEVERITIES = {"critical", "high", "standard"}
VALID_COMP_MODES = {"strict", "advisory"}
VALID_TRIGGER_TYPES = {"path", "invariant", "content", "explicit"}

# Allowed discipline ID pattern: lowercase alphanumeric and hyphens only,
# must start with alphanumeric.  Prevents path traversal (LOW-3).
ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]*$')

# --- Parse triggers.yaml ---
try:
    with open(triggers_path) as f:
        data = yaml.safe_load(f)
except Exception as e:
    print(f"FAIL: disciplines/triggers.yaml has invalid YAML: {e}")
    sys.exit(2)

triggers = data.get("triggers", {}) if isinstance(data, dict) else {}
if not isinstance(triggers, dict):
    print("FAIL: disciplines/triggers.yaml: 'triggers' key must be a mapping")
    sys.exit(2)

# --- Validate each discipline ID against safe pattern before any path ops ---
for discipline_id in list(triggers.keys()):
    if not ID_PATTERN.match(str(discipline_id)):
        print(f"FAIL: triggers.yaml: discipline ID '{discipline_id}' is invalid (must match [a-z0-9][a-z0-9-]*)")
        sys.exit(2)

# --- Validate each entry ---
for discipline_id, entry in triggers.items():
    if not isinstance(entry, dict):
        print(f"FAIL: triggers.yaml: entry '{discipline_id}' must be a mapping")
        exit_code = 2
        continue

    # Referential integrity: discipline file must exist
    disc_file = os.path.join(disciplines_dir, f"{discipline_id}.md")
    if not os.path.isfile(disc_file):
        print(f"FAIL: triggers.yaml references '{discipline_id}' but .armature/disciplines/{discipline_id}.md does not exist")
        exit_code = 2

    # severity must be from allowed set
    severity = entry.get("severity", "")
    if severity not in VALID_SEVERITIES:
        print(f"FAIL: triggers.yaml '{discipline_id}': invalid severity '{severity}' (must be one of {sorted(VALID_SEVERITIES)})")
        exit_code = 2

    # composition-mode must be from allowed set
    comp_mode = entry.get("composition-mode", "")
    if comp_mode not in VALID_COMP_MODES:
        print(f"FAIL: triggers.yaml '{discipline_id}': invalid composition-mode '{comp_mode}' (must be one of {sorted(VALID_COMP_MODES)})")
        exit_code = 2

    # triggers list: each type must be from allowed set
    for trig in entry.get("triggers", []):
        if not isinstance(trig, dict):
            print(f"FAIL: triggers.yaml '{discipline_id}': trigger entry must be a mapping")
            exit_code = 2
            continue
        trig_type = trig.get("type", "")
        if trig_type not in VALID_TRIGGER_TYPES:
            print(f"FAIL: triggers.yaml '{discipline_id}': invalid trigger type '{trig_type}' (must be one of {sorted(VALID_TRIGGER_TYPES)})")
            exit_code = 2

    # Cross-check: triggers.yaml severity must match discipline frontmatter severity
    if os.path.isfile(disc_file):
        with open(disc_file) as f:
            fm_text = f.read()
        fm_severity = None
        fm_comp_mode = None
        if fm_text.startswith("---"):
            end = fm_text.find("---", 3)
            if end > 0:
                fm = fm_text[3:end]
                m = re.search(r"severity:\s*(\S+)", fm)
                if m:
                    fm_severity = m.group(1)
                m = re.search(r"composition-mode:\s*(\S+)", fm)
                if m:
                    fm_comp_mode = m.group(1)

        if fm_severity is not None and severity and severity != fm_severity:
            print(f"FAIL: triggers.yaml '{discipline_id}': severity '{severity}' does not match discipline frontmatter severity '{fm_severity}'")
            exit_code = 2

        if fm_comp_mode is not None and comp_mode and comp_mode != fm_comp_mode:
            print(f"FAIL: triggers.yaml '{discipline_id}': composition-mode '{comp_mode}' does not match discipline frontmatter composition-mode '{fm_comp_mode}'")
            exit_code = 2

# --- Validate discipline frontmatter enums (carry-forward from CP1 review) ---
for fname in os.listdir(disciplines_dir):
    if not fname.endswith(".md"):
        continue
    disc_path = os.path.join(disciplines_dir, fname)
    with open(disc_path) as f:
        text = f.read()
    if not text.startswith("---"):
        continue
    end = text.find("---", 3)
    if end <= 0:
        continue
    fm = text[3:end]
    m_sev = re.search(r"severity:\s*(\S+)", fm)
    m_comp = re.search(r"composition-mode:\s*(\S+)", fm)
    disc_id = fname[:-3]

    if m_sev:
        fm_sev = m_sev.group(1)
        if fm_sev not in VALID_SEVERITIES:
            print(f"FAIL: {fname} frontmatter: invalid severity '{fm_sev}' (must be one of {sorted(VALID_SEVERITIES)})")
            exit_code = 2

    if m_comp:
        fm_comp = m_comp.group(1)
        if fm_comp not in VALID_COMP_MODES:
            print(f"FAIL: {fname} frontmatter: invalid composition-mode '{fm_comp}' (must be one of {sorted(VALID_COMP_MODES)})")
            exit_code = 2

if exit_code == 0:
    print(f"PASS: disciplines/triggers.yaml is valid ({len(triggers)} discipline(s) checked)")
sys.exit(exit_code)
PYEOF
fi

# 4. GC stale active-delegations correlation files (TASK-002, >24h)
# Advisory-only: any Python-level failure (e.g., TOCTOU on os.listdir) must
# NOT propagate to post-stop's exit code under `set -euo pipefail`. The
# `|| true` tail ensures GC failures stay warnings.
if [ -n "$PYTHON" ]; then
  export _POSTSTOP_REPO_ROOT="$REPO_ROOT"
  $PYTHON - <<'PYEOF' || true
import os, sys, time

repo_root = os.environ["_POSTSTOP_REPO_ROOT"]
GC_THRESHOLD_SECONDS = 24 * 3600
deleg_dir = os.path.join(repo_root, ".armature", "session", "active-delegations")
if os.path.isdir(deleg_dir):
    now = time.time()
    try:
        entries = os.listdir(deleg_dir)
    except OSError as e:
        print(f"WARN: post-stop.sh could not list active-delegations/: {e}")
        sys.exit(0)
    for entry in entries:
        if not entry.endswith(".json"):
            continue
        full = os.path.join(deleg_dir, entry)
        try:
            mtime = os.path.getmtime(full)
            if now - mtime > GC_THRESHOLD_SECONDS:
                os.remove(full)
                print(f"WARN: post-stop.sh removed stale correlation file {entry} (>24h)")
        except OSError as e:
            print(f"WARN: post-stop.sh could not GC {entry}: {e}")
PYEOF
fi

# 5. Check for uncommitted governance file changes without session log entries
GOVERNANCE_FILES=$(git diff --name-only HEAD 2>/dev/null | grep -E '(agents\.md|CLAUDE\.md|CODEX\.md|registry\.yaml|invariants\.md|docs/adr/)' || true)
if [ -n "$GOVERNANCE_FILES" ]; then
  echo "WARN: Uncommitted governance file changes detected:"
  echo "$GOVERNANCE_FILES"
  echo "  Ensure these changes are logged in .armature/session/state.md"
fi

# 6. Check that no agents.md frontmatter references non-existent ADRs
if [ -n "$PYTHON" ]; then
  export _POSTSTOP_REPO_ROOT="$REPO_ROOT"
  $PYTHON - <<'PYEOF' || EXIT_CODE=1
import os, re, sys, glob

repo_root = os.environ["_POSTSTOP_REPO_ROOT"]
exit_code = 0

# Use os.walk so dot-directories (.armature/, .claude/) are traversed.
# glob.glob with ** skips directories starting with '.' by default.
agents_files = []
for dirpath, dirnames, filenames in os.walk(repo_root):
    for filename in filenames:
        if filename.lower() == 'agents.md':
            agents_files.append(os.path.join(dirpath, filename))

checked = 0
for agents_file in agents_files:
    with open(agents_file) as f:
        content = f.read()
    # Extract frontmatter
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            frontmatter = content[3:end]
            adrs = re.findall(r'ADR-(\d+)', frontmatter)
            for adr_num in adrs:
                checked += 1
                adr_dir = os.path.join(repo_root, 'docs', 'adr')
                # Try multiple naming conventions, stopping at first match:
                #   1. {num}-*         e.g. 0001-governance-as-files.md
                #   2. ADR-{num}*      e.g. ADR-0001-something.md
                #   3. *{num}*         fallback
                patterns = [
                    os.path.join(adr_dir, f'{adr_num}-*'),
                    os.path.join(adr_dir, f'ADR-{adr_num}*'),
                    os.path.join(adr_dir, f'*{adr_num}*'),
                ]
                found = any(glob.glob(p) for p in patterns)
                if not found:
                    rel_path = os.path.relpath(agents_file, repo_root)
                    print(f'FAIL: {rel_path} references ADR-{adr_num} but no matching ADR file found')
                    exit_code = 1

if exit_code == 0:
    print(f'PASS: All ADR references in agents.md frontmatter resolve ({checked} reference(s) checked across {len(agents_files)} file(s))')
sys.exit(exit_code)
PYEOF
fi

# 7. If application code was modified (dirty marker exists), run project tests
#
# Governance vs. application code classification (HOOK-003):
#   mark-dirty.sh sets .code-dirty only for files NOT under a governance prefix
#   (.armature/, .claude/, docs/, CLAUDE.md, CODEX.md, ARMATURE.md, etc.).
#   Therefore .armature/tests/ — being under .armature/ — is classified as
#   governance and does NOT trigger .code-dirty when test files are edited.
#   This is intentional: hook tests are governance artifacts, not application code.
#   The hook-tests CI job (governance.yml) is the authoritative test gate for them.
DIRTY_MARKER="${ARMATURE_DIR}/.code-dirty"
if [ -f "$DIRTY_MARKER" ]; then
  TEST_RUNNER=""
  TEST_CMD=""

  # Detection order: pytest, npm test, make test
  # Probe for a Python test layout: either repo-root tests/ or any
  # top-level package-local <pkg>/tests/ (one level deep). The latter is
  # the common multi-package layout (e.g. cwt-sim/tests/, packages/foo/tests/);
  # the original code only detected the former, causing Python edits in
  # package-local layouts to silently fall through to npm/make and never
  # validate the Python tree. .armature/tests/ is deliberately not matched
  # — it is governance, not application.
  PY_TESTS_FOUND=""
  PY_TESTS_PATH=""
  if [ -d "${REPO_ROOT}/tests" ]; then
    PY_TESTS_FOUND="repo-root"
    PY_TESTS_PATH="tests"
  else
    for top_dir in "${REPO_ROOT}"/*/; do
      # Skip framework directories that hold governance tests, not app
      case "${top_dir%/}" in
        "${REPO_ROOT}/.armature"|"${REPO_ROOT}/.claude"|"${REPO_ROOT}/.git"|"${REPO_ROOT}/node_modules") continue ;;
      esac
      if [ -d "${top_dir}tests" ]; then
        PY_TESTS_FOUND="package-local"
        # Strip the REPO_ROOT prefix and the trailing slash from top_dir,
        # then append "tests". This produces e.g. "cwt-sim/tests" so pytest
        # is scoped to the detected package and does NOT collect unrelated
        # sibling test trees (which may have collection errors or use a
        # different test framework, e.g. jest's __tests__).
        pkg_rel="${top_dir#${REPO_ROOT}/}"
        pkg_rel="${pkg_rel%/}"
        PY_TESTS_PATH="${pkg_rel}/tests"
        break
      fi
    done
  fi

  # Scope pytest to the detected tree (PY_TESTS_PATH) so we don't accidentally
  # collect unrelated trees (e.g. baselines/__tests__/ jest files) that fail
  # collection when invoked from repo root.
  if [ -n "$PY_TESTS_FOUND" ] && command -v python3 &>/dev/null; then
    TEST_RUNNER="pytest"
    TEST_CMD="python3 -m pytest ${PY_TESTS_PATH} -x --tb=short -q"
  elif [ -n "$PY_TESTS_FOUND" ] && command -v python &>/dev/null; then
    TEST_RUNNER="pytest"
    TEST_CMD="python -m pytest ${PY_TESTS_PATH} -x --tb=short -q"
  elif [ -f "${REPO_ROOT}/package.json" ] && command -v npm &>/dev/null; then
    if _POSTSTOP_PKG="${REPO_ROOT}/package.json" $PYTHON - <<'PYEOF' 2>/dev/null
import json, os, sys
pkg = os.environ["_POSTSTOP_PKG"]
d = json.load(open(pkg))
sys.exit(0 if 'test' in d.get('scripts', {}) else 1)
PYEOF
    then
      TEST_RUNNER="npm"
      TEST_CMD="npm test"
    fi
  elif [ -f "${REPO_ROOT}/Makefile" ]; then
    if grep -qE '^test[[:space:]]*:' "${REPO_ROOT}/Makefile" 2>/dev/null; then
      TEST_RUNNER="make"
      TEST_CMD="make test"
    fi
  fi

  # NOTE on marker lifecycle: post-stop.sh runs a single best-effort stack
  # (the first runner it detects) as a fast-feedback smoke test, but it does
  # NOT clear $DIRTY_MARKER. Marker clearance is the responsibility of
  # run-ci.sh, which executes the configured full pipeline (test + types +
  # lint + invariants) defined in .armature/ci.yaml. In multi-stack repos
  # (e.g., Python + TypeScript), post-stop.sh only exercises one stack and
  # would otherwise prematurely clear the marker, causing run-ci.sh to skip
  # the other stacks. Leaving the marker intact preserves CI-001 coverage.
  if [ -n "$TEST_RUNNER" ]; then
    echo "INFO: Running application tests via ${TEST_RUNNER} (smoke; full pipeline runs in run-ci.sh)..."
    if (cd "${REPO_ROOT}" && $TEST_CMD 2>&1); then
      echo "PASS: Application smoke tests passed (run-ci.sh will execute the full pipeline)"
    else
      echo "FAIL: Application smoke tests failed"
      EXIT_CODE=1
    fi
  else
    echo "SKIP: No test runner detected; deferring to run-ci.sh for marker clearance"
  fi
else
  echo "SKIP: No application code changes detected"
fi

# 8. Validate .armature/ci.yaml schema (if present and python is available)
# Catches malformed ci.yaml at governance validation time, not at runtime (D11).
# FAIL propagates via EXIT_CODE=1 — this is a structural validation, not advisory.
if [ -n "$PYTHON" ]; then
  export _POSTSTOP_CI_YAML="${ARMATURE_DIR}/ci.yaml"
  export _POSTSTOP_REPO_ROOT="$REPO_ROOT"
  $PYTHON - <<'PYEOF' || EXIT_CODE=1
import os, sys, yaml

repo_root = os.environ["_POSTSTOP_REPO_ROOT"]
ci_yaml = os.environ["_POSTSTOP_CI_YAML"]

if not os.path.isfile(ci_yaml):
    print("SKIP: .armature/ci.yaml not present (CI hook will skip)")
    sys.exit(0)

try:
    with open(ci_yaml, "rb") as f:
        raw = f.read()
    if b"\x00" in raw:
        print("FAIL: .armature/ci.yaml contains NUL bytes")
        sys.exit(1)
    data = yaml.safe_load(raw.decode("utf-8", errors="replace"))
except yaml.YAMLError as e:
    print(f"FAIL: .armature/ci.yaml is not valid YAML: {e}")
    sys.exit(1)
except OSError as e:
    print(f"FAIL: .armature/ci.yaml could not be read: {e}")
    sys.exit(1)

if data is None:
    print("PASS: .armature/ci.yaml is empty (all steps skipped)")
    sys.exit(0)

if not isinstance(data, dict):
    print(f"FAIL: .armature/ci.yaml must be a YAML mapping, got {type(data).__name__}")
    sys.exit(1)

ALLOWED_KEYS = {"test", "types", "lint", "invariants"}
unknown = set(data.keys()) - ALLOWED_KEYS
if unknown:
    print(f"FAIL: .armature/ci.yaml has unknown top-level keys: {sorted(unknown)}")
    sys.exit(1)

errors = []
for key, val in data.items():
    if not isinstance(val, dict):
        errors.append(f"{key!r} must be a mapping, got {type(val).__name__}")
        continue
    cmd = val.get("command")
    if cmd is not None and not isinstance(cmd, str):
        errors.append(f"{key}.command must be null or string, got {type(cmd).__name__}")
    tos = val.get("timeout_seconds")
    if tos is not None and (not isinstance(tos, int) or isinstance(tos, bool) or tos <= 0):
        errors.append(f"{key}.timeout_seconds must be positive integer, got {tos!r}")

if errors:
    for e in errors:
        print(f"FAIL: .armature/ci.yaml: {e}")
    sys.exit(1)

print(f"PASS: .armature/ci.yaml schema valid ({len(data)} step(s) defined)")
sys.exit(0)
PYEOF
fi

echo "=== Armature Validation Complete (exit: ${EXIT_CODE}) ==="
exit $EXIT_CODE
