---
name: use-a-worktree
description: How to work in an isolated git worktree instead of a checkout another session may share.
when_to_use: Before the first git command that branches, commits, merges, or checks out -- not for read-only work.
---

# Working in your own worktree

## Applies to

The first time in a session you're about to run a git command that changes
what's checked out or what a branch points at (`git switch -c`, `commit`,
`merge`, `branch -d`). Not read-only work (reading, grepping, `nix flake
check` on whatever is checked out).

Stay in the current checkout when the user says to, when the task is about
that checkout's own state, or when you already made a worktree for this
branch earlier in the session (one per branch, not per command).

## Why

Two sessions sharing one checkout see each other's checkouts and commits
mid-task: files revert, branches swap underneath, `git branch -d` fails
because the branch is checked out in the other session's directory. A
worktree has its own directory and `HEAD` over the same `.git`.

## How

```sh
git -C <repo> fetch origin
git -C <repo> worktree add <scratch>/wt-<thing> -b feat/<thing> origin/main
```

`<scratch>` is the session's scratch directory (none named: `/tmp`). The
branch is the real one you will ship, not a throwaway label. Then work
there: `just`, `nix flake check` and `gh pr create` all behave as usual.

**Check you're in it** (`git status -sb`, `pwd`) before anything that
changes state; a tool that resets the working directory between commands
puts you back in the shared checkout. Prefer `git -C <path>` and absolute
paths.

Flakes in a git repository see only files git knows: `git add` a new file
in the worktree before `nix eval` or `nix flake check`, or it silently
doesn't exist.

## Afterwards

Once the branch has landed (skill `ship`): `git worktree remove <path>`,
then `git worktree prune`. If git state doesn't match your last action,
read `git reflog` before concluding anything is broken.
