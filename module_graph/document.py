"""Reading a module-graph document (format version 1).

dirs-as-categories publishes one as `flake.moduleGraph`; any other tool can write
one. doc/format.md in dirs-as-categories is the format. Only what the graph needs
is checked here: the version, and that the fields it reads have the right
shape, so a wrong document fails with a message rather than a traceback.
"""
import json
import subprocess

from .errors import ModuleGraphError

VERSION = 1


def fail(msg):
    raise ModuleGraphError(f'module-graph document: {msg}')


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


# `nix eval` and flakes are still experimental features of Nix, off in a
# fresh install. Turning them on for this one command changes nothing where
# they are already on.
NIX = ['nix', '--extra-experimental-features', 'nix-command flakes']

# (text in Nix's error, what to do about it), for the mistakes someone new
# to flakes makes first. `{attr}` is the attribute asked for.
HINTS = [
    ('does not provide attribute',
     "this flake doesn't publish `{attr}`. A flake using dirs-as-categories "
     'publishes `moduleGraph` (https://github.com/NireBryce/dirs-as-categories); '
     'another attribute is --flake REF#ATTR'),
    ('is not tracked by Git',
     'a flake in a git repository sees only the files git knows about: '
     '`git add` the new files (no commit needed) and run this again'),
]


def nix_cause(stderr):
    """The innermost cause in Nix's error output. Nix prints the outermost
    context first and the cause last, each as an `error:` line, around
    source excerpts and advice: the last `error:` line with text is the
    cause. Output without one gives its last line."""
    lines = [l.strip() for l in stderr.strip().splitlines()]
    causes = [l.removeprefix('error:').strip() for l in lines if l.startswith('error:')]
    causes = [c for c in causes if c]
    return causes[-1] if causes else (lines[-1] if lines else '')


def from_flake(ref, run=subprocess.run):
    """The document a flake publishes: `nix eval --json <ref>`, where a ref
    without `#` means `<ref>#moduleGraph`."""
    if '#' not in ref:
        ref += '#moduleGraph'
    try:
        r = run([*NIX, 'eval', '--json', ref], capture_output=True, text=True)
    except FileNotFoundError:
        fail('nix is not installed')
    if r.returncode:
        cause = nix_cause(r.stderr) or f'exit {r.returncode}'
        hint = next((h for text, h in HINTS if text in r.stderr),
                    f"run `nix eval --json {ref}` to see Nix's whole error")
        fail(f'nix eval {ref} failed: {cause}\n  hint: {hint.format(attr=ref.split("#", 1)[1])}')
    return loads(r.stdout)
