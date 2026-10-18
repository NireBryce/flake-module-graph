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

from . import __version__, document
from .dot import dot
from .layout import WRAP, Layout, load_layout
from .mermaid import mermaid
from .model import graph, select
from .page import page


# Which graph each command draws: `dot` draws either, by --view.
VIEW = {'tree': 'tree', 'hosts': 'hosts', 'html': 'hosts'}


def read(args, run):
    """The document: from --flake, a file, or stdin (`-`)."""
    if args.flake is not None:
        if args.document is not None:
            raise SystemExit('error: give a DOCUMENT or --flake, not both')
        return document.from_flake(args.flake, run)
    if args.document is None:
        raise SystemExit('error: give a DOCUMENT (a file, or - for stdin) or --flake REF')
    if args.document == '-':
        return document.loads(sys.stdin.read())
    return document.loads(pathlib.Path(args.document).read_text())


def main(argv=None, run=subprocess.run):
    """The command line. `run` stands in for subprocess.run in tests."""
    ap = argparse.ArgumentParser(prog='module-graph', description=__doc__.split('\n\n')[0])
    ap.add_argument('--version', action='version', version=f'module-graph {__version__}')
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
    args = ap.parse_args(argv)
    layout = load_layout(args.config) if args.config else Layout()
    view = args.view if args.cmd == 'dot' else VIEW[args.cmd]
    model = graph(read(args, run))
    drawn = select(model, view, args.category, args.depth, args.categories_only)
    if args.cmd == 'html':
        print(page(drawn, layout))
    elif args.cmd == 'dot':
        print(dot(drawn, args.wrap, layout))
    else:
        print(mermaid(drawn, args.wrap, layout))
    return 0


if __name__ == '__main__':
    sys.exit(main())
