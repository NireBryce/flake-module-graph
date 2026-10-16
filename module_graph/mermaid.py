"""Mermaid flowcharts: the tree view left to right, the hosts view top-down."""
from .layout import WRAP, Layout, arrows, boxes, hosts_view, layout_links, upward, walk
from .look import ALERT, INK, LINE, PALETTE, QUIET, box_look, hues, parts, style

INIT = ('%%{init: {"theme": "base", "themeVariables": {"fontFamily": '
        '"ui-sans-serif, system-ui, sans-serif", "fontSize": "14px", '
        f'"lineColor": "{LINE}"}}, "flowchart": {{"curve": "basis", '
        '"nodeSpacing": 24, "rankSpacing": 80, "padding": 14}}}%%')


def esc(text):
    return text.replace('"', '#quot;')


def mermaid(g, wrap=WRAP, layout=Layout()):
    ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
    shape = {'category': '({})', 'folder': '[{}]', 'module': '([{}])', 'aggregate': '[[{}]]',
             'missing': '{{{{{}}}}}', 'area': '[{}]'}

    def card(i):
        n = g.nodes[i]
        title, sub = parts(n)
        text = f'<b>{title}</b>' + (f'<br/><i>{sub}</i>' if sub else '')
        return f'{ids[i]}{shape[n.kind].format(chr(34) + esc(text) + chr(34))}'

    hue, drawn, tree = hues(g), arrows(g), boxes(g)
    index = {b.id: b for b in walk(tree) if b.kind == 'category'}
    sid, styles = {}, []

    def emit(b, pad):
        if not (b.items or b.subs):
            return []
        name = sid[b.id] = f'g{len(sid)}'
        if b.kind == 'category':
            title, sub = parts(g.nodes[b.id])
            text = f'<b>{title}</b>' + (f' · <i>{sub}</i>' if sub else '')
        else:
            text = g.nodes[b.id].label if b.kind == 'area' else 'hosts and home'
        fill, line, dashed, alert = box_look(g, b)
        styles.append(f'    style {name} fill:{fill},stroke:{line},'
                      f'color:{INK if b.kind == "category" else QUIET}'
                      + (',stroke-width:2.5px' if alert else '')
                      + (',stroke-dasharray:5 3' if dashed else ''))
        out = [f'{pad}subgraph {name}["{esc(text)}"]']
        out += [f'{pad}    {card(m)}' for m in b.items]
        for s in b.subs:
            out += emit(s, pad + '    ')
        return out + [f'{pad}end']

    def end(i):
        return sid[i] if i in index else ids[i]

    lines = [INIT, f'flowchart {"TB" if hosts_view(g) else "LR"}']
    # Mermaid stacks unconnected containers bottom-up; reversed, the areas
    # read top-down in the order the tree lists them.
    for b in (tree[::-1] if not drawn else tree):
        lines += emit(b, '    ')
    inside = {m for b in walk(tree) for m in b.items}
    lines += [f'    {card(i)}' for i, n in g.nodes.items()
              if i not in inside and i not in index and n.kind != 'area']
    # Mermaid has no reversed arrow and ranks by edge direction, so an
    # upward import is a plain `category --- host` line in the host's
    # colour: written category-first, it ranks the category above. (An
    # invisible `category ~~~ host` plus the real arrow forms a cycle per
    # pair, and dagre breaks such cycles inconsistently.)
    by_hue = {}
    for k, e in enumerate(drawn):
        a, b = end(e.src), end(e.dst)
        if upward(g, e, layout):
            lines.append(f'    {b} --- {a}')
            by_hue.setdefault(hue[e.src], []).append(str(k))
        elif e.kind == 'contains':
            # into a category: dotted, since it is importable on its own too
            nested = g.nodes[e.dst].kind == 'category'
            lines.append(f'    {a} {"-.->" if nested else "-->"} {b}')
        elif e.kind == 'enables':
            # dashed: not an import -- a module the host imports turns it on
            lines.append(f'    {a} -. enables .-> {b}')
            by_hue.setdefault(hue[e.src], []).append(str(k))
        else:
            lines.append(f'    {a} --> {b}')
            by_hue.setdefault(hue[e.src], []).append(str(k))
    # Layout links last: every linkStyle index above is already fixed. In
    # Mermaid each `~` past three is one more rank between the two ends.
    lines += [f'    {ids[a]} {"~" * (minlen + 2)} {ids[b]}' for a, b, minlen in layout_links(g, wrap, layout)]
    lines += [f'    linkStyle {",".join(v)} stroke:{h},stroke-width:1.5px'
              for h, v in by_hue.items()]
    lines += styles
    lines += [f'    style {ids[a]} stroke:{h},stroke-width:2px' for a, h in hue.items()]
    for kind in PALETTE:
        fill, line = PALETTE[kind]
        lines.append(f'    classDef {kind} fill:{fill},stroke:{line},color:{INK},stroke-width:1.5px')
    lines += [f'    classDef orphan fill:{ALERT[0]},stroke:{ALERT[1]},color:{INK},stroke-width:2.5px',
              '    classDef bymodule stroke-dasharray:5 3']
    members = {}
    for i, n in g.nodes.items():
        if n.kind == 'area' or i in index:
            continue
        for s in style(n):
            members.setdefault(s, []).append(ids[i])
    lines += [f'    class {",".join(v)} {k}' for k, v in members.items()]
    return '\n'.join(lines)
