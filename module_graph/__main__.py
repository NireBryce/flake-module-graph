"""module-graph: draw a flake's modules tree from a module-graph document.

    module-graph tree  [DOCUMENT | -] [--flake REF] [filters]   # category -> module tree, Mermaid
    module-graph hosts [DOCUMENT | -] [--flake REF] [filters]   # hosts -> what they include, Mermaid
    module-graph dot   [DOCUMENT | -] [--flake REF] [filters] [--view tree|hosts]   # Graphviz
    module-graph html  [DOCUMENT | -] [--flake REF] [filters]   # the hosts view as an interactive page

The document is a file, `-` for stdin, or --flake REF to run
`nix eval --json REF` (REF without `#` means REF#moduleGraph, as dirs-as-categories
publishes it). With neither, a flake.nix in the current directory is read
as --flake . (say - to read stdin instead). --config FILE sets where areas go (layout.py); -o FILE writes
the drawing there instead of stdout.
"""
import argparse
import pathlib
import subprocess
import sys

from . import __version__, document
from .dot import dot
from .layout import WRAP, Layout, load_layout
from .errors import ModuleGraphError, unreadable
from .mermaid import mermaid, warnings
from .model import graph, select
from .page import page


# Which graph each command draws: `dot` draws either, by --view.
VIEW = {'tree': 'tree', 'hosts': 'hosts', 'html': 'hosts'}


def read(args, run):
    """The document: from --flake, a file, or stdin (`-`); with none of
    them, the flake in the current directory."""
    if args.flake is not None:
        if args.document is not None:
            raise ModuleGraphError('give a DOCUMENT or --flake, not both')
        return document.from_flake(args.flake, run)
    if args.document is None:
        if pathlib.Path('flake.nix').is_file():
            if not sys.stdin.isatty():
                # something may be piped in, and `-` forgotten
                print('note: no DOCUMENT given: reading the flake here (--flake .); '
                      'to read stdin, give -', file=sys.stderr)
            return document.from_flake('.', run)
        raise ModuleGraphError('give a DOCUMENT (a file, or - for stdin) or --flake REF '
                               '(no flake.nix here to read)')
    if args.document == '-':
        return document.loads(sys.stdin.read())
    try:
        text = pathlib.Path(args.document).read_text()
    except (OSError, UnicodeDecodeError) as e:
        raise unreadable(args.document, e) from None
    return document.loads(text)


def draw(args, run):
    """The drawing the command line asks for, as text."""
    layout = load_layout(args.config) if args.config else Layout()
    view = args.view if args.cmd == 'dot' else VIEW[args.cmd]
    model = graph(read(args, run))
    drawn = select(model, view, args.category, args.depth, args.categories_only)
    if args.cmd == 'html':
        return page(drawn, layout)
    if args.cmd == 'dot':
        return dot(drawn, args.wrap, layout)
    return mermaid(drawn, args.wrap, layout)


def main(argv=None, run=subprocess.run):
    """The command line. `run` stands in for subprocess.run in tests."""
    ap = argparse.ArgumentParser(prog='module-graph', description=__doc__.split('\n\n')[0])
    ap.add_argument('--version', action='version', version=f'module-graph {__version__}')
    ap.add_argument('cmd', choices=['tree', 'hosts', 'dot', 'html'])
    ap.add_argument('document', nargs='?', help='a module-graph JSON file, or - for stdin')
    ap.add_argument('--flake', metavar='REF',
                    help='evaluate REF (default attribute: moduleGraph; default REF: . when it has a flake.nix)')
    ap.add_argument('-o', '--output', metavar='FILE', help='write the drawing to FILE, not stdout')
    ap.add_argument('--config', metavar='FILE', help='TOML file with a [layout] table')
    ap.add_argument('--category', help='only this category and what is nested in it')
    ap.add_argument('--depth', type=int, help='folder levels below the roots')
    ap.add_argument('--categories-only', action='store_true', help='leave out modules and plain folders')
    ap.add_argument('--view', choices=['tree', 'hosts'], default='tree', help='for dot: which graph')
    ap.add_argument('--wrap', type=int, default=WRAP,
                    help=f'hosts view: categories per row in a shared area (default {WRAP}; 0: one row)')
    args = ap.parse_args(argv)
    try:
        text = draw(args, run)
        if args.cmd in ('tree', 'hosts'):
            for w in warnings(text):
                print(f'warning: {w}', file=sys.stderr)
        # written only now, so a failure leaves no empty or half-written file
        if args.output:
            try:
                pathlib.Path(args.output).write_text(text + '\n')
            except OSError as e:
                raise unreadable(args.output, e) from None
        else:
            print(text)
    except ModuleGraphError as e:
        raise SystemExit(f'error: {e}') from None
    return 0


if __name__ == '__main__':
    sys.exit(main())
