---
name: fact-hygiene
description: How to write a specific fact, a dated status, or a cross-reference so it stays true or visibly says how sure it is.
when_to_use: Writing "confirmed", "as of <date>", a version, or a claim about another file in a doc, comment, or commit message.
---

# Writing facts that stay true

## Applies to

1. **A specific checkable fact about something outside this repo** -- an
   upstream behaviour, a version, "works with X" -- stated with more
   confidence than was observed this session.
2. **A "status as of `<date>`" snapshot** of something mutable. The date
   reads as freshly checked; nothing re-verifies it.
3. **A cross-reference to something else in this repo** stated as currently
   true in a comment or doc ("both X and Y do Z"). A later rename can't know
   the sentence exists.

Not this skill -- write freely: design rationale, **event dates** ("on
`<date>` X was decided"), plans and hypotheses labelled as such, and plain
comments describing the code in front of you.

## The rule

- **(1)** State only what you saw this session by a named method (command
  output, file read, test run). Everything else gets a qualifier --
  `UNVERIFIED`, `not confirmed`, `assumed from …` -- **in the same
  sentence**, where a later trim can't drop it.
- **(2)** A date is when someone last checked, not a guarantee. Re-check
  anything checkable now; otherwise "last checked `<date>`, unconfirmed
  since".
- **(3)** A name in prose is a live pointer that can dangle. Renaming or
  removing something: grep its exact name across the whole repo, not only
  the files you touched.

## Preventing it

1. For each specific noun in a claim (path, version, flag), name what showed
   it this session. Otherwise mark it inferred, or leave it out.
2. Don't fuse two separately-true facts into one never-observed claim.
3. Precision beyond what you checked is a liability: the vaguer true
   statement outlives the sharper false one.
4. Condensing text strips qualifiers first, as if they were hedging. They
   are facts about the claim; carry them verbatim, or drop the claim.

## When a claim turns out wrong

Grep for every copy (`git grep -n "<claim>"`), fix them all in the same
change, and correct the confidence, not just the content. A comment that
recorded *why* the wrong claim was believed stays.
