---
name: docs-sync
description: Check whether a change you just made leaves a doc, skill or AGENTS.md stale, and fix it in the same change.
when_to_use: Before committing any change to behaviour, a name, a command, an error message, or the file layout.
---

# Keeping the docs true

## Applies to

Every change that alters behaviour, a name, an option, a command, an error
message or where a file lives. Run it before the commit, not after: a doc
fixed in a later change is a doc that was wrong in between.

## Find what the change touched

```sh
git diff --name-only origin/main...           # what you changed
git grep -n '<old name>\|<old message>\|<old path>'
```

Grep for every name, key, flag, message and path the diff changed or
removed -- across `README.md`, `doc/`, `wiki/`, `AGENTS.md`, `.agents/skills/`,
code comments and test descriptions. A present-tense claim about another
file is a live pointer (skill `fact-hygiene`).

## Fix it in the same change

- One fact lives in one place; everywhere else points there. If the fact
  had copies, fix every copy, then cut the copies down to pointers.
- Examples in docs are claims too: run each one you touched.
- A history note ("until `<date>` X did Y") stays true; don't rewrite
  history, add to it.
- New skill, doc or recipe: list it where `AGENTS.md` lists them.

## Then

`just preflight`. Say in the commit message which docs moved with the
code, so a reviewer can check the pair.
