---
name: change-the-drawing
description: How to change what flake-module-graph draws or how, without breaking the colour standard or the page.
when_to_use: Changing the model, a renderer, the colour standard, the page, layout settings, or document checks.
---

# Changing the drawing

## Applies to

Anything under `module_graph/`: the model, Mermaid or Graphviz output, the
interactive page, the colour standard, `[layout]` settings, or what
`document.py` accepts.

## Read first

[`wiki/changing-the-drawing.md`](../../../wiki/changing-the-drawing.md):
where things are, the rules that hold the drawing together (one colour
standard; the page never decides the model), the traps already hit, and
the checks. This skill adds only what an agent tends to skip.

## Every time

1. A model or renderer change: a unit test that fails first.
2. `just golden`: a refactor leaves it untouched; a drawing change has its
   diff read line by line before `--update`.
3. A page change: `python3 tests/browser.py`. If counts change, check each
   new value **by hand against the fixture** before `--update` -- never
   record numbers you haven't explained.
4. Break it on purpose and watch a test fail for the right reason.
5. Docs in the same change (skill `docs-sync`), a `CHANGELOG.md` line, then
   `just preflight`.
