#!/usr/bin/env python3
"""The page in a real browser: for each selection and layout, what it shows.

After every change the page writes <body data-selected data-visible
data-edges>. This renders tests/fixtures/browser.json, opens it in headless
Chromium once per case, and compares those three to
tests/expected/browser.json.

    python3 tests/browser.py             # needs chromium (or $CHROMIUM) on PATH
    python3 tests/browser.py --update    # rewrite the expected values
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from module_graph import document, graph, load_layout, page, select  # noqa: E402

FIXTURE = ROOT / 'tests' / 'fixtures' / 'browser.json'
EXPECTED = ROOT / 'tests' / 'expected' / 'browser.json'
CASES = ['', 'hosts=alpha-host', 'hosts=beta-host', 'hosts=home', 'hosts=alpha-host,beta-host',
         'hosts=nope']
CASES += [f'{c}&layout=lr' if c else 'layout=lr' for c in CASES]


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


def main(argv):
    exe = browser()
    layout = load_layout(ROOT / 'tests' / 'browser.toml')
    g = select(graph(document.loads(FIXTURE.read_text())), 'hosts')
    with tempfile.TemporaryDirectory() as tmp:
        html = pathlib.Path(tmp) / 'page.html'
        html.write_text(page(g, layout))
        got = {case: body(exe, f'file://{html}' + (f'#{case}' if case else '')) for case in CASES}
    if '--update' in argv:
        EXPECTED.write_text(json.dumps(got, indent=2) + '\n')
        print(f'wrote {EXPECTED}')
        return 0
    want = json.loads(EXPECTED.read_text())
    bad = [c for c in CASES if got[c] != want.get(c)]
    for c in CASES:
        print(f'{"FAIL" if c in bad else "PASS"}  #{c:32} {got[c]}' + (f'  expected {want.get(c)}' if c in bad else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
