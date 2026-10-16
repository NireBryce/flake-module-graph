"""Reading a module-graph document (format version 1).

dirs-as-categories publishes one as `flake.moduleGraph`; any other tool can write
one. doc/format.md in dirs-as-categories is the format. Only what the graph needs
is checked here: the version, and that the fields it reads have the right
shape, so a wrong document fails with a message rather than a traceback.
"""
import json
import subprocess

VERSION = 1


def fail(msg):
    raise SystemExit(f'error: module-graph document: {msg}')


def check(doc):
    if not isinstance(doc, dict):
        fail('expected a JSON object')
    if doc.get('version') != VERSION:
        fail(f'version {doc.get("version")!r}; this tool reads version {VERSION}')
    for key in ('categories', 'modules'):
        if not isinstance(doc.get(key), dict):
            fail(f'`{key}` must be an object')
    for name, c in doc['categories'].items():
        if not isinstance(c, dict) or not isinstance(c.get('dir'), str):
            fail(f'categories.{name}: needs a string `dir`')
    for name, m in doc['modules'].items():
        if not (isinstance(m, dict) and isinstance(m.get('path'), str)
                and isinstance(m.get('classes'), list)):
            fail(f'modules.{name}: needs a string `path` and a list `classes`')
    for key in ('includes', 'enables'):
        for name, per in (doc.get(key) or {}).items():
            if not (isinstance(per, dict) and all(isinstance(v, list) for v in per.values())):
                fail(f'{key}.{name}: must map classes to lists of names')
    return doc


def loads(text):
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        fail(f'not JSON ({e})')
    return check(doc)


def from_flake(ref, run=subprocess.run):
    """The document a flake publishes: `nix eval --json <ref>`, where a ref
    without `#` means `<ref>#moduleGraph`."""
    if '#' not in ref:
        ref += '#moduleGraph'
    try:
        r = run(['nix', 'eval', '--json', ref], capture_output=True, text=True)
    except FileNotFoundError:
        fail('nix is not installed')
    if r.returncode:
        lines = r.stderr.strip().splitlines()
        fail(f'nix eval {ref} failed: {lines[-1] if lines else f"exit {r.returncode}"}')
    return loads(r.stdout)
