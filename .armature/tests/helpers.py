"""
Pure factory helpers for constructing JSON payloads used in Armature hook tests.

JSON payload shapes verified against each hook's stdin parsing:
  block-dangerous-commands.sh : data.get('tool_input', {}).get('command', '')
  mark-dirty.sh               : data.get('tool_input', {}).get('file_path', '')
  block-config-changes.sh     : data.get('source', '')
  inject-context.sh           : data.get('file'|'path'|'scope'|'cwd'|'workingDirectory')
  check-required-reading.sh   : payload.get('tool_input', {}).get('file_path')
                                  or payload.get('file_path')
"""

import json


def bash_event(command: str) -> str:
    """
    JSON payload for PreToolUse(Bash).
    block-dangerous-commands.sh reads: data['tool_input']['command']
    """
    return json.dumps({"tool_input": {"command": command}})


def edit_event(file_path: str) -> str:
    """
    JSON payload for PreToolUse(Edit) / PostToolUse(Edit|Write).
    mark-dirty.sh and check-required-reading.sh read:
      data['tool_input']['file_path']
    """
    return json.dumps({"tool_input": {"file_path": file_path}})


def config_event(source: str) -> str:
    """
    JSON payload for ConfigChange.
    block-config-changes.sh reads: data['source']
    """
    return json.dumps({"source": source})


def subagent_start_event(scope: str | None = None) -> str:
    """
    JSON payload for SubagentStart.
    inject-context.sh reads one of: data['file'], data['path'],
    data['scope'], data['cwd'], data['workingDirectory'].
    scope=None emits an empty object (hook handles gracefully).
    """
    if scope is not None:
        return json.dumps({"scope": scope})
    return json.dumps({})


def subagent_stop_event(
    output: str | None = None,
    *,
    scope: str | None = None,
    severity: str | None = None,
    subagent_type: str | None = None,
    tool_result_content: str | None = None,
    extra: dict | None = None,
) -> str:
    """Build a SubagentStop hook payload JSON string."""
    payload: dict = {}
    if output is not None:
        payload["output"] = output
    if tool_result_content is not None:
        payload["tool_result"] = {"content": tool_result_content}
    if scope is not None:
        payload["scope"] = scope
    if severity is not None:
        payload["severity"] = severity
    if subagent_type is not None:
        payload["subagent_type"] = subagent_type
    if extra:
        payload.update(extra)
    return json.dumps(payload)


def stop_event() -> str:
    """Build a Stop hook payload JSON string.

    Stop events do not carry per-invocation data in the current Claude
    Code model; the payload is an empty JSON object. This factory
    exists for test-suite consistency with task_event() and
    subagent_stop_event().
    """
    return json.dumps({})


def task_event(
    prompt: str,
    tool_name: str | None = "Task",
    scope: str | None = None,
) -> str:
    """
    JSON payload for PreToolUse(Agent|Task) or SubagentStart (task-readiness.sh).

    When tool_name in ("Agent", "Task"): produces a PreToolUse payload with
      {"tool_name": <tool_name>, "tool_input": {"prompt": <prompt>}}

    When tool_name=None and scope is provided: produces a SubagentStart-shaped
      payload {"scope": <scope>, "prompt": <prompt>}  (R1 dual-mode).

    Per https://code.claude.com/docs/en/hooks.md, Claude Code's current
    subagent-delegation tool is named "Agent" with tool_input fields
    {prompt, description, subagent_type, model}. "Task" is the legacy alias
    accepted by task-readiness.sh and retained here for backwards-compat
    test coverage.

    task-readiness.sh reads:
      PreToolUse: data['tool_name'] in ("Agent","Task"), data['tool_input']['prompt']
      SubagentStart: data['scope'] present, data['prompt']
    """
    if tool_name is None and scope is not None:
        return json.dumps({"scope": scope, "prompt": prompt})
    return json.dumps({"tool_name": tool_name, "tool_input": {"prompt": prompt}})


def posttooluse_agent_event(
    response_text: str,
    *,
    prompt: str | None = None,
    subagent_type: str | None = None,
    severity: str | None = None,
    extra: dict | None = None,
) -> str:
    """Build a PostToolUse(Agent) hook payload JSON string.

    Shape per https://code.claude.com/docs/en/hooks.md:
      {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": ..., "subagent_type": ...},
        "tool_response": {"type": "text", "text": <response_text>}
      }

    This is the documented channel for surfacing a subagent's final response
    text back into the parent (orchestrator) session. task-completion.sh and
    auto-reviewer.sh both probe `tool_response.text` first and emit advisories
    wrapped in the `hookSpecificOutput.additionalContext` JSON envelope.
    """
    payload: dict = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {},
        "tool_response": {"type": "text", "text": response_text},
    }
    if prompt is not None:
        payload["tool_input"]["prompt"] = prompt
    if subagent_type is not None:
        payload["tool_input"]["subagent_type"] = subagent_type
        # Many Armature hooks also expect top-level subagent_type for
        # implementer extraction; mirror it for compatibility.
        payload["subagent_type"] = subagent_type
    if severity is not None:
        payload["severity"] = severity
    if extra:
        payload.update(extra)
    return json.dumps(payload)
