"""
Tests for auto-reviewer.sh (TASK-003).

Hook behaviour (verified from source):
  - Reads stdin JSON; NUL-byte in payload → WARN stderr + fallback advisory, exit 0.
  - Invalid JSON → fallback advisory (implementer=unknown, reason=invalid-payload), exit 0.
  - Hotfix phase → ADVISORY on stderr + HTML comment still emitted, exit 0.
  - Emits <!-- AUTO-REVIEW-REQUIRED ... --> HTML comment to stdout.
  - red-team=false by default (no trigger conditions met).
  - red-team=true when: severity=="critical", deliverable contains trigger keyword,
    or FORCE_RED_TEAM=1.
  - Reason field populated descriptively when red-team=true.
  - implementer extracted from subagent_type / agent_type / subagent_name.
  - scope extracted from scope / tool_input.scope / working_directory.
  - Values sanitized: -- replaced with - -, newlines stripped, capped at 200 chars.
  - Always exits 0 — advisory emission hook.

All tests use tmp_armature so the real repo is never mutated.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

import json as _json

from .helpers import posttooluse_agent_event, subagent_stop_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_phase(tmp_armature: Path, phase: str) -> None:
    phase_file = tmp_armature / ".armature" / "session" / "phase"
    phase_file.parent.mkdir(parents=True, exist_ok=True)
    phase_file.write_text(phase, encoding="utf-8")


HTML_COMMENT_RE = re.compile(r"<!--\s*AUTO-REVIEW-REQUIRED[\s\S]*?-->", re.MULTILINE)


# ===========================================================================
# MUST tests (11)
# ===========================================================================

# ---------------------------------------------------------------------------
# MUST 1: Normal deliverable → HTML comment present in stdout, exit 0
# ---------------------------------------------------------------------------

def test_normal_deliverable_emits_html_comment(run_hook, tmp_armature):
    """Normal deliverable → <!-- AUTO-REVIEW-REQUIRED ... --> present in stdout, exit 0."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="The implementation is complete."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "<!-- AUTO-REVIEW-REQUIRED" in result.stdout


# ---------------------------------------------------------------------------
# MUST 2: red-team=false when no trigger conditions met
# ---------------------------------------------------------------------------

def test_no_trigger_red_team_false(run_hook, tmp_armature):
    """No trigger conditions → red-team=false in emitted comment."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Standard implementation complete."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=false" in result.stdout


# ---------------------------------------------------------------------------
# MUST 3: red-team=true when payload severity == "critical"
# ---------------------------------------------------------------------------

def test_severity_critical_triggers_red_team(run_hook, tmp_armature):
    """Payload severity=critical → red-team=true."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Changes made.", severity="critical"),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout


# ---------------------------------------------------------------------------
# MUST 4: red-team=true when deliverable text contains "CRITICAL"
# ---------------------------------------------------------------------------

def test_keyword_CRITICAL_triggers_red_team(run_hook, tmp_armature):
    """Deliverable containing "CRITICAL" → red-team=true."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="This is a CRITICAL security fix."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout


# ---------------------------------------------------------------------------
# MUST 5: red-team=true when deliverable text contains "cross-cutting"
# ---------------------------------------------------------------------------

def test_keyword_cross_cutting_triggers_red_team(run_hook, tmp_armature):
    """Deliverable containing "cross-cutting" → red-team=true."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="This is a cross-cutting change to all layers."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout


# ---------------------------------------------------------------------------
# MUST 6: red-team=true when FORCE_RED_TEAM=1 env set
# ---------------------------------------------------------------------------

def test_force_red_team_env_triggers_red_team(run_hook, tmp_armature):
    """FORCE_RED_TEAM=1 → red-team=true regardless of payload content."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Routine change."),
        env_overrides={"FORCE_RED_TEAM": "1"},
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout


# ---------------------------------------------------------------------------
# MUST 7: HTML comment is syntactically well-formed (starts <!-- ends -->)
# ---------------------------------------------------------------------------

def test_html_comment_well_formed(run_hook, tmp_armature):
    """HTML comment must start with <!-- and end with --> (well-formed)."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Implementation done."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    stdout = result.stdout
    assert "<!--" in stdout
    assert "-->" in stdout
    # Starts before ends
    assert stdout.index("<!--") < stdout.index("-->")


# ---------------------------------------------------------------------------
# MUST 8: implementer field present in comment
# ---------------------------------------------------------------------------

def test_implementer_field_present(run_hook, tmp_armature):
    """The implementer= field must be present in the emitted HTML comment."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Done.", subagent_type="specification-impl"),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "implementer=" in result.stdout


# ---------------------------------------------------------------------------
# MUST 9: scope field present in comment
# ---------------------------------------------------------------------------

def test_scope_field_present(run_hook, tmp_armature):
    """The scope= field must be present in the emitted HTML comment."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Done.", scope=".armature"),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "scope=" in result.stdout


# ---------------------------------------------------------------------------
# MUST 10: Invalid JSON stdin → fallback advisory still emitted, exit 0
# ---------------------------------------------------------------------------

def test_invalid_json_emits_fallback_advisory(run_hook, tmp_armature):
    """Invalid JSON → fallback advisory with implementer=unknown, reason=invalid-payload, exit 0."""
    result = run_hook(
        "auto-reviewer.sh",
        "{{this is not json}}",
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "<!-- AUTO-REVIEW-REQUIRED" in result.stdout
    assert "implementer=unknown" in result.stdout
    assert "invalid-payload" in result.stdout


# ---------------------------------------------------------------------------
# MUST 11: Hotfix phase → exit 0 + ADVISORY bypass on stderr + HTML comment still emitted
# ---------------------------------------------------------------------------

def test_hotfix_phase_emits_advisory_and_html_comment(run_hook, tmp_armature):
    """Hotfix phase → ADVISORY on stderr AND HTML comment still emitted to stdout."""
    _write_phase(tmp_armature, "Hotfix")
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Hotfix implementation."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    # Advisory on stderr
    assert "ADVISORY" in result.stderr
    assert "Hotfix" in result.stderr
    # HTML comment still emitted
    assert "<!-- AUTO-REVIEW-REQUIRED" in result.stdout


# ===========================================================================
# SHOULD tests (5)
# ===========================================================================

# ---------------------------------------------------------------------------
# SHOULD 12: NUL byte in payload → advisory emitted with WARN, exit 0
# ---------------------------------------------------------------------------

def test_should_12_nul_byte_emits_warn_and_advisory(repo_root, tmp_armature):
    """NUL byte in stdin → WARN on stderr + fallback advisory comment, exit 0."""
    bash_bin = shutil.which("bash")
    if bash_bin is None:
        pytest.skip("bash not available")

    hook_path = repo_root / ".armature" / "hooks" / "auto-reviewer.sh"
    payload = b'{"output":"implementation\x00complete"}'

    result = subprocess.run(
        [bash_bin, str(hook_path)],
        input=payload,
        capture_output=True,
        cwd=str(tmp_armature),
        timeout=10,
    )
    assert result.returncode == 0
    stderr = result.stderr.decode("utf-8", errors="replace")
    stdout = result.stdout.decode("utf-8", errors="replace")
    assert "WARN" in stderr
    assert "<!-- AUTO-REVIEW-REQUIRED" in stdout


# ---------------------------------------------------------------------------
# SHOULD 13: red-team=true when deliverable contains "new invariant"
# ---------------------------------------------------------------------------

def test_should_13_keyword_new_invariant_triggers_red_team(run_hook, tmp_armature):
    """Deliverable containing "new invariant" → red-team=true."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Adding a new invariant to the registry."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout


# ---------------------------------------------------------------------------
# SHOULD 14: red-team=true when deliverable contains "schema change"
# ---------------------------------------------------------------------------

def test_should_14_keyword_schema_change_triggers_red_team(run_hook, tmp_armature):
    """Deliverable containing "schema change" → red-team=true."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="This schema change updates the registry format."),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout


# ---------------------------------------------------------------------------
# SHOULD 15: reason field populated descriptively when red-team triggered
# ---------------------------------------------------------------------------

def test_should_15_reason_field_descriptive_on_red_team(run_hook, tmp_armature):
    """When red-team=true, reason field is not just 'standard-review'."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="CRITICAL security update applied.", severity="critical"),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "red-team=true" in result.stdout
    # reason must not be "standard-review" when triggered
    assert "reason=standard-review" not in result.stdout
    # reason should mention something descriptive
    assert "reason=" in result.stdout
    # Extract reason line
    for line in result.stdout.splitlines():
        if line.startswith("reason="):
            reason_val = line[len("reason="):]
            assert reason_val != "standard-review", (
                f"reason must be descriptive when triggered, got: {reason_val}"
            )
            break


# ---------------------------------------------------------------------------
# SHOULD 16: Comment is parseable by regex (implementer-consumption smoke)
# ---------------------------------------------------------------------------

def test_should_16_comment_parseable_by_regex(run_hook, tmp_armature):
    """HTML comment matches <!-- AUTO-REVIEW-REQUIRED[\\s\\S]*?--> regex."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Implementation complete.", scope=".armature",
                            subagent_type="specification-impl"),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    match = re.search(r"<!--\s*AUTO-REVIEW-REQUIRED[\s\S]*?-->", result.stdout)
    assert match is not None, (
        f"stdout did not match AUTO-REVIEW-REQUIRED regex. stdout={result.stdout!r}"
    )


# ---------------------------------------------------------------------------
# Cycle-16: PostToolUse(Agent) payload — JSON envelope on stdout
# ---------------------------------------------------------------------------

def _additional_context_from(stdout: str) -> str:
    """Parse stdout as JSON and return hookSpecificOutput.additionalContext."""
    envelope = _json.loads(stdout)
    return envelope["hookSpecificOutput"]["additionalContext"]


def test_posttooluse_agent_emits_json_envelope(run_hook, tmp_armature):
    """When fired on PostToolUse(Agent), stdout is a JSON envelope with
    hookSpecificOutput.hookEventName == 'PostToolUse' and the AUTO-REVIEW-
    REQUIRED HTML comment carried in additionalContext."""
    result = run_hook(
        "auto-reviewer.sh",
        posttooluse_agent_event(
            response_text="Implementation complete.",
            prompt="Add the foo feature.",
            subagent_type="specification-impl",
        ),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    envelope = _json.loads(result.stdout)
    assert envelope["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    ctx = envelope["hookSpecificOutput"]["additionalContext"]
    assert "<!-- AUTO-REVIEW-REQUIRED" in ctx
    assert "implementer=specification-impl" in ctx
    assert "red-team=false" in ctx


def test_posttooluse_agent_probes_tool_response_text_for_red_team(
    run_hook, tmp_armature
):
    """Red-team keywords found in tool_response.text trigger red-team=true.
    Verifies the new probe order picks up the PostToolUse(Agent) primary
    field instead of falling through to legacy fallbacks."""
    result = run_hook(
        "auto-reviewer.sh",
        posttooluse_agent_event(
            response_text="Introduced a CRITICAL invariant change.",
            subagent_type="specification-impl",
        ),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    ctx = _additional_context_from(result.stdout)
    assert "red-team=true" in ctx


def test_legacy_subagent_stop_still_emits_plain_html_comment(
    run_hook, tmp_armature
):
    """SubagentStop payload (no hook_event_name field) drains the buffer
    plain — no JSON envelope wrapping. Preserves backwards-compat for
    older installs and direct test invocation."""
    result = run_hook(
        "auto-reviewer.sh",
        subagent_stop_event(output="Done.", subagent_type="specification-impl"),
        cwd=str(tmp_armature),
    )
    assert result.returncode == 0
    assert "<!-- AUTO-REVIEW-REQUIRED" in result.stdout
    # Should NOT be a JSON envelope
    stripped = result.stdout.strip()
    assert not stripped.startswith("{"), (
        f"SubagentStop output should be plain, not JSON-wrapped. stdout={stripped!r}"
    )
