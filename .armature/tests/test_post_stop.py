"""
Tests for post-stop.sh (HOOK-003, SCHEMA-001, SCHEMA-002, REF-001, REF-002, REF-003, TASK-002 GC).

Hook behaviour (verified from source):
  - Runs multiple sequential checks; exits 1 on first FAIL.
  - Exits 0 if all checks pass.
  - Does NOT read stdin.

Check summary:
  1. check_adapter_routes(CLAUDE.md) — backtick-agents.md references must exist
  2. check_adapter_routes(CODEX.md) — same for CODEX.md; silently skipped if absent
  3. registry.yaml valid YAML → PASS; invalid → FAIL (exit 1)
  4. Uncommitted governance file changes → WARN (not FAIL), exit 0
  5. agents.md frontmatter ADR refs must resolve → FAIL (exit 1) if any missing
  6. .code-dirty present:
       - test runner found → run tests; pass → remove marker; fail → exit 1
       - test runner absent → "SKIP: No test runner detected", remove marker, exit 0
     .code-dirty absent → "SKIP: No application code changes detected"

Test isolation: each test uses setup_post_stop_repo() from conftest to build a
minimal valid baseline git repo in tmp_path, then mutates it for the specific case.
"""

import os
import subprocess
import time

import pytest


# ---------------------------------------------------------------------------
# MUST: exit 0 on clean repo (all checks PASS)
# ---------------------------------------------------------------------------

def test_clean_repo_exits_zero(run_hook, setup_post_stop_repo):
    """A fully valid baseline repo must produce exit 0."""
    repo = setup_post_stop_repo()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0


def test_clean_repo_has_pass_messages(run_hook, setup_post_stop_repo):
    """A clean repo should emit at least one PASS line."""
    repo = setup_post_stop_repo()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0
    assert "PASS" in result.stdout


# ---------------------------------------------------------------------------
# MUST: exit 1 on bad CLAUDE.md route (agents.md path that doesn't exist)
# ---------------------------------------------------------------------------

def test_bad_claude_md_route_exits_one(run_hook, setup_post_stop_repo):
    """A CLAUDE.md referencing a non-existent agents.md must exit 1."""
    repo = setup_post_stop_repo()
    # Append a backtick-referenced agents.md path that doesn't exist
    claude_md = repo / "CLAUDE.md"
    existing = claude_md.read_text()
    claude_md.write_text(
        existing + "\n| Ghost Scope | `.ghost/does-not-exist/agents.md` | ADR-0001 |\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1


def test_bad_claude_md_route_emits_fail_message(run_hook, setup_post_stop_repo):
    """The FAIL message must reference the missing agents.md path."""
    repo = setup_post_stop_repo()
    claude_md = repo / "CLAUDE.md"
    existing = claude_md.read_text()
    claude_md.write_text(
        existing + "\n| Ghost Scope | `.ghost/agents.md` | ADR-0001 |\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert ".ghost/agents.md" in result.stdout


# ---------------------------------------------------------------------------
# MUST: exit 1 on invalid registry YAML
# ---------------------------------------------------------------------------

def test_invalid_registry_yaml_exits_one(run_hook, setup_post_stop_repo):
    """Invalid YAML in registry.yaml must cause exit 1."""
    repo = setup_post_stop_repo()
    registry = repo / ".armature" / "invariants" / "registry.yaml"
    registry.write_text("invariants: [\nunterminated bracket\n")
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1


def test_invalid_registry_yaml_emits_fail_message(run_hook, setup_post_stop_repo):
    """The FAIL message must mention 'Invariant registry has invalid YAML'."""
    repo = setup_post_stop_repo()
    registry = repo / ".armature" / "invariants" / "registry.yaml"
    registry.write_text(": bad: yaml: {{{")
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "invalid YAML" in result.stdout


# ---------------------------------------------------------------------------
# MUST: exit 0 + "PASS: Invariant registry is valid YAML" on valid registry
# ---------------------------------------------------------------------------

def test_valid_registry_emits_pass_message(run_hook, setup_post_stop_repo):
    """A valid registry.yaml must produce a PASS message for registry YAML."""
    repo = setup_post_stop_repo()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0
    assert "PASS: Invariant registry is valid YAML" in result.stdout


# ---------------------------------------------------------------------------
# MUST: exit 1 on bad ADR ref in agents.md
# ---------------------------------------------------------------------------

def test_bad_adr_ref_in_agents_md_exits_one(run_hook, setup_post_stop_repo):
    """An agents.md frontmatter referencing a non-existent ADR must exit 1."""
    repo = setup_post_stop_repo()
    # Add an agents.md that references a non-existent ADR
    scope_dir = repo / "bad_scope"
    scope_dir.mkdir()
    (scope_dir / "agents.md").write_text(
        "---\nscope: bad_scope\nadrs: [ADR-9999]\n---\n\n# Bad Scope\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1


def test_bad_adr_ref_emits_fail_message(run_hook, setup_post_stop_repo):
    """The FAIL message must mention the ADR number and the agents.md file."""
    repo = setup_post_stop_repo()
    scope_dir = repo / "bad_adr_scope"
    scope_dir.mkdir()
    (scope_dir / "agents.md").write_text(
        "---\nscope: bad_adr_scope\nadrs: [ADR-8888]\n---\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "8888" in result.stdout


# ---------------------------------------------------------------------------
# MUST: .code-dirty present + no test runner → "SKIP: No test runner detected"
#       exit 0, marker REMOVED
# ---------------------------------------------------------------------------

def test_code_dirty_no_test_runner_exits_zero(run_hook, setup_post_stop_repo):
    """.code-dirty with no tests/ dir and no Makefile/package.json → exit 0."""
    repo = setup_post_stop_repo()
    marker = repo / ".armature" / ".code-dirty"
    marker.touch()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0


def test_code_dirty_no_test_runner_emits_skip(run_hook, setup_post_stop_repo):
    """.code-dirty with no test runner must emit SKIP message."""
    repo = setup_post_stop_repo()
    marker = repo / ".armature" / ".code-dirty"
    marker.touch()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0
    assert "SKIP" in result.stdout
    assert "No test runner detected" in result.stdout


def test_code_dirty_no_test_runner_preserves_marker(run_hook, setup_post_stop_repo):
    """.code-dirty marker must be preserved when post-stop finds no test runner.

    Contract: marker clearance is the responsibility of run-ci.sh (CI-001),
    which runs the configured full pipeline. post-stop.sh is a fast-feedback
    smoke pass and must not pre-empt run-ci.sh's marker lifecycle.
    """
    repo = setup_post_stop_repo()
    marker = repo / ".armature" / ".code-dirty"
    marker.touch()
    assert marker.exists()
    run_hook("post-stop.sh", "", cwd=str(repo))
    assert marker.exists(), (
        ".code-dirty must be preserved by post-stop.sh so run-ci.sh "
        "can execute the configured full pipeline before clearing it"
    )


def test_code_dirty_no_test_runner_marker_absent_before_run_stays_absent(
    run_hook, setup_post_stop_repo
):
    """When .code-dirty is absent, no marker should be created by post-stop."""
    repo = setup_post_stop_repo()
    marker = repo / ".armature" / ".code-dirty"
    assert not marker.exists()
    run_hook("post-stop.sh", "", cwd=str(repo))
    assert not marker.exists()


# ---------------------------------------------------------------------------
# MUST: .code-dirty absent → "SKIP: No application code changes detected"
# ---------------------------------------------------------------------------

def test_no_code_dirty_emits_no_app_changes_skip(run_hook, setup_post_stop_repo):
    """When .code-dirty is absent, hook must emit the 'no changes' SKIP message."""
    repo = setup_post_stop_repo()
    marker = repo / ".armature" / ".code-dirty"
    if marker.exists():
        marker.unlink()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0
    assert "SKIP" in result.stdout
    assert "No application code changes detected" in result.stdout


# ---------------------------------------------------------------------------
# SHOULD: bad CODEX.md route → exit 1
# ---------------------------------------------------------------------------

def test_bad_codex_md_route_exits_one(run_hook, setup_post_stop_repo):
    """A CODEX.md referencing a non-existent agents.md must exit 1."""
    repo = setup_post_stop_repo()
    codex_md = repo / "CODEX.md"
    existing = codex_md.read_text()
    codex_md.write_text(
        existing + "\n| Ghost Scope | `.ghost/agents.md` | ADR-0001 |\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 1
    assert "FAIL" in result.stdout


# ---------------------------------------------------------------------------
# SHOULD: CODEX.md absent → CODEX check silently skipped (exit 0 unaffected)
# ---------------------------------------------------------------------------

def test_codex_md_absent_does_not_cause_failure(run_hook, setup_post_stop_repo):
    """When CODEX.md doesn't exist, the CODEX route check must be silently skipped."""
    repo = setup_post_stop_repo()
    codex_md = repo / "CODEX.md"
    if codex_md.exists():
        codex_md.unlink()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# SHOULD: uncommitted governance file changes → WARN in output, exit 0 (not FAIL)
# ---------------------------------------------------------------------------

def test_uncommitted_governance_changes_warns_not_fails(run_hook, setup_post_stop_repo):
    """Uncommitted governance file changes must produce WARN, not FAIL (exit 0)."""
    repo = setup_post_stop_repo()
    # Modify agents.md without committing — this triggers the governance diff check
    agents_file = repo / ".armature" / "agents.md"
    agents_file.write_text(
        "---\nscope: .armature\nadrs: [ADR-0001, ADR-0002]\n---\n\n# Modified\n"
    )
    # Modify the docs/adr files to match the references (so check 5 still passes)
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    # Must exit 0 (WARN is not FAIL)
    assert result.returncode == 0
    # Must emit WARN
    assert "WARN" in result.stdout


# ---------------------------------------------------------------------------
# MUST: GC removes stale correlation file (>24h) and emits WARN
# ---------------------------------------------------------------------------

def test_gc_removes_stale_correlation_file(run_hook, setup_post_stop_repo):
    """A .json file in active-delegations/ older than 24h must be removed with a WARN log."""
    repo = setup_post_stop_repo()
    deleg_dir = repo / ".armature" / "session" / "active-delegations"
    deleg_dir.mkdir(parents=True, exist_ok=True)
    stale_file = deleg_dir / "stale_abc123.json"
    stale_file.write_text('{"prompt_hash": "abc123", "criteria_items": []}')
    # Set mtime to 25 hours ago
    stale_mtime = time.time() - 25 * 3600
    os.utime(str(stale_file), (stale_mtime, stale_mtime))

    result = run_hook("post-stop.sh", "", cwd=str(repo))

    assert result.returncode == 0
    assert not stale_file.exists(), "Stale correlation file must be removed by GC"
    assert "WARN" in result.stdout
    assert "stale_abc123.json" in result.stdout


# ---------------------------------------------------------------------------
# MUST: GC preserves recent correlation file (<1h) with no WARN about it
# ---------------------------------------------------------------------------

def test_gc_preserves_recent_correlation_file(run_hook, setup_post_stop_repo):
    """A .json file in active-delegations/ younger than 24h must not be removed."""
    repo = setup_post_stop_repo()
    deleg_dir = repo / ".armature" / "session" / "active-delegations"
    deleg_dir.mkdir(parents=True, exist_ok=True)
    recent_file = deleg_dir / "recent_def456.json"
    recent_file.write_text('{"prompt_hash": "def456", "criteria_items": []}')
    # Set mtime to 1 hour ago (well within the 24h threshold)
    recent_mtime = time.time() - 1 * 3600
    os.utime(str(recent_file), (recent_mtime, recent_mtime))

    result = run_hook("post-stop.sh", "", cwd=str(repo))

    assert result.returncode == 0
    assert recent_file.exists(), "Recent correlation file must be preserved by GC"
    assert "recent_def456.json" not in result.stdout


# ---------------------------------------------------------------------------
# MUST: GC handles empty active-delegations directory without error
# ---------------------------------------------------------------------------

def test_gc_handles_empty_active_delegations(run_hook, setup_post_stop_repo):
    """An empty active-delegations/ directory must cause no error or crash."""
    repo = setup_post_stop_repo()
    deleg_dir = repo / ".armature" / "session" / "active-delegations"
    deleg_dir.mkdir(parents=True, exist_ok=True)

    result = run_hook("post-stop.sh", "", cwd=str(repo))

    assert result.returncode == 0


# ---------------------------------------------------------------------------
# SHOULD: GC handles missing active-delegations directory without error
# ---------------------------------------------------------------------------

def test_gc_handles_missing_active_delegations(run_hook, setup_post_stop_repo):
    """When active-delegations/ does not exist at all, post-stop must exit 0."""
    repo = setup_post_stop_repo()
    deleg_dir = repo / ".armature" / "session" / "active-delegations"
    # Ensure the directory does not exist
    if deleg_dir.exists():
        import shutil
        shutil.rmtree(str(deleg_dir))

    result = run_hook("post-stop.sh", "", cwd=str(repo))

    assert result.returncode == 0


# ---------------------------------------------------------------------------
# ci.yaml schema validation tests (Step 14, CP3)
# ---------------------------------------------------------------------------

def test_post_stop_ci_yaml_valid_passes(run_hook, setup_post_stop_repo):
    """A valid ci.yaml must produce a PASS line and exit 0."""
    repo = setup_post_stop_repo()
    ci_yaml = repo / ".armature" / "ci.yaml"
    ci_yaml.write_text(
        "test:\n"
        "  command: 'python -m pytest'\n"
        "  timeout_seconds: 60\n"
        "types:\n"
        "  command: null\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0
    assert "PASS: .armature/ci.yaml schema valid" in result.stdout


def test_post_stop_ci_yaml_command_wrong_type_fails(run_hook, setup_post_stop_repo):
    """ci.yaml with command as integer must produce a FAIL line and exit non-zero."""
    repo = setup_post_stop_repo()
    ci_yaml = repo / ".armature" / "ci.yaml"
    ci_yaml.write_text(
        "test:\n"
        "  command: 42\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode != 0
    assert "FAIL" in result.stdout


def test_post_stop_ci_yaml_unknown_top_level_key_fails(run_hook, setup_post_stop_repo):
    """ci.yaml with an unknown top-level key must produce a FAIL line and exit non-zero."""
    repo = setup_post_stop_repo()
    ci_yaml = repo / ".armature" / "ci.yaml"
    ci_yaml.write_text(
        "test:\n"
        "  command: 'pytest'\n"
        "deploy:\n"
        "  command: 'make deploy'\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode != 0
    assert "FAIL" in result.stdout
    assert "unknown top-level keys" in result.stdout


def test_post_stop_ci_yaml_absent_skips(run_hook, setup_post_stop_repo):
    """When ci.yaml is absent, post-stop must emit a SKIP message and exit 0."""
    repo = setup_post_stop_repo()
    ci_yaml = repo / ".armature" / "ci.yaml"
    # Ensure ci.yaml does not exist
    if ci_yaml.exists():
        ci_yaml.unlink()
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode == 0
    assert "SKIP: .armature/ci.yaml not present" in result.stdout


def test_post_stop_ci_yaml_negative_timeout_fails(run_hook, setup_post_stop_repo):
    """ci.yaml with timeout_seconds: -1 must produce a FAIL line and exit non-zero."""
    repo = setup_post_stop_repo()
    ci_yaml = repo / ".armature" / "ci.yaml"
    ci_yaml.write_text(
        "test:\n"
        "  command: 'pytest'\n"
        "  timeout_seconds: -1\n"
    )
    result = run_hook("post-stop.sh", "", cwd=str(repo))
    assert result.returncode != 0
    assert "FAIL" in result.stdout
    assert "must be positive integer" in result.stdout
