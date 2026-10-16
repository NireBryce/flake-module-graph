---
name: boyscouting
description: How to leave code you are already touching a little better, without letting the cleanup outgrow the task.
when_to_use: Editing a file and noticing a small, local problem next to the change.
---

# Leaving it a little better

## Applies to

You are already editing a file for some task and notice something small
and local next to your change: a stale comment, an unclear name, a missing
test for the case you just touched, a doc line your change made wrong.

## Do

- Fix what is **in the lines you are already touching**, or directly beside
  them, when the fix is obviously right and small.
- Keep it in the same commit only if it belongs with the change; otherwise
  make it a separate commit in the same branch, so a reviewer can tell the
  two apart.
- Say what you tidied in the commit message.

## Don't

- Reformat a file, rename across the codebase, or restructure on the side.
- Change behaviour as a "cleanup".
- Delete a comment explaining a past bug or a design decision because the
  code around it changed: move it to where it still applies, or keep it.

Anything bigger: note it, finish the task, and propose it (skill
`propose-issue`).
