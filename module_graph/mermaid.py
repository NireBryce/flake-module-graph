"""Mermaid flowcharts: the tree view left to right, the hosts view top-down.

A flowchart here is, in order: the init line and direction, the containers
(`subgraph`) with their cards, the cards outside every container, the
arrows, the invisible layout links, then the styles. The order matters:
`linkStyle` colours arrows by their position among all links, so the
layout links come after every arrow they must not shift.
"""
from .layout import WRAP, Layout, arrows, boxes, hosts_view, layout_links, upward, walk
from .look import ALERT, INK, LINE, PALETTE, QUIET, box_look, hues, parts, style

INIT = ('%%{init: {"theme": "base", "themeVariables": {"fontFamily": '
        '"ui-sans-serif, system-ui, sans-serif", "fontSize": "14px", '
        f'"lineColor": "{LINE}"}}, "flowchart": {{"curve": "basis", '
        '"nodeSpacing": 24, "rankSpacing": 80, "padding": 14}}}%%')

# A card's shape, by kind: Mermaid's bracket pairs around the label.
SHAPE = {'category': '({})', 'folder': '[{}]', 'module': '([{}])', 'aggregate': '[[{}]]',
         'missing': '{{{{{}}}}}', 'area': '[{}]'}


def esc(text):
    return text.replace('"', '#quot;')


def mermaid(g, wrap=WRAP, layout=Layout()):
    card_id = {i: f'n{k}' for k, i in enumerate(g.nodes)}
    hue, tree = hues(g), boxes(g)
    box_of = {b.id: b for b in walk(tree) if b.kind == 'category'}
    box_id, box_styles = {}, []

    def card(i):
        n = g.nodes[i]
        title, sub = parts(n)
        text = f'<b>{title}</b>' + (f'<br/><i>{sub}</i>' if sub else '')
        return f'{card_id[i]}{SHAPE[n.kind].format(chr(34) + esc(text) + chr(34))}'

    def container(b, pad):
        """A box as a `subgraph`, its cards and nested boxes inside."""
        if not (b.items or b.subs):
            return []
        name = box_id[b.id] = f'g{len(box_id)}'
        if b.kind == 'category':
            title, sub = parts(g.nodes[b.id])
            text = f'<b>{title}</b>' + (f' · <i>{sub}</i>' if sub else '')
        else:
            text = g.nodes[b.id].label if b.kind == 'area' else 'hosts and home'
        fill, line, dashed, alert = box_look(g, b)
        box_styles.append(f'    style {name} fill:{fill},stroke:{line},'
                          f'color:{INK if b.kind == "category" else QUIET}'
                          + (',stroke-width:2.5px' if alert else '')
                          + (',stroke-dasharray:5 3' if dashed else ''))
        out = [f'{pad}subgraph {name}["{esc(text)}"]']
        out += [f'{pad}    {card(m)}' for m in b.items]
        for s in b.subs:
            out += container(s, pad + '    ')
        return out + [f'{pad}end']

    def end(i):
        """What an arrow at `i` attaches to: a box_of category's subgraph,
        else the card."""
        return box_id[i] if i in box_of else card_id[i]

    drawn = arrows(g)
    lines = [INIT, f'flowchart {"TB" if hosts_view(g) else "LR"}']
    # Mermaid stacks unconnected containers bottom-up; reversed, the areas
    # read top-down in the order the tree lists them.
    for b in (tree[::-1] if not drawn else tree):
        lines += container(b, '    ')
    inside = {m for b in walk(tree) for m in b.items}
    lines += [f'    {card(i)}' for i, n in g.nodes.items()
              if i not in inside and i not in box_of and n.kind != 'area']
    arrow_lines, coloured = arrow_links(g, drawn, end, hue, layout)
    lines += arrow_lines
    # Layout links last: every linkStyle index above is already fixed. In
    # Mermaid each `~` past three is one more rank between the two ends.
    lines += [f'    {card_id[a]} {"~" * (minlen + 2)} {card_id[b]}'
              for a, b, minlen in layout_links(g, wrap, layout)]
    lines += [f'    linkStyle {",".join(v)} stroke:{h},stroke-width:1.5px'
              for h, v in coloured.items()]
    lines += box_styles
    lines += [f'    style {card_id[a]} stroke:{h},stroke-width:2px' for a, h in hue.items()]
    lines += class_lines(g, card_id, box_of)
    return '\n'.join(lines)


def arrow_links(g, drawn, end, hue, layout):
    """(lines, {hue: [link index]}): one Mermaid link per drawn edge, and
    which of them `linkStyle` colours in their host's hue."""
    lines, coloured = [], {}
    for k, e in enumerate(drawn):
        a, b = end(e.src), end(e.dst)
        if upward(g, e, layout):
            # Mermaid has no reversed arrow and ranks by edge direction, so
            # an upward import is a plain `category --- host` line in the
            # host's colour: written category-first, it ranks the category
            # above. (An invisible `category ~~~ host` plus the real arrow
            # forms a cycle per pair, and dagre breaks such cycles
            # inconsistently.)
            lines.append(f'    {b} --- {a}')
        elif e.kind == 'contains':
            # into a category: dotted, since it is importable on its own too
            nested = g.nodes[e.dst].kind == 'category'
            lines.append(f'    {a} {"-.->" if nested else "-->"} {b}')
            continue
        elif e.kind == 'enables':
            # dashed: not an import -- a module the host imports turns it on
            lines.append(f'    {a} -. enables .-> {b}')
        else:
            lines.append(f'    {a} --> {b}')
        coloured.setdefault(hue[e.src], []).append(str(k))
    return lines, coloured


def class_lines(g, card_id, box_of):
    """The `classDef`s from the colour standard, and which cards take each."""
    lines = []
    for kind, (fill, line) in PALETTE.items():
        lines.append(f'    classDef {kind} fill:{fill},stroke:{line},color:{INK},stroke-width:1.5px')
    lines += [f'    classDef orphan fill:{ALERT[0]},stroke:{ALERT[1]},color:{INK},stroke-width:2.5px',
              '    classDef bymodule stroke-dasharray:5 3']
    members = {}
    for i, n in g.nodes.items():
        if n.kind == 'area' or i in box_of:
            continue
        for s in style(n):
            members.setdefault(s, []).append(card_id[i])
    return lines + [f'    class {",".join(v)} {k}' for k, v in members.items()]
