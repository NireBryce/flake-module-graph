---
name: trim-docs
description: How to tighten this repo's docs, skills and AGENTS.md for concision without losing a load-bearing fact.
when_to_use: Asked to lint, tighten, trim, or make the docs more concise.
---

# Tightening docs

## Applies to

Asked to "tighten", "trim" or "make more concise" `README.md`, `doc/`, `wiki/`,
`.agents/skills/*/SKILL.md` or `AGENTS.md`. Not: fixing a stale fact
(skill `docs-sync`), or code comments.

## Keep

Mechanisms, exact option, key, flag and command names, error message text,
dates, verification methods and what was actually verified, and every
qualifier about confidence (skill `fact-hygiene`). When unsure whether a
sentence is load-bearing, it is.

Also keep what other files point at: headings are link anchors -- grep
`<file>#` across the repo before renaming one.

## Cut

- The same explanation on several pages: keep the fullest in one place,
  point to it from the rest.
- How something came to be, told as a story: one dated line.
- Meta-commentary ("as explained above", "this page covers …").
- Several cross-references to one fact: one pointer.

## After

Run the checks (`just preflight`): nothing a test reads may have moved, and
a doc's examples must still be true -- run any command you left in.
