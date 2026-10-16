---
name: git-archaeology
description: How to find the commit that added, changed, or removed something in git history, even when the file has since moved.
when_to_use: Asked when or why something changed, or verifying a date or commit a comment cites.
---

# Finding when something changed

## Applies to

"When did this change?", "why is it like this?", or checking a date or
commit hash a comment or doc cites.

## Recipes

```sh
git log --oneline -S '<string>'                 # commits that added or removed this exact string
git log --oneline -G '<regex>'                  # commits whose diff matches the regex
git log --oneline --follow -- <path>            # one file's history, across renames
git log --oneline --diff-filter=D -- '<glob>'   # when files matching the glob were deleted
git show <commit>:<path>                        # a file as it was at that commit
git blame -w -C <path>                          # line by line, ignoring whitespace, across moves
```

- An empty `git log -- <path>` usually means the file moved: retry with
  `--follow`, or search the content with `-S`.
- `-S` counts occurrences, so a commit that only moves a line within a file
  doesn't show; `-G` does.
- The commit message says why; the PR (`gh pr list --search <sha>`) often
  says more.

## Writing the answer down

Cite the commit (short hash) and the date. A date in a comment is an event
date -- it can't go stale -- but say what it is the date *of*.
