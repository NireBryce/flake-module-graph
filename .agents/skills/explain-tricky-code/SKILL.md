---
name: explain-tricky-code
description: How to write comments that teach a reader a piece of code whose design isn't obvious from the code alone.
when_to_use: Asked to explain code like a talk, or a comment rewrite keeps coming back still confusing.
---

# Explaining tricky code

## Applies to

Code whose *mechanism* is the hard part -- a competent reader can't follow
it from the code alone; the questions are "why is it shaped like this" and
"what breaks if I touch it". Asked directly, or offered when a comment
rewrite keeps coming back "still confusing". Ordinary code keeps short,
dense comments.

This is the opposite trade from short comments: a header in this style is
several times longer. Use it only where the mechanism earns it, and say so
when offering.

## The shape

Each part is its own titled section, in this order; skip parts the code
doesn't need, don't reorder. Title sections after what they describe, not
with a judgement ("the clever part") -- labels bias how the next reader
weighs the code.

1. **Self-introduction, with the full path.** "This file, `<path>`, is …"
2. **The problem: what first, why second.** What it does in one plain
   sentence, then the obvious alternative and how it fails, concretely.
3. **Background the mechanism leans on -- only that.** Language or library
   behaviour the reader needs, stated once.
4. **How it works, in the order it runs**, with a worked example from this
   repo's own tests or fixtures.
5. **What you can't change, and why**: each constraint that looks like a
   cleanup opportunity, with what breaks.
6. **How to check a change**: the test or command that would catch a
   mistake.

## Voice

- Define every term at first use, in words.
- Real examples from this repo, never `foo`/`bar`: a real path can be
  checked.
- Short sentences; one idea each.
