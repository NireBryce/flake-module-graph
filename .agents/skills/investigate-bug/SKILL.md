---
name: investigate-bug
description: How to check whether a reported bug is already known before investigating it, then narrow it down to a failing test.
when_to_use: Someone reports a bug, an error, or behaviour that looks wrong.
---

# Investigating a bug

## Applies to

A report of a bug, a confusing error, or behaviour that looks wrong --
from the user, an issue, or a failing CI run.

## 1. Is it already known?

```sh
gh issue list --search "<keywords from the error>" --state all
git log --oneline -S '<distinctive string>'      # when did this text appear or vanish?
git grep -n '<error text>'
```

Read any match in full before starting your own investigation.

## 2. Did it ever work?

Find the last commit where it worked (`git bisect` over a fixture or a
`nix eval` expression). Regression and always-broken need different fixes,
and the answer settles arguments about mechanism quickly.

## 3. Reproduce it as a test

Turn the report into the smallest case that fails -- a fixture, a document,
an expression -- **before** fixing anything. Then fix, and watch the same
test pass. A fix with no test that failed first is unverified.

## 4. Read the whole output

Nix puts the innermost cause last: read an error trace to the bottom.
`cmd | tail` exits 0 when `cmd` failed. Before believing a zero or a count,
show the query can return something else.

## 5. Say what you reached

"Evaluates", "the checks pass", "CI is green" are different claims; say
which. If you couldn't reproduce it, say so rather than fixing a guess.
