# Contributing

flake-module-graph is **experimental** (see the README's notice), so a
change may break what users rely on -- that's allowed, but say so: in the
PR, and under **Breaks** in `CHANGELOG.md`.

## Getting set up

```sh
nix develop          # python3, just, graphviz; chromium on Linux
just                 # list the recipes
just preflight       # everything CI runs
```

Without Nix: Python 3.11 or newer runs the tool and its unit tests
(`python3 -m unittest discover -s tests`); the page check needs Chromium.

## Making a change

[`wiki/changing-the-drawing.md`](wiki/changing-the-drawing.md) is how the
code fits together, the rules that keep every view consistent, the traps
already hit, and how a change is checked. In short:

- Write the test that shows the change first, and see it fail.
- `just golden` shows every byte a change moved in the drawings; a change
  meant to change nothing moves none.
- A change that makes a doc wrong fixes it in the same PR; `just test`
  checks the docs' links, anchors, flags and wiki examples.
- Docs follow [`doc/style.md`](doc/style.md); examples use generic names
  (`laptop`, `base`, `me`), never real machines.

## Reporting a bug

Open an issue with the bug template: the command, what it printed, and the
document if you can share it (`nix eval --json .#moduleGraph > graph.json`).

## Agents

`AGENTS.md` and `.agents/skills/` are working notes for coding agents; they
point into the same wiki and docs.
