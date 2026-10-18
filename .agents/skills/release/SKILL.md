---
name: release
description: How to cut a release of flake-module-graph -- version, changelog, tag and GitHub release.
when_to_use: Asked to release, tag, or publish a version.
---

# Cutting a release

## Applies to

An ask to release, tag or publish a version. Not for landing ordinary
work (skill `ship`), and never on your own initiative: a tag is public and
people pin it.

## What a version means

`0.MINOR.PATCH` while the project is experimental (`CHANGELOG.md`'s
preamble): a release with any **Breaks** line bumps MINOR, anything else
PATCH. The version lives in one place, `module_graph/__init__.py`'s
`__version__`; `pyproject.toml` and `--version` read it.

## 1. The release PR

In a worktree (skill `use-a-worktree`), on `release/vX.Y.Z` from
`origin/main`:

1. `__version__ = 'X.Y.Z'` in `module_graph/__init__.py`.
2. In `CHANGELOG.md`, `## Unreleased` becomes `## X.Y.Z -- YYYY-MM-DD`
   (today), with a new empty `## Unreleased` above it. Read every line
   under it against `git log vPREVIOUS..origin/main` (the first release:
   `git log origin/main`): a user-visible change without a line gets one,
   and each breaking change is under **Breaks**.
3. `just preflight`, then land it with skill `ship`.

## 2. Tag and publish -- only after the user says yes

Show the user the version, the changelog section and the merge commit, and
ask once: "tag vX.Y.Z on <commit> and publish the release?" On yes:

```sh
git switch main && git pull --ff-only
git tag -a vX.Y.Z -m "flake-module-graph X.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "X.Y.Z" --notes-file <the changelog section, as a file>
```

Then check it is reachable the way the README says to pin it:
`nix run github:NireBryce/flake-module-graph/vX.Y.Z -- --version` prints
`module-graph X.Y.Z`.

## Never

- Move or delete a pushed tag: anyone who pinned it now gets something else.
  A bad release is fixed by the next one.
- Tag a commit that isn't on `main`, or one CI hasn't passed.

## See also

Skill `ship` (the release PR), `CHANGELOG.md` (what a version means).
