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
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')      # CommonMark: up to three spaces in
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
    try:
        words = shlex.split(spec)
    except ValueError as e:                 # an unclosed quote
        raise ModuleGraphError(str(e)) from None
    for w in words:
        if w.split('=', 1)[0] in COMMAND_ONLY:
            raise ModuleGraphError(f'{w.split("=", 1)[0]} belongs on the command line, not in a marker')
    if words and words[0] not in ('tree', 'hosts'):
        raise ModuleGraphError(f"`{words[0]}` can't go in Markdown; use tree or hosts")
    return PARSER.parse_args(words)


def rewrite(text, draw):
    """(new text, blocks, stale blocks): `text` with every block redrawn by
    `draw(options)`, which returns Mermaid. Markers inside a fenced code
    block are examples, not blocks. A redrawn block keeps the file's line
    endings. A mistake names its line."""
    lines = text.splitlines(keepends=True)
    out, total, stale, fence, i = [], 0, 0, None, 0
    while i < len(lines):
        bare = lines[i].rstrip()            # also drops \r\n and trailing spaces
        f = FENCE.match(bare)
        if fence:                           # inside ``` or ~~~: copied as it is
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) \
                    and not bare[f.end():].strip():
                fence = None
        elif f:
            fence = f.group(1)
        elif bare == CLOSE:
            raise ModuleGraphError(f'line {i + 1}: `{CLOSE}` with no marker open')
        elif found := OPEN.match(bare):
            end = close_of(lines, i)
            eol = '\r\n' if lines[i].endswith('\r\n') else '\n'
            try:
                drawing = draw(marker(found.group(1))).replace('\n', eol)
            except ModuleGraphError as e:
                raise ModuleGraphError(f'line {i + 1}: {e}') from None
            block = f'```mermaid{eol}{drawing}{eol}```{eol}'
            total += 1
            stale += ''.join(lines[i + 1:end]) != block
            out += [lines[i], block, lines[end]]
            i = end + 1
            continue
        out.append(lines[i])
        i += 1
    if not total:
        raise ModuleGraphError(f'no `<!-- module-graph: … -->` blocks')
    return ''.join(out), total, stale


def close_of(lines, i):
    """The line closing the block opened on line `i`."""
    for j in range(i + 1, len(lines)):
        bare = lines[j].rstrip()
        if bare == CLOSE:
            return j
        if OPEN.match(bare):
            raise ModuleGraphError(f"line {j + 1}: a second marker before line {i + 1}'s is closed")
    raise ModuleGraphError(f'line {i + 1}: no `{CLOSE}` after it')
