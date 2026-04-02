#!/usr/bin/env bash
# Armature post-stop hook
# Runs deterministic checks after a Claude Code session or subagent completes.
# Wire to Claude Code's Stop and SubagentStop lifecycle events.
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

# 1. Check that all agents.md files referenced in CLAUDE.md exist
if [ -f "${REPO_ROOT}/CLAUDE.md" ]; then
  while IFS= read -r ref; do
    agents_path="${REPO_ROOT}/${ref}"
    if [ ! -f "$agents_path" ]; then
      echo "FAIL: CLAUDE.md references ${ref} but file does not exist"
      EXIT_CODE=1
    fi
  done < <(grep -oP '`[^`]*agents\.md`' "${REPO_ROOT}/CLAUDE.md" | tr -d '`' | sort -u)
fi

# 2. Check that the invariant registry is valid YAML (if python is available)
if [ -f "$REGISTRY" ]; then
  if [ -n "$PYTHON" ]; then
    $PYTHON -c "
import yaml, sys
try:
    with open('${REGISTRY}') as f:
        yaml.safe_load(f)
    print('PASS: Invariant registry is valid YAML')
except Exception as e:
    print(f'FAIL: Invariant registry has invalid YAML: {e}')
    sys.exit(1)
" || EXIT_CODE=1
  else
    echo "SKIP: No python available to validate registry YAML"
  fi
fi

# 3. Check for uncommitted governance file changes without session log entries
GOVERNANCE_FILES=$(git diff --name-only HEAD 2>/dev/null | grep -E '(agents\.md|CLAUDE\.md|registry\.yaml|invariants\.md|docs/adr/)' || true)
if [ -n "$GOVERNANCE_FILES" ]; then
  echo "WARN: Uncommitted governance file changes detected:"
  echo "$GOVERNANCE_FILES"
  echo "  Ensure these changes are logged in .armature/session/state.md"
fi

# 4. Check that no agents.md frontmatter references non-existent ADRs
if [ -n "$PYTHON" ]; then
  $PYTHON -c "
import os, re, sys, glob

repo_root = '${REPO_ROOT}'
exit_code = 0

for agents_file in glob.glob(os.path.join(repo_root, '**', 'agents.md'), recursive=True):
    with open(agents_file) as f:
        content = f.read()
    # Extract frontmatter
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            frontmatter = content[3:end]
            adrs = re.findall(r'ADR-(\d+)', frontmatter)
            for adr_num in adrs:
                # Look for any ADR file matching this number
                adr_pattern = os.path.join(repo_root, 'docs', 'adr', f'ADR-{adr_num}*')
                if not glob.glob(adr_pattern):
                    rel_path = os.path.relpath(agents_file, repo_root)
                    print(f'FAIL: {rel_path} references ADR-{adr_num} but no matching ADR file found')
                    exit_code = 1

if exit_code == 0:
    print('PASS: All ADR references in agents.md frontmatter resolve')
sys.exit(exit_code)
" || EXIT_CODE=1
fi

echo "=== Armature Validation Complete (exit: ${EXIT_CODE}) ==="
exit $EXIT_CODE
