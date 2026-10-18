# Using the tool

_Last modified: 2026-10-17_

How to draw a flake's modules tree: getting a document, the four views,
where areas go, what the drawings mean, the interactive page, and what each
error means. Every command here was run against the example below.

**flake-module-graph is experimental** and may change without notice; read
the [README](../README.md)'s notice before relying on it.

## Contents

- [Quick facts](#quick-facts)
- [The example](#the-example)
- [Getting a document](#getting-a-document)
- [The four views](#the-four-views)
- [Narrowing a drawing](#narrowing-a-drawing)
- [Where areas go: the layout file](#where-areas-go-the-layout-file)
- [Reading a drawing](#reading-a-drawing)
- [The interactive page](#the-interactive-page)
- [Without dirs-as-categories](#without-dirs-as-categories)
- [Putting a drawing in docs](#putting-a-drawing-in-docs)
- [Drawings built by Nix](#drawings-built-by-nix)
- [When it refuses](#when-it-refuses)

## Quick facts

| You want to | Run |
|---|---|
| hosts and what they include, as Mermaid | `nix run github:NireBryce/flake-module-graph -- hosts --flake .` |
| every category, folder and module | `… -- tree --flake .` |
| Graphviz instead | `… -- dot --flake . --view hosts` |
| a clickable page | `… -- html -o modules.html` |
| one category only | add `--category base` |
| only categories | add `--categories-only` |
| your areas placed | add `--config module-graph.toml` |
| a document from a file or a pipe | `… -- hosts graph.json`, `… -- hosts -` |

## The example

The flake built in dirs-as-categories' guide
([`wiki/using-the-flake.md`](https://github.com/NireBryce/dirs-as-categories/blob/main/wiki/using-the-flake.md)):
a host `laptop` including the categories `base` and `desktop`, a Home
Manager configuration `me-home` including `shell`, and a module in `base`
that hands `me-home` to the laptop through `enables`. Areas: `hosts`,
`users`, `shared`.

## Getting a document

The tool draws a **module-graph document** -- JSON, format version 1 --
and never reads `.nix` files. dirs-as-categories publishes one as
`flake.moduleGraph`. Three ways in:

```sh
module-graph hosts --flake .                     # runs: nix eval --json .#moduleGraph
module-graph hosts graph.json                    # a file
nix eval --json .#moduleGraph | module-graph hosts -   # stdin
```

`--flake REF` without a `#` means `REF#moduleGraph`. Given no document at
all, the tool reads the flake in the current directory, if it has a
`flake.nix`: `module-graph hosts` there is `module-graph hosts --flake .`.
When something may be piped in, it says so on stderr (`note: no DOCUMENT
given: reading the flake here (--flake .); to read stdin, give -`): piped
input needs `-`. The tool turns on
Nix's `nix-command` and `flakes` features for its own `nix eval`, so it works
on a fresh Nix install; your own `nix` commands, like the stdin one above,
still need them on. Writing the document to
a file first is useful when the flake needs `--override-input` or other
`nix eval` options the tool doesn't pass.

`module-graph` is `nix run github:NireBryce/flake-module-graph --` or, with
the repository as a flake input, its `packages.<system>.default`; the
input should follow your nixpkgs
([README: As a flake input](../README.md#as-a-flake-input)).

## The four views

| View | Draws | Direction |
|---|---|---|
| `tree` | areas, categories, plain folders and modules | left to right |
| `hosts` | the hosts and home configurations, and the categories each includes | top to bottom |
| `dot` | either, as Graphviz (`--view tree` or `--view hosts`) | as above |
| `html` | the hosts view as one self-contained page | either, switchable |

For the example, `hosts` draws two cards in the "hosts and home" box --
`laptop` (nixos) and `me-home` (homeManager) -- with arrows from `laptop`
to `base` and `desktop`, from `me-home` to `shell`, and a dashed `enables`
arrow from `laptop` to `me-home`.

Mermaid output renders in GitHub, GitLab and most Markdown viewers;
Graphviz needs `dot`:

```sh
module-graph dot --flake . --view hosts | nix shell nixpkgs#graphviz -c dot -Tsvg > hosts.svg
```

## Narrowing a drawing

A whole tree of a few hundred modules is unreadable. The options:

- `--category NAME`: that category and what is nested in it. In the hosts
  view, also only the hosts that include something in it.
- `--depth N`: folder levels below the starting point.
- `--categories-only`: leave out modules and plain folders.
- `--wrap N` (hosts view): categories per row in a shared area; 0 for one
  row.

An unknown category is refused, listing the real ones.

## Where areas go: the layout file

Top-level folders are areas. With no settings, every area is drawn the same
way, alphabetically. A TOML file says where yours belong:

```toml
# module-graph.toml
[layout]
top    = ["hosts", "users"]   # Mermaid/Graphviz hosts view: above the hosts
behind = ["hosts"]            # page: before the hosts
beside = ["services"]         # page: next to the hosts
far    = ["users"]            # page: the far end, past the shared areas
shared = ["shared"]           # page: these first, in this order
```

```sh
module-graph html --flake . --config module-graph.toml > modules.html
```

`top` puts an area's categories above the hosts in the static hosts view --
right for a host's own folder, which is part of what the host is.
`behind`, `beside`, `far` and `shared` place areas on the page, which flows
**behind → hosts → shared areas ← homes → far**, top-down or left to
right. Every key is optional; an unknown key is refused.

## Reading a drawing

One colour standard holds in every view:

| Looks like | Is |
|---|---|
| blue, rounded card | a **category**: a host can include it by name |
| pale blue box around cards | a category that holds nested categories |
| slate, square-cornered (a folder shape in Graphviz) | a **plain folder** inside a category, collected only through it |
| white card | a **module** -- also when a host names one directly |
| white card with a coloured outline, in the "hosts and home" box | a **host or home configuration**; its outline colour is shared by every arrow it draws |
| red outline | a category nothing reaches |
| dashed outline | a category reached only through modules named one by one |
| red card, "no such module" | a name a host includes that the document doesn't know |
| dashed arrow labelled `enables` | a host turning on a home configuration |
| `n h d` under a name | the classes: nixos, homeManager, darwin; then how many modules a category holds |

Host colours are never blue or red, so a host can't be mistaken for a
category or an alert.

## The interactive page

`html` writes one file with no external scripts or stylesheets; open it in
a browser. Clicking a host or home card shows only what it reaches -- what
it includes, everything inside those categories, and, for a host, the home
configurations it enables and what they reach. Click more cards to combine
them, or "All hosts" to clear. Each card shows a coloured dot for every
selected host that reaches it. The "Left to right" / "Top to bottom" button
switches direction. The selection and direction live in the URL, so a link
reopens the same view: `modules.html#hosts=laptop&layout=lr`.

In the example (checked in headless Chromium): nothing selected shows all 3
categories and 4 edges; `laptop` shows the same 3 -- `base` and `desktop`
directly, `shell` through the `me-home` it enables; `me-home` shows only
`shell`.

## Without dirs-as-categories

Any tool can write a document. The smallest useful one:

```json
{
  "version": 1,
  "categories": {
    "base": { "dir": "shared/base" }
  },
  "modules": {
    "ssh":    { "path": "shared/base/ssh.nix", "classes": ["nixos"] },
    "laptop": { "path": "hosts/laptop.nix",    "classes": ["nixos"] }
  },
  "includes": {
    "laptop": { "nixos": ["base"] }
  }
}
```

`module-graph hosts minimal.json` draws `laptop` with an arrow into `base`.
A module with `includes` outside every category is drawn as a host; the
rest of the fields are in
[the format](https://github.com/NireBryce/dirs-as-categories/blob/main/doc/format.md).
The tool checks the version and the fields it reads, and ignores fields it
doesn't know.

## Putting a drawing in docs

Mermaid goes straight into Markdown, but a drawing in docs is a copy of the
tree, and copies drift. Put two markers where it goes, saying how to draw
it -- `tree` or `hosts` and any filters:

```markdown
<!-- module-graph: tree --depth 1 --categories-only -->
<!-- /module-graph -->
```

Then let the tool fill and refresh what is between them:

```sh
module-graph markdown --file README.md            # redraws every block; prints how many changed
module-graph markdown --file README.md --check    # changes nothing; fails if any block is stale
```

The document comes from the command as usual (the flake here, a file,
`--flake REF`), and `--config` applies to every block; `--file` repeats for
several files. Filters go in each marker, not on the command line. Markers
inside a fenced code block, like the one above, are examples and left
alone, and a redrawn block keeps the file's line endings. `--check` in CI, or `lib.checkMarkdown` below, fails the
build when someone changes the tree and forgets the docs.

Mermaid refuses a diagram past its default limits -- 50,000 characters or
500 links (mermaid 11.17.2's `maxTextSize` and `maxEdges`) -- and a viewer
using those defaults shows an error instead. `tree` and `hosts` print a
`warning:` on stderr when the drawing passes either; narrow it with
`--category`, `--depth` or `--categories-only`, or use `dot` or `html`,
which have no such limit.

## Drawings built by Nix

A flake that publishes `moduleGraph` can have Nix build its drawings, using
its own nixpkgs (`pkgs`), through this flake's `lib`:

```nix
# outputs, with flake-module-graph as an input (README: As a flake input)
packages.x86_64-linux.modules-html = flake-module-graph.lib.render {
  inherit pkgs;
  graph = self.moduleGraph;
  view = "html";                     # or tree, hosts, dot
  args = [ "--category" "base" ];    # filters, optional
  config = ./module-graph.toml;      # layout, optional
};

checks.x86_64-linux.drawings = flake-module-graph.lib.checkMarkdown {
  inherit pkgs;
  graph = self.moduleGraph;
  src = self;                        # where the files are
  files = [ "README.md" ];           # relative to src
};
```

`nix build .#modules-html` then writes `result`, the page; `nix flake check`
fails, naming the file, when a block in `README.md` is stale. This
repository's own `checks.render` and `checks.markdown` call both the same
way, on `tests/fixtures/golden.json`.

## When it refuses

| Message | Means |
|---|---|
| `` error: module-graph document: version 2; this tool reads version 1 `` | a newer format than this tool knows; update the tool |
| ``error: module-graph document: `categories` must be an object`` | a required field is missing or the wrong type (also `modules`) |
| ``error: module-graph document: categories.x: needs a string `dir` `` | one entry is malformed; the message names it |
| `error: module-graph document: not JSON (…)` | the input isn't JSON -- often `nix eval` printed a warning into it; use `--json` and keep stderr out |
| `error: module-graph document: nix eval /path#moduleGraph failed: …` | the flake didn't evaluate; the innermost cause from Nix's error follows, then a `hint:` line |
| `… failed: flake '…' does not provide attribute … 'moduleGraph'` | the flake doesn't publish `moduleGraph` (dirs-as-categories does); name another attribute with `--flake REF#ATTR` |
| `… failed: Path 'x.nix' in the repository "…" is not tracked by Git.` | a flake in a git repository sees only files git knows about: `git add` them (no commit needed) |
| any other `… failed: …` | run the `nix eval --json` command the hint names to see Nix's whole error |
| `error: give a DOCUMENT (a file, or - for stdin) or --flake REF (no flake.nix here to read)` | nothing to draw, and no flake in the current directory to default to |
| `error: graph.json: no such file` | the document (or `--config` file) isn't where the command says; likewise `Is a directory`, `Permission denied`, `not UTF-8 text`, and for `-o FILE` a folder that doesn't exist |
| ``error: README.md: 1 of 2 drawings is stale; run `module-graph markdown --file README.md` to update them`` | `markdown --check` (or `lib.checkMarkdown`) found a block that no longer matches the tree |
| ``error: README.md: line 3: no `<!-- /module-graph -->` after it`` | a marker without its closing marker; also a second marker before the first closes, a closing marker with none open, and an option a marker can't take, each named by its line |
| ``error: README.md: no `<!-- module-graph: … -->` blocks`` | `markdown --file` found nothing to draw -- often a marker spelled differently, such as `<!--module-graph:` |
| `error: module-graph.toml: not TOML (…)` | the layout file has a syntax error; the parser's message says where |
| `warning: this Mermaid diagram is … characters; Mermaid refuses more than 50000 by default …` | the drawing is still printed, but may not render; see [Putting a drawing in docs](#putting-a-drawing-in-docs) |
| `error: no category 'nope'; categories: …` | `--category` named something that isn't a category |
