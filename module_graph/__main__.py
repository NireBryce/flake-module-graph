"""module-graph: draw a flake's modules tree from a module-graph document.

    module-graph tree  [DOCUMENT | -] [--flake REF] [filters]   # category -> module tree, Mermaid
    module-graph hosts [DOCUMENT | -] [--flake REF] [filters]   # hosts -> what they include, Mermaid
    module-graph dot   [DOCUMENT | -] [--flake REF] [filters] [--view tree|hosts]   # Graphviz
    module-graph html  [DOCUMENT | -] [--flake REF] [filters]   # the hosts view as an interactive page

The document is a file, `-` for stdin, or --flake REF to run
`nix eval --json REF` (REF without `#` means REF#moduleGraph, as dirs-as-categories
publishes it). --config FILE sets where areas go (layout.py).
"""
import argparse
import pathlib
import subprocess
import sys

from . import document
from .dot import dot
from .layout import WRAP, Layout, load_layout
from .mermaid import mermaid
from .model import graph, select
from .page import page


def read(a, run):
    if a.flake is not None:
        if a.document is not None:
            raise SystemExit('error: give a DOCUMENT or --flake, not both')
        return document.from_flake(a.flake, run)
    if a.document is None:
        raise SystemExit('error: give a DOCUMENT (a file, or - for stdin) or --flake REF')
    text = sys.stdin.read() if a.document == '-' else pathlib.Path(a.document).read_text()
    return document.loads(text)


def main(argv=None, run=subprocess.run):
    ap = argparse.ArgumentParser(prog='module-graph', description=__doc__.split('\n\n')[0])
    ap.add_argument('cmd', choices=['tree', 'hosts', 'dot', 'html'])
    ap.add_argument('document', nargs='?', help='a module-graph JSON file, or - for stdin')
    ap.add_argument('--flake', metavar='REF', help='evaluate REF (default attribute: moduleGraph)')
    ap.add_argument('--config', metavar='FILE', help='TOML file with a [layout] table')
    ap.add_argument('--category', help='only this category and what is nested in it')
    ap.add_argument('--depth', type=int, help='folder levels below the roots')
    ap.add_argument('--categories-only', action='store_true', help='leave out modules and plain folders')
    ap.add_argument('--view', choices=['tree', 'hosts'], default='tree', help='for dot: which graph')
    ap.add_argument('--wrap', type=int, default=WRAP,
                    help=f'hosts view: categories per row in a shared area (default {WRAP}; 0: one row)')
    a = ap.parse_args(argv)
    layout = load_layout(a.config) if a.config else Layout()
    view = a.view if a.cmd == 'dot' else 'hosts' if a.cmd == 'html' else a.cmd
    sub = select(graph(read(a, run)), view, a.category, a.depth, a.categories_only)
    if a.cmd == 'html':
        print(page(sub, layout))
    elif a.cmd == 'dot':
        print(dot(sub, a.wrap, layout))
    else:
        print(mermaid(sub, a.wrap, layout))
    return 0


if __name__ == '__main__':
    sys.exit(main())
