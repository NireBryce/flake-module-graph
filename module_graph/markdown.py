"""`markdown`: drawings kept inside a Markdown file, rewritten in place.

A drawing in docs is a copy of the tree, and copies drift. This keeps each
one between two markers that say how to draw it:

    <!-- module-graph: tree --depth 1 --categories-only -->
    ```mermaid
    ...
    ```
    <!-- /module-graph -->

`module-graph markdown --file README.md` redraws every block from the
document; `--check` changes nothing and fails if any block would change, so
a CI step or a flake check (lib.checkMarkdown in flake.nix) catches a stale
drawing. A marker takes `tree` or `hosts` and the filters; where the
document comes from and the layout file are the command's, shared by every
block.
"""
import argparse
import re
import shlex

from .errors import ModuleGraphError
from .layout import WRAP

OPEN = re.compile(r'^<!-- module-graph: (.*?) -->$')
CLOSE = '<!-- /module-graph -->'
# Options that pick the document, the layout or the output: one per command.
COMMAND_ONLY = ('--flake', '--config', '--file', '--check', '-o', '--output')


class MarkerParser(argparse.ArgumentParser):
    """Reports a bad marker as a ModuleGraphError instead of exiting."""

    def error(self, message):
        raise ModuleGraphError(message)


PARSER = MarkerParser(prog='marker', add_help=False)
PARSER.add_argument('view')
PARSER.add_argument('--category')
PARSER.add_argument('--depth', type=int)
PARSER.add_argument('--categories-only', action='store_true')
PARSER.add_argument('--wrap', type=int, default=WRAP)


def marker(spec):
    """The options a marker's `spec` gives, checked."""
    words = shlex.split(spec)
    for w in words:
        if w.split('=', 1)[0] in COMMAND_ONLY:
            raise ModuleGraphError(f'{w.split("=", 1)[0]} belongs on the command line, not in a marker')
    if words and words[0] not in ('tree', 'hosts'):
        raise ModuleGraphError(f"`{words[0]}` can't go in Markdown; use tree or hosts")
    return PARSER.parse_args(words)


def rewrite(text, draw):
    """(new text, blocks, stale blocks): `text` with every block redrawn by
    `draw(options)`, which returns Mermaid. A mistake names its line."""
    lines = text.splitlines(keepends=True)
    out, total, stale, i = [], 0, 0, 0
    while i < len(lines):
        found = OPEN.match(lines[i].rstrip('\n'))
        if not found:
            out.append(lines[i])
            i += 1
            continue
        end = next((j for j in range(i + 1, len(lines)) if lines[j].rstrip('\n') == CLOSE), None)
        try:
            if end is None:
                raise ModuleGraphError(f'no `{CLOSE}` after it')
            block = f'```mermaid\n{draw(marker(found.group(1)))}\n```\n'
        except ModuleGraphError as e:
            raise ModuleGraphError(f'line {i + 1}: {e}') from None
        total += 1
        stale += ''.join(lines[i + 1:end]) != block
        out += [lines[i], block, lines[end]]
        i = end + 1
    return ''.join(out), total, stale
