# AGENTS.md

> **Written by agents, for agents.** Working notes for a session with no
> memory of the last one. `README.md` is the human entry point.
>
> This file is canonical; `CLAUDE.md` is a symlink to it. Skills are plain
> markdown at `.agents/skills/<name>/SKILL.md` (Claude Code reads them
> through `.claude/skills`); any agent can read them as files.

## What this is

A Python tool (stdlib only) that draws a flake's modules tree from a
module-graph document: Mermaid and Graphviz diagrams, and a self-contained
interactive page. It never reads `.nix` files.
[dirs-as-categories](https://github.com/NireBryce/dirs-as-categories)
publishes the document as `flake.moduleGraph`; its `doc/format.md` is the
format.

## Hard rules

- **This project is experimental.** Never describe it as stable or
  production-ready; keep the README's notice and the pointers to it in the
  wiki. Say what a change breaks for users, since nothing here promises
  compatibility yet.
- **"push" means skill `ship`**: branch, PR, green CI, one confirmation
  covering merge and branch deletion. Never push to `main` directly.
- **Branching work happens in its own worktree** (skill `use-a-worktree`).
- **`git add` before `nix flake check`**: flakes ignore untracked files.
- **The page never decides the model**; Python does, and one colour
  standard serves every renderer (skill `change-the-drawing`).
- **Never file anything outside this repository** without the user saying
  so explicitly (skill `propose-issue`).
- **Say which rung you reached**: tests pass, the browser check passes, CI
  is green. Never more than you saw.
- **A change that makes a doc stale fixes it in the same change** (skill
  `docs-sync`); one a user can see also adds a line under `CHANGELOG.md`'s
  **Unreleased**.
- **Never tag or publish a release** without the user saying so (skill
  `release`).
- **Examples are generic** -- `laptop`, `base`, `me` -- never anyone's real
  machines (`doc/style.md`).
- **Trailer `Co-Authored-By: Claude`** on agent commits, name only; prose
  says "the user".

## Commands

```sh
just                 # list recipes
just test            # unit tests
just golden          # every view against its saved output (`just golden --update`)
just browser         # the page in headless Chromium (needs chromium: `nix develop`)
just check           # nix flake check: unit tests (also on Python 3.11) and the packaged command
just e2e             # the packaged command on dirs-as-categories' graph, at a pinned revision
just preflight       # all of the above -- what CI runs; needs network (e2e)
nix develop          # python3, just, graphviz; chromium on Linux
nix run . -- hosts --flake <flake>    # draw a flake that publishes moduleGraph
```

## Layout

| Path | Holds |
|---|---|
| `module_graph/model.py` | the model from a document, and `select()` |
| `module_graph/look.py` | the colour standard and card text |
| `module_graph/layout.py` | `[layout]` settings, boxes, rank links |
| `module_graph/mermaid.py`, `dot.py`, `page.py`, `page.html` | the renderers |
| `module_graph/document.py` | reading and checking a document |
| `module_graph/errors.py` | `ModuleGraphError`: every mistake the package reports; only `__main__` exits |
| `tests/` | unit tests, the saved views (`golden.py`), the browser check, their fixtures |
| `doc/style.md` | how all the docs are written |
| `wiki/` | guides: `using-the-tool.md`; `styleguide.md` before adding a page |

## Testing discipline

- **Test first**: the case that shows the change is written, and seen to
  fail, before the code changes.
- **Read an expected value before recording it** -- `tests/browser.py
  --update` writes whatever the page shows; check the counts by hand
  against the fixture first.
- **Break it on purpose**: undo the core of a change and confirm a test
  fails for *that* reason.
- **Every view is saved** (`tests/expected/golden/`, `just golden`): a
  refactor meant to change nothing leaves them byte for byte; a change
  meant to move the drawing has its `git diff` read before `--update`.

## Maintenance that runs itself

- `.github/workflows/update-flake-lock.yml`: on the 3rd of each month, a
  `nix flake update` PR from branch `chore/flake-lock`, force-pushed, so an
  open one is refreshed rather than duplicated. Review it like
  any other: CI passing means the saved views didn't move.
- `.github/dependabot.yml`: monthly PRs bumping the actions, which are
  pinned by commit with the version in a comment.
- The dirs-as-categories revision `just e2e` draws is pinned in `justfile`;
  bump it by hand, on purpose.

## The contract with dirs-as-categories

The document format is versioned (dirs-as-categories' `doc/format.md`).
`document.py` refuses a version it doesn't know and checks only the fields
this tool reads. A new field is fine to ignore; a format change is a change
to both repositories.

## Skills

| Skill | For |
|---|---|
| `change-the-drawing` | changing the model, renderers, colours, page or layout |
| `ship` | landing work on `main` |
| `release` | a version, its changelog, tag and GitHub release |
| `use-a-worktree` | branching work in isolation |
| `review` | reviewing a change here |
| `docs-sync` | keeping docs true in the same change |
| `fact-hygiene` | facts, dates and cross-references that stay true |
| `investigate-bug` | a reported bug, to a failing test |
| `propose-issue` | filing a bug found along the way |
| `git-archaeology` | when and why something changed |
| `boyscouting` | small fixes beside a change |
| `explain-tricky-code` | comments that teach a hard mechanism |
| `trim-docs` | tightening prose |
| `new-skill` | writing a skill |
