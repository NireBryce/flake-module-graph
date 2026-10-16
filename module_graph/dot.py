"""Graphviz: areas as clusters, boxed categories as nested clusters."""
import html

from .layout import WRAP, Layout, arrows, boxes, hosts_view, layout_links, rep, upward, walk
from .look import INK, LINE, QUIET, box_look, colours, hues, parts

GRID = 4      # cards per row in an arrowless diagram


def dot(g, wrap=WRAP, layout=Layout()):
    ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
    hue, drawn, tree = hues(g), arrows(g), boxes(g)
    index = {b.id: b for b in walk(tree) if b.kind == 'category'}
    cluster = {}

    def card(i):
        n = g.nodes[i]
        title, sub = parts(n)
        fill, line = colours(n)
        label = f'<b>{html.escape(title)}</b>'
        if sub:
            label += f'<br/><font point-size="9" color="{QUIET}">{html.escape(sub)}</font>'
        attrs = [f'label=<{label}>', f'fillcolor="{fill}"',
                 f'color="{hue.get(i, line)}"']
        if n.kind == 'module':
            attrs.append('shape=box style="rounded,filled"')
        if n.kind == 'folder':
            attrs.append('shape=folder style=filled')
        if n.kind == 'aggregate':
            attrs.append('shape=box style="rounded,filled" penwidth=1.6')
        if n.kind == 'category' and n.status == 'orphan':
            attrs.append('penwidth=2.5')
        if n.kind == 'category' and n.status == 'by-module':
            attrs.append('style="rounded,filled,dashed"')
        return f'{ids[i]} [{" ".join(attrs)}];'

    def emit(b, pad):
        if not (b.items or b.subs):
            return []
        name = cluster[b.id] = f'cluster_{len(cluster)}'
        fill, line, dashed, alert = box_look(g, b)
        if b.kind == 'category':
            title, sub = parts(g.nodes[b.id])
            label = (f'<b>{html.escape(title)}</b>'
                     + (f'  <font point-size="9" color="{QUIET}">{html.escape(sub)}</font>' if sub else ''))
        else:
            text = g.nodes[b.id].label if b.kind == 'area' else 'hosts and home'
            label = f'<font color="{QUIET}" point-size="10">{html.escape(text)}</font>'
        out = [f'{pad}subgraph {name} {{',
               f'{pad}    label=<{label}>;',
               f'{pad}    style="rounded,filled{",dashed" if dashed else ""}"; fillcolor="{fill}"; '
               f'color="{line}"; penwidth={2.5 if alert else 1.2}; margin=14;']
        out += [f'{pad}    {card(m)}' for m in b.items]
        if not drawn:
            out += [f'{pad}    {ids[x]} -> {ids[y]} [style=invis];'
                    for x, y in zip(b.items, b.items[GRID:])]
        for s in b.subs:
            out += emit(s, pad + '    ')
        return out + [f'{pad}}}']

    def edge(src, dst, attrs):
        """An edge whose ends may be boxes: drawn to the box's first node
        and clipped at the box (compound=true)."""
        attrs = list(attrs)
        if src in index:
            attrs.append(f'ltail={cluster[src]}')
        if dst in index:
            attrs.append(f'lhead={cluster[dst]}')
        a, b = ids[rep(src, index)], ids[rep(dst, index)]
        return f'    {a} -> {b}' + (f' [{" ".join(attrs)}];' if attrs else ';')

    # With no arrows (areas and their categories only) a left-to-right layout
    # stacks every card in one column; top-down plus invisible edges every
    # GRID cards lays each area out as a grid instead. The hosts view runs
    # top-down (layout.top above the hosts, see upward()).
    lines = ['digraph modules {',
             f'    rankdir={"LR" if drawn and not hosts_view(g) else "TB"}; bgcolor="white"; nodesep=0.22; '
             f'ranksep={0.9 if drawn else 0.3}; splines=true; newrank=true; compound=true;',
             f'    node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 '
             f'fontcolor="{INK}" penwidth=1.3 margin="0.16,0.08"];',
             f'    edge [color="{LINE}" fontname="Helvetica" fontsize=9 fontcolor="{QUIET}" '
             f'arrowsize=0.7];']
    for b in tree:
        lines += emit(b, '    ')
    inside = {m for b in walk(tree) for m in b.items}
    lines += [f'    {card(i)}' for i, n in g.nodes.items()
              if i not in inside and i not in index and n.kind != 'area']
    lines += [f'    {ids[a]} -> {ids[b]} [style=invis minlen={minlen}];'
              for a, b, minlen in layout_links(g, wrap, layout)]
    if hosts_view(g):
        # One row of hosts. Without it a host whose imports all sit in a
        # lower wrapped row is pulled down to them -- Graphviz shortens
        # edges, it does not keep rows.
        lines.append('    { rank=same; ' + ' '.join(
            ids[i] for i, n in g.nodes.items() if n.kind == 'aggregate') + ' }')
    for e in drawn:
        if e.kind == 'contains':
            nested = g.nodes[e.dst].kind == 'category'
            lines.append(edge(e.src, e.dst, ['style=dotted'] if nested else []))
        elif e.kind == 'enables':
            lines.append(edge(e.src, e.dst, [f'color="{hue[e.src]}" style=dashed penwidth=1.2',
                                             'label="enables"', f'fontcolor="{hue[e.src]}"']))
        elif upward(g, e, layout):
            # reversed for ranking, arrowhead kept on the category
            lines.append(edge(e.dst, e.src, [f'dir=back color="{hue[e.src]}" penwidth=1.2']))
        else:
            lines.append(edge(e.src, e.dst, [f'color="{hue[e.src]}" penwidth=1.2']))
    lines.append('}')
    return '\n'.join(lines)
