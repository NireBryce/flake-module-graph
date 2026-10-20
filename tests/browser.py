#!/usr/bin/env python3
"""The page in a real browser: for each selection and layout, what it shows.

After every change the page writes <body data-selected data-visible
data-edges>. This renders each page in PAGES, opens it in headless Chromium
once per case, and compares those three to its expected file:

    browser   tests/fixtures/browser.json, every selection in both directions
    example   tests/fixtures/example.json, the example wiki/using-the-tool.md
              describes -- the counts that page states are these

    python3 tests/browser.py             # needs chromium (or $CHROMIUM) on PATH
    python3 tests/browser.py --update    # rewrite the expected values, printing what moved
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from module_graph import Layout, document, graph, load_layout, page, select  # noqa: E402

CASES = ['', 'hosts=alpha-host', 'hosts=beta-host', 'hosts=home', 'hosts=alpha-host,beta-host',
         'hosts=nope', 'hosts=%']
CASES += [f'{c}&layout=lr' if c else 'layout=lr' for c in CASES]
TESTS = ROOT / 'tests'
PAGES = {   # name -> (document, layout file or None, URL fragments, expected)
    'browser': (TESTS / 'fixtures' / 'browser.json', TESTS / 'browser.toml', CASES,
                TESTS / 'expected' / 'browser.json'),
    'example': (TESTS / 'fixtures' / 'example.json', None, ['', 'hosts=laptop', 'hosts=me-home'],
                TESTS / 'expected' / 'browser-example.json'),
    # names with markup, quotes and % in them: the page shows them as text,
    # selects one through its percent-encoded hash, and survives a broken one
    'hostile': (TESTS / 'fixtures' / 'hostile.json', None, ['', 'hosts=50%25', 'hosts=%'],
                TESTS / 'expected' / 'browser-hostile.json'),
}


def browser():
    exe = os.environ.get('CHROMIUM') or next(
        (shutil.which(n) for n in ('chromium', 'chromium-browser', 'google-chrome') if shutil.which(n)), None)
    if not exe:
        raise SystemExit('error: no chromium on PATH (or set $CHROMIUM)')
    return exe


def body(exe, url):
    r = subprocess.run([exe, '--headless=new', '--disable-gpu', '--no-sandbox',
                        '--virtual-time-budget=3000', '--dump-dom', url],
                       capture_output=True, text=True, timeout=120)
    tag = re.search(r'<body[^>]*>', r.stdout)
    if not tag:
        raise SystemExit(f'error: no <body> in the DOM for {url}:\n{r.stderr[-2000:]}')
    attrs = dict(re.findall(r'data-(\w+)="([^"]*)"', tag.group(0)))
    return {k: attrs.get(k) for k in ('selected', 'visible', 'edges')}


def shown(exe, fixture, layout, cases):
    """{case: what the page shows} for one document."""
    g = select(graph(document.loads(fixture.read_text(encoding='utf-8'))), 'hosts')
    with tempfile.TemporaryDirectory() as tmp:
        html = pathlib.Path(tmp) / 'page.html'
        html.write_text(page(g, load_layout(layout) if layout else Layout()), encoding='utf-8')
        return {case: body(exe, f'file://{html}' + (f'#{case}' if case else '')) for case in cases}


def main(argv):
    exe, failed = browser(), False
    for name, (fixture, layout, cases, expected) in PAGES.items():
        got = shown(exe, fixture, layout, cases)
        want = json.loads(expected.read_text(encoding='utf-8')) if expected.exists() else {}
        bad = [c for c in cases if got[c] != want.get(c)]
        if '--update' in argv:
            # what moved, so it can be checked by hand against the fixture
            for c in bad:
                print(f'{name}  #{c:32} {want.get(c)} -> {got[c]}')
            expected.write_text(json.dumps(got, indent=2) + '\n', encoding='utf-8')
            print(f'wrote {expected.relative_to(ROOT)}: {len(bad)} of {len(cases)} cases changed')
            continue
        for c in cases:
            print(f'{"FAIL" if c in bad else "PASS"}  {name} #{c:32} {got[c]}'
                  + (f'  expected {want.get(c)}' if c in bad else ''))
        failed |= bool(bad)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
