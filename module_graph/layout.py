"""Where things go: the placement settings, and the container tree and rank
links both static renderers lay out from.

Placement is per repository, so it comes from a TOML file (--config), and
with none every area is a shared area in alphabetical order:

    [layout]
    top    = ["hosts", "users"]        # static diagrams: drawn above the hosts
    behind = ["hosts"]                 # page: before the hosts
    beside = ["services"]              # page: next to the hosts
    far    = ["users"]                 # page: the far end, past the shared areas
    shared = ["shared", "packages"]    # page: these first, in this order
"""
import tomllib
from dataclasses import dataclass, field

# The shared areas below the hosts wrap their categories at this many per
# row (--wrap; 0 for one row).
WRAP = 5


@dataclass(frozen=True)
class Layout:
    top: tuple = ()          # static hosts views: areas drawn above the hosts
    behind: tuple = ()       # page: areas before the hosts
    beside: tuple = ()       # page: areas next to the hosts
    far: tuple = ()          # page: areas at the far end
    shared: tuple = ()       # page: shared areas to put first, in this order


def load_layout(path):
    """A Layout from the [layout] table of a TOML file."""
    with open(path, 'rb') as f:
        table = tomllib.load(f).get('layout', {})
    unknown = set(table) - set(Layout.__dataclass_fields__)
    if unknown:
        raise SystemExit(f'error: {path}: unknown [layout] keys: {", ".join(sorted(unknown))}')
    for key, value in table.items():
        if not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            raise SystemExit(f'error: {path}: [layout] {key} must be a list of area names')
    return Layout(**{k: tuple(v) for k, v in table.items()})


@dataclass
class Box:
    """A container a diagram draws: an area, the host and home entry points,
    or a category that holds a nested category."""
    id: str                  # the area or category node id; 'grp:entry' for the hosts
    kind: str                # area | category | entry
    items: list              # node ids drawn directly inside
    subs: list               # Boxes nested inside
    top: list = field(default_factory=list)   # direct children, in order: what wrapping lays out in rows


def children_of(g):
    """id -> the ids it `contains`, in edge order (select() has already
    sorted them)."""
    kids = {}
    for e in g.edges:
        if e.kind == 'contains':
            kids.setdefault(e.src, []).append(e.dst)
    return kids


def boxed(g):
    """Categories drawn as a container rather than a card: those with a
    nested category drawn directly under them. Their own `contains` edges
    become the containment, as an area's do."""
    kids = children_of(g)
    return {i for i, n in g.nodes.items() if n.kind == 'category'
            and any(g.nodes[k].kind == 'category' for k in kids.get(i, []))}


def boxes(g):
    """The container tree: one Box per area, holding everything beneath it
    -- a boxed category as a nested Box, anything else as an item -- then
    the host and home entry points together, in the hosts view."""
    kids, cats = children_of(g), boxed(g)

    def build(i):
        b = Box(i, g.nodes[i].kind, [], [], list(kids.get(i, [])))
        queue = list(kids.get(i, []))
        while queue:
            m = queue.pop(0)
            if m in cats:
                b.subs.append(build(m))
            else:
                b.items.append(m)
                queue += kids.get(m, [])
        return b

    out = [build(i) for i, n in g.nodes.items() if n.kind == 'area']
    entry = [i for i, n in g.nodes.items() if n.kind == 'aggregate']
    if entry:
        out.append(Box('grp:entry', 'entry', entry, [], entry))
    return out


def walk(tree):
    for b in tree:
        yield b
        yield from walk(b.subs)


def anchor(i, box_of):
    """The card an edge or a layout link attaches to for `i`. A boxed
    category has no card of its own -- it is drawn as a box -- so it is
    reached through the first thing in its box (`box_of`: id -> Box)."""
    while i in box_of:
        i = box_of[i].top[0]
    return i


def arrows(g):
    """The edges drawn as arrows: everything but the containment an area or
    a boxed category draws as a box."""
    inside = boxed(g)
    return [e for e in g.edges
            if not (e.kind == 'contains' and (g.nodes[e.src].kind == 'area' or e.src in inside))]


def hosts_view(g):
    return any(n.kind == 'aggregate' for n in g.nodes.values())


def area_of(i):
    return i.split(':', 1)[1].split('/')[0]


def upward(g, e, layout):
    """An import into a category under one of layout.top: drawn pointing up.
    The hosts view runs top-down, imports flowing down from the hosts, except
    into the areas a host or user owns, drawn above them: they are what a
    host and its user are, not something pulled in from the shared tree."""
    return (e.kind == 'imports' and g.nodes[e.dst].kind == 'category'
            and area_of(e.dst) in layout.top)


def layout_links(g, wrap=WRAP, layout=Layout()):
    """[(first host, card, rank)]: invisible links that place every card in
    a shared area exactly `rank` ranks below the hosts -- shared by both
    renderers so they cannot disagree.

    Each shared area's categories are cut into rows of `wrap`; row r sits
    below row r-1 by that row's tallest entry, where a card is one rank and
    a boxed category the sum of its own rows (a box takes no rank of its
    own; its rows start where it does). Every card gets a link, not only
    the first of a row: a card in a box beside the one its host edges land
    on has no other edge at all, and Graphviz floats an unconstrained node
    to the top rank. The same link holds a category nothing imports whole
    below the hosts instead of beside them."""
    if not hosts_view(g):
        return []
    tree = boxes(g)
    box_of = {b.id: b for b in walk(tree) if b.kind == 'category'}
    first = next(i for i, n in g.nodes.items() if n.kind == 'aggregate')

    def rows(items):
        if wrap <= 0:
            return [items] if items else []
        return [items[k:k + wrap] for k in range(0, len(items), wrap)]

    def height(i):
        if i not in box_of:
            return 1
        return sum(max(height(c) for c in r) for r in rows(box_of[i].top))

    links = []

    def place(top, rank):
        for row in rows(top):
            for i in row:
                if i in box_of:
                    place(box_of[i].top, rank)
                else:
                    links.append((first, i, rank))
            rank += max(height(i) for i in row)

    for b in tree:
        if b.kind == 'area' and g.nodes[b.id].label not in layout.top:
            place(b.top, 1)
    return links
