---
name: new-skill
description: How to write a new SKILL.md in this repo, or fix an existing skill's frontmatter.
when_to_use: Creating a skill under .agents/skills, or editing a skill's description or when_to_use.
---

# Writing a skill

## Applies to

Creating `.agents/skills/<name>/SKILL.md`, or editing an existing skill's
`description` or `when_to_use`. Not for editing a skill's body alone.

## The rule

Three places, three jobs:

| Where | Holds | Who sees it |
|---|---|---|
| `description` | **One sentence: what the skill does or is for.** No file paths, no parenthetical scope lists, no trigger conditions. | Every harness's skill listing |
| `when_to_use` (optional) | Short trigger phrases a user or task would actually say -- one line. | Claude Code only, appended to `description` |
| `## Applies to` (right after the H1) | The full trigger detail: triggers, non-triggers, exceptions. | Anyone who loaded the skill |

The listing a session sees shows only the frontmatter, and that is all it
has when deciding whether to load a skill: scope caveats in `description`
read as noise there. Other harnesses ignore `when_to_use`, so nothing may
live *only* there -- `## Applies to` stays the complete trigger list. The
body loads in full once the skill fires, so detail there costs nothing.

- Prefer "How to `<verb>` …" for a procedural skill. A noun phrase like
  "Known traps in …" reads as scope, not purpose.
- Add `when_to_use` where a missed trigger has cost something (`ship`'s
  bare "push"). Skip it when the description already says it all.
- Both values are plain YAML scalars: never open with a quote (lead with a
  word: `A bare "push", ...`), and no `: ` or ` #` inside. Claude Code
  truncates description + `when_to_use` at 1,536 characters combined.
- Only `name`, `description` and `when_to_use`: a misspelt key such as
  `when-to-use` is silently ignored by every harness.

## The body

- `## Applies to` first, then the procedure or rule, then `## See also`.
- Real examples from this repo, never placeholders: a real path can be
  checked.
- One fact in one place: point to the file that owns a fact rather than
  restating it (skill `docs-sync`).
- Register it: `AGENTS.md`'s skill list names every skill.
