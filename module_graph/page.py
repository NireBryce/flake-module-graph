"""`html`: the hosts view as one self-contained interactive page.

Python decides what is in the model and how each kind looks -- the same
PALETTE, hues and parts() the other renderers use -- and the page
(page.html) only lays it out and filters it, so it cannot disagree with them.
"""
import json
import pathlib

from .errors import ModuleGraphError
from .layout import Layout, children_of
from .look import ALERT, BOX_FILL, PALETTE, colours, hues, parts

TEMPLATE = pathlib.Path(__file__).with_name('page.html')
PLACEHOLDER = '/*@DATA@*/null'


def page_data(g, layout=Layout()):
    """The page's model, from a hosts-view graph: areas holding everything
    beneath them as a tree, each card or box with its `look`, each area with
    its `place` (behind, beside, user -- the far end -- or shared; shared
    ones in layout.shared's order, then the rest alphabetically); the hosts
    and the home configurations they enable ("homes": aggregates another
    aggregate enables), each with its hue and number; what each imports;
    and which homes each host enables. A name a host includes that the
    document doesn't know goes in its own 'not found' area."""
    kids, hue = children_of(g), hues(g)

    def look(n, boxed):
        """How the page draws a card or box, from the colour standard: its
        fill and outline, and whether it is outlined as an alert (nothing
        reaches it) or dashed (reached only through a module named alone)."""
        fill, line = colours(n)
        alert = colours(n) == ALERT
        if boxed:       # a category holding categories, drawn as a box
            fill = ALERT[0] if alert else BOX_FILL
        return {'fill': fill, 'line': line, 'alert': alert, 'dashed': n.status == 'by-module'}

    def node(i):
        n = g.nodes[i]
        title, sub = parts(n)
        out = {'id': i, 'kind': n.kind, 'title': title, 'sub': sub}
        if n.kind == 'category':
            out['status'] = n.status
        children = [node(c) for c in kids.get(i, []) if c in g.nodes]
        if n.kind != 'area':
            out['look'] = look(n, boxed=bool(children) and n.kind == 'category')
        if children:
            out['children'] = children
        return out

    areas = []
    for i, n in g.nodes.items():
        if n.kind == 'area' and kids.get(i):
            area = node(i)
            area['place'] = ('behind' if n.label in layout.behind
                             else 'beside' if n.label in layout.beside
                             else 'user' if n.label in layout.far else 'shared')
            areas.append(area)
    rank = {name: k for k, name in enumerate(layout.shared)}
    areas.sort(key=lambda a: (rank.get(a['title'], len(rank)), a['title']))
    missing = [i for i, n in g.nodes.items() if n.kind == 'missing']
    if missing:
        areas.append({'id': 'area:(not found)', 'kind': 'area', 'title': 'not found',
                      'sub': '', 'place': 'shared', 'children': [node(i) for i in missing]})
    enabled = {e.dst for e in g.edges if e.kind == 'enables'}

    # Each host and home also gets a number, in hue order: shown on its card
    # and in the dots of what it reaches, so they can be told apart without
    # telling the hues apart.
    mark = {a: str(k + 1) for k, a in enumerate(hue)}

    def card(a):
        title, sub = parts(g.nodes[a])
        return {'id': a, 'title': title, 'sub': sub, 'hue': hue[a], 'mark': mark[a]}

    hosts = [card(a) for a in hue if a not in enabled]
    homes = [card(a) for a in hue if a in enabled]
    imports = {a: [e.dst for e in g.edges if e.kind == 'imports' and e.src == a] for a in hue}
    enables = {a: [e.dst for e in g.edges if e.kind == 'enables' and e.src == a] for a in hue}
    style = {'palette': {k: list(v) for k, v in PALETTE.items()}, 'alert': list(ALERT),
             'boxFill': BOX_FILL}
    return {'areas': areas, 'hosts': hosts, 'homes': homes, 'imports': imports,
            'enables': enables, 'style': style}


def page(g, layout=Layout(), template=None):
    """The template with the model filled in. Every `<` in the data is
    escaped, so no name in it can carry markup or end the <script> element
    it sits in -- not even by the `<!--` ... `<script` path through the
    HTML parser, where the template's own </script> would stop closing it."""
    template = template or TEMPLATE
    data = json.dumps(page_data(g, layout), separators=(',', ':')).replace('<', '\\u003c')
    text = pathlib.Path(template).read_text(encoding='utf-8')
    if text.count(PLACEHOLDER) != 1:
        raise ModuleGraphError(f'{template} must hold {PLACEHOLDER} exactly once')
    return text.replace(PLACEHOLDER, data)
