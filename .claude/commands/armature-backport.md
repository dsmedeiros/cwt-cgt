---
description: >
  Update a project's framework-generic Armature files from the canonical
  Armature repository without overwriting project-specific files.
  Use when the canonical Armature has been updated and you want to
  pull improvements into an existing project.
argument-hint: "<path-to-canonical-armature-repo>"
---

# Armature Backport

You are the orchestrator. A newer version of the Armature framework is available and needs to be backported into this project. Follow this protocol to update framework-generic files while preserving all project-specific content.

## Source: $ARGUMENTS

If no argument is provided, ask the human for the path to the canonical Armature repository (local path or git clone URL).

## Framework-Generic vs. Project-Specific

**Framework-generic (will be updated):**
- `.armature/ARMATURE.md` — the specification
- `.armature/personas/orchestrator.md` — orchestrator persona
- `.armature/personas/reviewer.md` — reviewer persona
- `.armature/personas/reviewer-redteam.md` — red team reviewer persona
- `.armature/personas/planner.md` — planner persona
- `.armature/templates/` — all template files (adr.md.tmpl, agents.md.tmpl, persona.md.tmpl)
- `.armature/hooks/post-stop.sh` — validation hook
- `.claude/commands/armature-init.md` — init protocol
- `.claude/commands/armature-extend.md` — extend protocol
- `.claude/commands/armature-update.md` — update protocol
- `.claude/commands/armature-backport.md` — this file (self-update)
- `.claude/commands/checkpoint.md` — checkpoint protocol
- `.claude/agents/reviewer.md` — reviewer subagent wiring
- `.claude/agents/reviewer-redteam.md` — red team subagent wiring
- `.claude/agents/planner.md` — planner subagent wiring

**Project-specific (NEVER overwritten):**
- `.armature/config.yaml` — project metadata and topology
- `.armature/invariants/registry.yaml` — project invariant registry
- `.armature/invariants/invariants.md` — project invariant descriptions
- `.armature/personas/implementers/*.md` — component implementer personas
- `.armature/journal.md` — governance journal
- `.armature/session/` — session state
- `.armature/reviews/` — review verdicts
- `.claude/agents/*-impl.md` — implementer subagent wiring
- `CLAUDE.md` — project orchestrator entry point
- `agents.md` — project root directives
- `*/agents.md` — scoped directives
- `docs/adr/*.md` — project ADRs

## Protocol

### Step 1: Read Source Version

Read the canonical Armature repo's `.armature/config.yaml` to get its `armature-version`.
Read this project's `.armature/config.yaml` to get the current `armature-version`.

Report to the human: "Upgrading Armature from {current} to {canonical}."

If versions are the same, ask the human whether to proceed anyway (there may be changes within the same version).

### Step 2: Diff Framework Files

For each framework-generic file listed above:
1. Read the canonical version
2. Read the project's current version
3. Note whether the file is: identical, modified, new (exists in canonical but not in project), or missing (exists in project but not in canonical)

Present a summary to the human:
- Files that will be updated (with brief description of what changed)
- New files that will be added
- Files that are already current (no changes needed)

### Step 3: Check for Project-Specific Modifications

Before overwriting, check whether any framework-generic files in the project have been locally modified (e.g., the project customized orchestrator.md beyond the standard persona). If so, warn the human:

"These framework files have local modifications that will be lost:
- {file}: {description of local changes}

Should I proceed, or do you want to merge these manually?"

### Step 4: Apply Updates

With human confirmation:
1. Copy each modified/new framework-generic file from the canonical source to the project
2. Do NOT touch any project-specific file

### Step 5: Schema Migration

Check whether the canonical ARMATURE.md introduces new schema fields (config.yaml, agents.md frontmatter, registry.yaml). If so:
1. List the new fields for the human
2. Add new fields to the project's config.yaml with default values
3. Note which agents.md files need frontmatter updates (but do not auto-update — list them for the human)

### Step 6: Update Version

Update the `armature-version` field in the project's `.armature/config.yaml` to match the canonical version.

### Step 7: Verify

Run `bash .armature/hooks/post-stop.sh` to confirm governance integrity after the backport.

If validation fails:
- Report which checks failed
- These are likely due to new cross-reference requirements introduced by the updated spec
- Help the human resolve each failure

### Step 8: Log

Append to `.armature/journal.md`:
```markdown
### {YYYY-MM-DD HH:MM} — backport
Armature framework updated from {old-version} to {new-version}.
Source: {canonical-repo-path}
Files updated: {count}
New files added: {list or "none"}
Schema migrations: {list or "none"}
Validation: {PASS or list of issues}
```

Commit with message: `armature: backport framework from {old-version} to {new-version}`
