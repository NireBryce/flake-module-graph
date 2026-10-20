#!/usr/bin/env python3
"""Saved outputs: every view of two fixtures, as the command prints it,
kept in tests/expected/golden/. The unit tests compare against them, so a
change meant to change nothing (a refactor, a rename) is checked byte for
byte, and a change meant to change the drawing shows exactly what moved in
`git diff`.

    python3 tests/golden.py             # compare; prints what differs
    python3 tests/golden.py --update    # rewrite the saved outputs

golden.json has one of everything the drawings distinguish: a nested
category, a plain folder holding a category, a category reached only through
a module named on its own, one nothing reaches, a name no module declares,
a host enabling a home configuration, areas above the hosts, and enough
shared categories to wrap. hostile.json has names that must never reach a
renderer as markup or quotes -- `<img>`, `</script>`, `"` and `%` -- and
non-ASCII; its saved drawings are the escaping contracts. The html case
keeps only the data the page is given, indented so a diff reads: the rest
is page.html, already in git.
"""
import contextlib, difflib, io, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from module_graph.__main__ import main  # noqa: E402

FIXTURE = 'tests/fixtures/golden.json'
HOSTILE = 'tests/fixtures/hostile.json'
CONFIG = ['--config', 'tests/fixtures/golden.toml']
SAVED = ROOT / 'tests' / 'expected' / 'golden'
CASES = {                                   # file name -> command line
    'tree.mmd':                 ['tree', FIXTURE],
    'tree-categories-only.mmd': ['tree', FIXTURE, '--categories-only'],
    'tree-desktop-depth-1.mmd': ['tree', FIXTURE, '--category', 'desktop', '--depth', '1'],
    'hosts.mmd':                ['hosts', FIXTURE, *CONFIG],
    'hosts-no-config.mmd':      ['hosts', FIXTURE],
    'hosts-wrap-0.mmd':         ['hosts', FIXTURE, *CONFIG, '--wrap', '0'],
    'hosts-base.mmd':           ['hosts', FIXTURE, *CONFIG, '--category', 'base'],
    'tree.dot':                 ['dot', FIXTURE],
    'tree-categories-only.dot': ['dot', FIXTURE, '--categories-only'],
    'hosts.dot':                ['dot', FIXTURE, '--view', 'hosts', *CONFIG],
    'page-data.json':           ['html', FIXTURE, *CONFIG],
    'page-data-base.json':      ['html', FIXTURE, *CONFIG, '--category', 'base'],
    'hostile-tree.mmd':         ['tree', HOSTILE],
    'hostile-hosts.mmd':        ['hosts', HOSTILE],
    'hostile-tree.dot':         ['dot', HOSTILE],
    'hostile-page-data.json':   ['html', HOSTILE],
}


def render(argv):
    """What `module-graph <argv>` prints, run from the repository root."""
    out = io.StringIO()
    with contextlib.chdir(ROOT), contextlib.redirect_stdout(out):
        main(argv)
    text = out.getvalue()
    if argv[0] == 'html':
        (line,) = [l for l in text.splitlines() if l.startswith('const DATA = ')]
        data = json.loads(line.removeprefix('const DATA = ').removesuffix(';'))
        text = json.dumps(data, indent=1) + '\n'
    return text


def differences():
    """{file name: unified diff} for every case whose output moved."""
    out = {}
    for name, argv in CASES.items():
        path = SAVED / name
        want = path.read_text() if path.exists() else ''
        got = render(argv)
        if got != want:
            out[name] = ''.join(difflib.unified_diff(
                want.splitlines(True), got.splitlines(True), f'saved/{name}', f'now/{name}'))
    return out


def main_(argv):
    if '--update' in argv:
        SAVED.mkdir(parents=True, exist_ok=True)
        for name, case in CASES.items():
            (SAVED / name).write_text(render(case))
        print(f'wrote {len(CASES)} files to {SAVED.relative_to(ROOT)}')
        return 0
    diffs = differences()
    for name in CASES:
        print(f'{"DIFF" if name in diffs else "same"}  {name}')
    for d in diffs.values():
        print(d)
    return 1 if diffs else 0


if __name__ == '__main__':
    sys.exit(main_(sys.argv[1:]))
