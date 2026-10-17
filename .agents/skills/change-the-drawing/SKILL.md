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

## Where things are

| File | Holds |
|---|---|
| `module_graph/model.py` | `graph(document)` -- nodes and edges -- and `select()` |
| `module_graph/look.py` | the colour standard (`PALETTE`, `HUES`, `ALERT`), card text |
| `module_graph/layout.py` | `[layout]` settings, boxes, rank links shared by both renderers |
| `module_graph/mermaid.py`, `dot.py` | the static renderers |
| `module_graph/page.py`, `page.html` | the interactive page: Python decides the model and look, the page only lays out and filters |
| `module_graph/document.py` | reading and checking a format-1 document |
| `tests/test_module_graph.py` | unit tests; the `Doc` builder makes documents |
| `tests/golden.py` | every view of `tests/fixtures/golden.json`, against `tests/expected/golden/` |
| `tests/browser.py` | the page in headless Chromium, against `tests/expected/browser.json` |

## The rules that hold the drawing together

- **One colour standard**: a category is the only thing in blue; a plain
  folder is slate and square; a module is white even when a host names it;
  red is only for alerts. Host hues are never blue or red. Every renderer
  and the page take colours from `look.py`.
- **The page never decides the model.** If the page needs something new,
  `page_data()` provides it.
- **After every change the page writes `<body data-selected data-visible
  data-edges>`**; `tests/browser.py` reads those.

## Traps already hit

- Mermaid has no reversed arrow (`<--` fails). An invisible `a ~~~ b` plus a
  real arrow back makes a cycle per pair, and dagre breaks such cycles
  inconsistently -- draw an upward edge as a plain `---` line written
  target-first. `linkStyle` indices count `~~~` links too: emit layout
  links last. Each `~` past three is one more rank.
- Graphviz floats a node with no edges to the top rank, and ordering
  clusters by declaration does nothing: pin cards with invisible `minlen`
  links from the first host, and keep hosts on one row with `rank=same`.
- On the page, edges are an SVG layer above box backgrounds (z-index 1) and
  cards above that (z-index 2). Boxes must not get a z-index, or they
  become stacking contexts.
- A translucent host tint turns dark on a dark page and hides the text: mix
  the hue with white (`tint()`).

## Test first, then check by eye

1. A model or renderer change: a unit test that fails first.
2. A page change: run `python3 tests/browser.py`. If the expected counts
   change, check the new values **by hand against the fixture** before
   `--update` -- never record numbers you haven't explained.
3. Every view of `tests/fixtures/golden.json` is saved in
   `tests/expected/golden/`, and the unit tests compare against it. A
   refactor meant to change nothing leaves it untouched. A change meant to
   move the drawing: `just golden` prints the diff; read it, then
   `just golden --update` and commit the diff with the change. A new kind of
   thing to draw gets a case in the fixture first.
4. Break it on purpose and watch a test fail for the right reason.
5. `doc`/README, `just preflight`; a change to the document format follows
   dirs-as-categories' `doc/format.md` and its version.
