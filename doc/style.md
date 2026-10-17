# How the docs are written

For `README.md`, `doc/`, `AGENTS.md` and the skills under `.agents/skills/`.
Code comments follow the same spirit, shorter.

## Where a fact goes

| File | For | Holds |
|---|---|---|
| `README.md` | someone arriving cold | what this is, a quick start, one example, links into `doc/` |
| `doc/*.md` | someone looking something up | one topic per file, complete and exact |
| `wiki/*.md` | someone using or changing it | guides, worked examples, reasoning, troubleshooting -- [`../wiki/styleguide.md`](../wiki/styleguide.md) |
| `AGENTS.md` | an agent starting a session | what applies to every session, and where the rest is |
| `.agents/skills/<name>/SKILL.md` | an agent doing one kind of task | that task's procedure and traps |

**One fact lives in one place**; everywhere else points to it. A fact
written twice drifts, and nothing tells you which copy is right. When a
copy is unavoidable (a summary table in the README), the README points to
the full statement.

## Writing

- **Present tense describes how it is now.** How it came to be is one dated
  line ("until 2026-10-16, …") or the commit log, not a narrative.
- **Plain words.** Define a term at first use. Prefer the word a reader
  would search for.
- **Exact names.** Options, keys, flags, error messages and commands as
  written, in backticks.
- **Tables for lookups**, prose for reasoning, code blocks for anything a
  reader would type -- and every code block runs as written.
- **Examples are generic.** Hosts are `laptop` and `server`, categories
  `base` and `desktop`, users `me`. Never a real person's machines, network
  or accounts.
- **Confidence stays with the claim** (skill `fact-hygiene`): what was
  checked says how; what wasn't says so in the same sentence.
- **Security in public text stays mechanical**: what a check enforces and
  how it was verified, not what got past an older version or what it could
  reach.

## Shape

- A doc opens with what it is for, in a sentence or two.
- Headings are link anchors: grep for `<file>#` before renaming one.
- A doc past roughly 1,000 words opens with a short table of the key facts,
  or splits.

## Keeping it true

A change that makes a doc wrong fixes it in the same change (skill
`docs-sync`). `just preflight` runs the examples the tests cover; the rest
are yours to run.
