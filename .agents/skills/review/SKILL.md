---
name: review
description: How to review a change to flake-module-graph -- the checks to run and the failure modes a generic reviewer doesn't know.
when_to_use: Review a PR, branch, or commit here, or before saying done on your own change.
---

# Reviewing a change

## Applies to

Reviewing a PR, branch or commit here, yours or another's, or the last
step before saying "done".

## Run first

1. `just preflight` -- unit tests, the browser check, flake check.
2. A refactor meant to change nothing: render a real document before and
   after and compare byte for byte.

## Read for

- **Colours chosen outside `look.py`**, a host hue in blue or red, or a
  module drawn as importable.
- **The page deciding something the model should** -- new logic in
  `page.html` that `page_data()` could provide.
- **`tests/expected/browser.json` changed** without the new counts explained
  against the fixture.
- **Mermaid or Graphviz layout changes** that reintroduce a trap
  `change-the-drawing` lists (reversed arrows, invisible-link cycles,
  floating cards).
- **`document.py` accepting a version it doesn't know**, or rejecting a
  field it doesn't read.
- **A behaviour without a test that failed first.**
- **Examples naming real machines or people** (`doc/style.md`).

## Saying the outcome

"Tests pass", "the browser check passes" and "CI is green" are different
claims; say which you saw.
