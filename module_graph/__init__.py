"""Draw a flake's modules tree from a module-graph document.

Every command runs the same four steps, one module each:

    document.py   read and check the JSON document (from a file, stdin, or `nix eval`)
    model.py      graph(): nodes and edges for the whole tree
                  select(): the part one drawing shows (--category, --depth, ...)
    layout.py     where things go: containers, rows, the [layout] settings
    mermaid.py, dot.py, page.py
                  draw it, in the colours look.py sets for every renderer

__main__.py is the command line that joins them.
"""
# The release this is, or will be: bumped by skill `release`, read by
# pyproject.toml and `module-graph --version`.
__version__ = '0.1.0'

from .document import from_flake, loads
from .dot import dot
from .layout import Layout, load_layout
from .mermaid import mermaid
from .model import graph, select
from .page import page, page_data

__all__ = ['from_flake', 'loads', 'dot', 'Layout', 'load_layout', 'mermaid', 'graph',
           'select', 'page', 'page_data']
