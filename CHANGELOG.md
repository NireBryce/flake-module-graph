# Changelog

What changed for someone using flake-module-graph, newest first. The project
is **experimental**: any release may break the command line, the layout
file, the drawings or the page, and each entry's **Breaks** says how.

Every change a user can see adds a line under **Unreleased** in the same
PR; a release renames that heading (skill `release`). Versions are
`0.MINOR.PATCH` until the project stops being experimental: a release that
breaks something bumps MINOR.

## Unreleased

The first release, 0.1.0. It reads module-graph documents of format
version 1 (dirs-as-categories' `doc/format.md`).

- Four views: `tree` and `hosts` (Mermaid), `dot` (Graphviz, either view),
  and `html`, a self-contained interactive page of the hosts view.
- The document from a file, stdin (`-`), or `--flake REF`, which runs
  `nix eval --json` with flakes turned on for that command.
- Filters `--category`, `--depth`, `--categories-only`, `--wrap`; where
  areas go from a `[layout]` table (`--config`).
- A failed `nix eval` names its innermost cause and a hint for the usual
  mistakes.
- `module-graph --version`; installable without Nix through
  `pyproject.toml` (`pipx`, `uvx`), on Python 3.11 or newer.
