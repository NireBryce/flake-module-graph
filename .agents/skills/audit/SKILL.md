---
name: audit
description: How to audit this tree for unintended side-effects and security issues -- trust boundaries, the escaping contracts, and the sweep that must come back clean.
when_to_use: Asked to audit or review for security or side-effects -- or before a release, beside the checks the review skill runs on a change.
---

# Auditing this tree

## Applies to

An audit of flake-module-graph itself -- what it does to the world, and
what untrusted input can do to its output. The review skill checks a
change; this checks the whole tree. Findings feed the test-first flow;
nothing is fixed without a test that failed first.

## Run first

1. `just test` -- `tests/test_hygiene.py` is the mechanical sweep, and it
   must be clean before anything else is believed.
2. `just browser` -- the `hostile` page renders names holding markup,
   quotes and `%` in a real browser.
3. `python3 tests/golden.py` -- the `hostile-*` saved drawings are the
   escaping contracts, byte for byte.

## Trust boundaries, and where each one lands

Every input crosses into some interpreter. The table is the contract; a
change that adds an input or a path to an interpreter updates it.

| Input | Reaches | Guard |
|---|---|---|
| names in the document (module, category, class, a missing name) | Mermaid HTML labels | `mermaid.esc()` -- entity form |
| the same names | Graphviz HTML-like labels | `html.escape` in `dot.py` |
| the same names | the page's DOM | `textContent` only; the data line has every `<` escaped (`page.py`) |
| the URL hash | `decodeURIComponent` | one title at a time, each in a try/catch; titles are looked up, never rendered |
| the flake ref | `subprocess.run` argv | a list, never a shell; the ref is the user's own choice to evaluate |
| `--config` TOML | `tomllib`, then `Layout` | keys checked against the dataclass, values against list-of-str |
| the document's shape | `document.check` | refuses what the tool would misread; an unreadable input says so, not a traceback |

Names may hold `<!--<script`, `%`, quotes, any Unicode. An escape aimed
only at `</` was once not enough: `<!--` plus `<script` puts the HTML
parser in a state where the template's own `</script>` stops closing the
element, and only a real browser showed it. Believe a probe over a
reading; `tests/fixtures/hostile.json` exists so a probe is one command.

## The side-effect sweep

The package writes nothing but stdout or `-o FILE`, spawns nothing but
`nix eval` as an argument list, and fetches nothing. `test_hygiene.py`
pins all of it, so a regression fails `just test`; when working by hand,
the sweep is one grep:

    shell= | os.system | popen | eval( | urllib | socket | requests
    | innerHTML | document.write | <script src | https?://

Every hit needs a place in the table above or a removal.

## Refusals, not silent merges

Where the tool cannot draw what a document says, `document.check` refuses
it with a reason (two modules on one path, a list entry that is not a
name). A field the tool does not read stays ignored. When a check occurs
to you during an audit, prefer adding it to `check` over teaching the
drawing to tolerate the input.

## Saying the outcome

"the sweep is clean", "the browser probes pass", "CI is green" are
different claims; say which you saw. A bug beyond this task goes to skill
`propose-issue`.
