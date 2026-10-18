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
- With no document given, the flake in the current directory
  (`--flake .`), with a note on stderr when stdin may have been meant.
- `-o FILE`, written only once the drawing succeeded.
- A mistake in the input is one `error:` line, never a traceback; as a
  library, the package raises `ModuleGraphError` and never exits.
- A warning when a Mermaid drawing passes Mermaid's default limits.
- A few thousand modules draw in about a second.
- `markdown --file FILE [--check]` keeps Mermaid drawings in Markdown
  current between `<!-- module-graph: … -->` markers; `lib.render` and
  `lib.checkMarkdown` do the same from another flake, with its nixpkgs.
- On the page, each host has a number as well as a colour, on its card
  and in the dots of everything it reaches; screen readers hear the names.
- `--category` in the hosts view keeps the category inside its area, so
  `html --category X` draws X instead of an empty page.
