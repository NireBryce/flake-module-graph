# Changing the drawing

_Last modified: 2026-10-17_

How the code that draws a modules tree fits together, the rules that keep
every view consistent, the traps already hit, and how a change is checked.
For anyone changing `module_graph/`; using the tool is
[using-the-tool.md](using-the-tool.md).

**flake-module-graph is experimental**: say in the change what it breaks
for users (and add it to `CHANGELOG.md`).

## Contents

- [How it fits together](#how-it-fits-together)
- [The rules that hold the drawing together](#the-rules-that-hold-the-drawing-together)
- [Traps already hit](#traps-already-hit)
- [How a change is checked](#how-a-change-is-checked)

## How it fits together

Every command runs the same steps, one module each (the package docstring
in `module_graph/__init__.py` says the same, beside the code):

| File | Holds |
|---|---|
| `module_graph/document.py` | reading and checking a format-1 document, from a file, stdin or `nix eval` |
| `module_graph/model.py` | `graph(document)` -- nodes and edges for the whole tree -- and `select()`, the part one drawing shows |
| `module_graph/layout.py` | `[layout]` settings, the boxes, and the rank links both static renderers share |
| `module_graph/look.py` | the colour standard (`PALETTE`, `HUES`, `ALERT`) and card text |
| `module_graph/mermaid.py`, `dot.py` | the static renderers |
| `module_graph/page.py`, `page.html` | the interactive page: Python decides the model and look, the page only lays out and filters |
| `module_graph/markdown.py` | drawings kept between markers in a Markdown file |
| `module_graph/__main__.py` | the command line that joins them; the only place that exits |

Node ids say what and where (`cat:shared/base`, `agg:hosts/laptop.nix:nixos`);
`model.py`'s docstring lists them, and the order nodes are added in, which
numbers them in every drawing.

## The rules that hold the drawing together

- **One colour standard.** A category is the only thing in blue; a plain
  folder is slate and square; a module is white even when a host names it;
  red is only for alerts. Host hues are never blue or red. Every renderer
  and the page take colours from `look.py`.
- **The page never decides the model.** If the page needs something new,
  `page_data()` in `page.py` provides it.
- **After every change the page writes `<body data-selected data-visible
  data-edges>`**; `tests/browser.py` reads those.

## Traps already hit

- **Mermaid has no reversed arrow** (`<--` fails). An invisible `a ~~~ b`
  plus a real arrow back makes a cycle per pair, and dagre breaks such
  cycles inconsistently -- so an upward edge is a plain `---` line written
  target-first. `linkStyle` indices count `~~~` links too: layout links go
  last. Each `~` past three is one more rank.
- **Graphviz floats a node with no edges to the top rank**, and ordering
  clusters by declaration does nothing: cards are pinned with invisible
  `minlen` links from the first host, and hosts kept on one row with
  `rank=same`.
- **On the page, edges are an SVG layer** above box backgrounds (z-index 1)
  and cards above that (z-index 2). Boxes must not get a z-index, or they
  become stacking contexts.
- **A translucent host tint turns dark on a dark page** and hides the text:
  the hue is mixed with white (`tint()`).

## How a change is checked

| Check | Run | Catches |
|---|---|---|
| unit tests | `just test` | the model, renderers, command line, and the docs' own rules (`tests/test_docs.py`) |
| saved views | `just golden` | any byte that moved in the saved views of `tests/fixtures/golden.json` |
| the page | `just browser` | what the page shows per selection, in headless Chromium |
| the package | `just check` | `nix flake check`: the tests on Python 3.11 too, `lib.render` |
| everything | `just preflight` | all of the above, and the published graph end to end -- what CI runs |

`nix develop` gives a shell with everything these need.

- **Write the test first**, and see it fail, before changing the code.
- **A change meant to change nothing** leaves `tests/expected/golden/`
  untouched. **A change meant to move the drawing** shows exactly what
  moved: `just golden` prints the diff; read it, then
  `just golden --update` and commit it with the change. A new kind of thing
  to draw gets a case in `tests/fixtures/golden.json` first.
- **The page's counts** (`tests/expected/browser*.json`) are recorded with
  `python3 tests/browser.py --update`, which prints what moved. Check each
  new number by hand against the fixture before committing it.
- **A change to the document format** is a change to dirs-as-categories'
  `doc/format.md` and its version too.
