# Wiki style guide

_Last modified: 2026-10-16_

How this wiki is organised and written. The rest of the docs follow
[`../doc/style.md`](../doc/style.md); this page adds what is particular to
the wiki. Read it before adding, splitting or renaming a page.

## Contents

- [What the wiki is for](#what-the-wiki-is-for)
- [Every page](#every-page)
- [Naming and placing a page](#naming-and-placing-a-page)
- [Writing a page](#writing-a-page)
- [Linking](#linking)
- [Keeping it true](#keeping-it-true)

## What the wiki is for

Three places hold docs, and each has one job:

| Where | For | Holds |
|---|---|---|
| `README.md` | someone deciding whether to use this | what it is, a quick start, the commands |
| `doc/` | someone writing a docs change | how the docs are written (`style.md`) |
| `wiki/` | someone using it or changing it | guides, worked examples, reading the drawings, troubleshooting |

The document format itself is dirs-as-categories' `doc/format.md`; a page
here links to it rather than restating it. A fact written in two places
drifts, and nothing says which copy is right.

## Every page

1. `# Title` -- what the reader wants ("Using the tool"), not a module name.
2. `_Last modified: YYYY-MM-DD_` on the line after the title. **Bump it in
   the same change that edits the page's content.** A typo fix or a
   mechanical link update doesn't need it.
3. One or two sentences on what the page is for and who it is for.
4. `## Contents`, one bullet per `##` heading, when the page has three or
   more of them. Anchors are GitHub's: lowercase, spaces to hyphens,
   punctuation dropped.
5. A page over roughly 1,000 words opens with `## Quick facts` -- a table
   of the facts a returning reader looks up -- as its first section after
   Contents.
6. An entry in [00-INDEX.md](00-INDEX.md).

## Naming and placing a page

- Lowercase, hyphenated, named for the task or topic: `using-the-tool.md`.
- One level: `wiki/*.md`. A subdirectory only when a single topic has grown
  several pages of its own, and then with its own `00-INDEX.md`.
- Before creating a page, check whether the subject belongs as a section of
  an existing one.

## Writing a page

- **Every command is run before it is published**, on the document the page
  uses, and the output described is what it printed. Counts the page reports
  (visible cards, edges) come from the page in a browser, the way
  `tests/browser.py` reads them.
- **Use the generic names from `doc/style.md`** (`laptop`, `base`, `me`) and
  generic area names (`hosts`, `users`, `shared`).
- **Show the command, then what it does.**
- **Errors appear as the tool prints them**, so a reader can search the page
  for the message they got.
- **Describe colours and shapes in words** as well as by name: a reader may
  be looking at a Mermaid render in a different theme.
- **Confidence stays with the claim** (skill `fact-hygiene`): say what an
  example was checked with, and mark anything unchecked.

## Linking

- Relative links within this repository; full URLs to dirs-as-categories.
- Headings are anchors other pages use: grep for `<page>.md#` before
  renaming one.
- One pointer per fact, at the place it is needed.

## Keeping it true

A change to a command, a flag, an error message, a colour or what the page
shows updates every wiki page that shows it, in the same change (skill
`docs-sync`). Search the wiki for the old text before committing:

```sh
git grep -n '<old flag or message>' -- wiki/
```
