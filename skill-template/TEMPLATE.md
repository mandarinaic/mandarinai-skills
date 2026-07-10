---
name: skill-template
description: Template skill — copy this directory to start a new skill. Replace this description with WHAT the skill does + WHEN to use it, including the exact trigger phrases users would type (English and Chinese), e.g. "Use when the user asks for X, mentions 'Y', '做成Z'".
---

# Skill Template

> Copy `skill-template/` to `skills/<your-skill-name>/`, rename this file to
> `SKILL.md` (it ships as TEMPLATE.md so skill installers don't pick it up),
> set `name:` to match the directory, rewrite the description, then delete the
> parts you don't need. Delete this blockquote.

## What this skill does

One short paragraph: the artifact or outcome this skill produces, and what it does NOT do
(point to a different skill for out-of-scope requests).

## Workflow

### Step 1 · Clarify requirements (before doing anything)

If the user gave complete inputs, skip to Step 2. Otherwise ask the 2-3 questions whose
answers would change the structure of the output. Do not start on guesses.

**Environment adaptation** (keep this section — it is what makes the skill portable):

- **Claude Code**: may use AskUserQuestion for clarification; Read/Write/Bash for files.
- **Codex / Gemini CLI**: ask in plain conversation; do not assume Claude-specific tools
  exist. If a tool is unavailable, fall back to shell commands.

### Step 2 · Produce the output

Concrete, ordered instructions. Prefer:

- Deterministic work → a script in `scripts/` (validation, conversion, screenshots).
- Starting points → a template in `assets/` that gets copied and filled in.
- Deep knowledge (style guides, spec tables, recipes) → files in `references/`,
  loaded only when needed. Tell the agent exactly which file to read for which case:
  e.g. "For theme colors, read `references/themes.md`."

### Step 3 · Verify

How the agent checks its own work before declaring done (run the validator script,
open the output, check a checklist in `references/`).

## Constraints

- Hard rules the agent must never break (output location, file naming, what not to touch).
