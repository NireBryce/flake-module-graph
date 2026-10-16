"""The model: plain nodes and edges built from a module-graph document
(document.py), and select(), which narrows it to what one diagram draws.

Node kinds:
    area       a top-level folder of the modules tree
    category   a folder a host can include by name
    folder     a plain folder inside a category (collected only through it)
    module     a module file
    aggregate  an entry point: a module with `includes`, outside every category
               (a host, or a home configuration)
    missing    a name an aggregate includes that the document doesn't know

Edge kinds:
    contains   area/category/folder -> what sits in it
    imports    aggregate -> category or module it includes
    enables    aggregate -> aggregate that a module it reaches enables
               (a host turning on its Home Manager configuration)
"""
from dataclasses import dataclass
from pathlib import PurePosixPath

CLASS_LETTER = {'nixos': 'n', 'homeManager': 'h', 'darwin': 'd'}
CLASS_ORDER = list(CLASS_LETTER)
TOP_LEVEL = '(top level)'      # the area of a module sitting directly in the tree's root


@dataclass(frozen=True)
class Node:
    id: str
    kind: str                # area | category | folder | module | aggregate | missing
    label: str
    classes: frozenset = frozenset()
    count: int = 0           # category, folder: modules beneath, nested categories included
    status: str = ''         # category: imported | inherited | by-module | orphan


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str                # contains | imports | enables
    cls: str = ''            # imports, enables: the class of the aggregate drawing it


@dataclass
class Graph:
    nodes: dict              # id -> Node, in insertion order
    edges: list
    roots: list              # ids the `contains` tree hangs from


def class_order(doc):
    known = list(doc.get('classes') or [])
    return known + [c for c in CLASS_ORDER if c not in known]


def graph(doc):
    """The whole model from a document (format version 1)."""
    categories, modules = doc['categories'], doc['modules']
    catdir_of = {name: PurePosixPath(c['dir']) for name, c in categories.items()}
    catdirs = {d: name for name, d in catdir_of.items()}
    entries = sorted((PurePosixPath(m['path']), name, frozenset(m['classes']))
                     for name, m in modules.items())
    # A plain folder inside a category: drawn as its own node so the two
    # kinds of folder can be told apart. Folders outside every category are
    # not drawn; their modules hang off the area.
    folderdirs = sorted({d for p, _, _ in entries for d in p.parents
                         if d not in catdirs and catdirs.keys() & set(d.parents)})
    includes, enables = doc.get('includes') or {}, doc.get('enables') or {}
    all_imported = ({n for per in includes.values() for names in per.values() for n in names}
                    | {n for per in enables.values() for names in per.values() for n in names})

    nodes, edges, roots = {}, [], []

    def area(path):
        parts = path.parts
        name = parts[0] if len(parts) > 1 else TOP_LEVEL
        node = nodes.setdefault(f'area:{name}', Node(f'area:{name}', 'area', name))
        if node.id not in roots:
            roots.append(node.id)
        return node.id

    def parent_of(path):
        """Nearest enclosing category or folder, else the area."""
        for anc in path.parents:
            if anc in catdirs:
                return f'cat:{anc}'
            if anc in folderdirs:
                return f'dir:{anc}'
        return area(path)

    def beneath(d):
        return [e for e in entries if d in e[0].parents]

    def in_category(p):
        return bool(catdirs.keys() & set(p.parents))

    for d, name in sorted(catdirs.items()):
        subtree = beneath(d)
        classes = frozenset().union(*(c for _, _, c in subtree)) if subtree else frozenset()
        if name in all_imported:
            status = 'imported'
        elif any(n in all_imported for dd, n in catdirs.items() if dd in d.parents):
            status = 'inherited'
        elif any(n in all_imported for _, n, _ in subtree):
            status = 'by-module'
        else:
            status = 'orphan'
        nodes[f'cat:{d}'] = Node(f'cat:{d}', 'category', name, classes, len(subtree), status)

    for d in folderdirs:
        subtree = beneath(d)
        nodes[f'dir:{d}'] = Node(f'dir:{d}', 'folder', d.name,
                                 frozenset().union(*(c for _, _, c in subtree)), len(subtree))

    for path, name, classes in entries:
        nodes[f'mod:{path}'] = Node(f'mod:{path}', 'module', name, classes)

    # containment last, so area nodes are created in a stable order
    for nid, n in list(nodes.items()):
        if n.kind in ('category', 'folder', 'module'):
            edges.append(Edge(parent_of(PurePosixPath(nid.split(':', 1)[1])), nid, 'contains'))

    order = class_order(doc)
    aggregate_list = [(path, cls, name, includes[name][cls])
                      for path, name, _ in entries
                      if name in includes and not in_category(path)
                      for cls in order if cls in includes[name]]
    for path, cls, name, listed in aggregate_list:
        aid = f'agg:{path}:{cls}'
        nodes.setdefault(aid, Node(aid, 'aggregate', name, frozenset([cls])))
        for target in dict.fromkeys(listed):
            if target in catdir_of:
                ends = [f'cat:{catdir_of[target]}']
            elif target in modules:
                ends = [f'mod:{modules[target]["path"]}']
            else:
                ends = [f'missing:{target}']
                nodes.setdefault(ends[0], Node(ends[0], 'missing', target))
            edges += [Edge(aid, t, 'imports', cls) for t in ends]

    # enables: aggregate A -> aggregate B when a module A reaches names B in
    # its `enables`. A reaches its own module, the modules of its class under
    # a category it includes, and the modules of its class it includes by name.
    declared = {(cls, name): f'agg:{path}:{cls}' for path, cls, name, _ in aggregate_list}
    for path, cls, name, listed in aggregate_list:
        aid = f'agg:{path}:{cls}'
        reached = {name}
        for target in listed:
            if target in catdir_of:
                reached |= {n for _, n, c in beneath(catdir_of[target]) if cls in c}
            if target in modules and cls in modules[target]['classes']:
                reached.add(target)
        refs = {(c, n) for m in reached for c, names in enables.get(m, {}).items() for n in names}
        targets = sorted({declared[r] for r in refs if r in declared and declared[r] != aid})
        edges += [Edge(aid, t, 'enables', cls) for t in targets]
    return Graph(nodes, edges, roots)


def children(g):
    out = {}
    for e in g.edges:
        if e.kind == 'contains':
            out.setdefault(e.src, []).append(e.dst)
    for kids in out.values():
        kids.sort(key=lambda i: (g.nodes[i].kind != 'category', g.nodes[i].label, i))
    return out


def select(g, view='tree', category=None, depth=None, categories_only=False):
    """The subgraph a diagram draws. `view` is 'tree' (containment) or 'hosts'
    (aggregates and what they import; categories only, nesting dotted in)."""
    kids = children(g)
    if category is None:
        starts = list(g.roots)
    else:
        starts = [i for i, n in g.nodes.items() if n.kind == 'category' and n.label == category]
        if not starts:
            known = ', '.join(sorted({n.label for n in g.nodes.values() if n.kind == 'category'}))
            raise SystemExit(f"error: no category {category!r}; categories: {known}")
    keep, level, queue = [], {}, [(s, 0) for s in starts]
    while queue:
        i, d = queue.pop(0)
        if i in level or (depth is not None and d > depth):
            continue
        level[i] = d
        keep.append(i)
        queue += [(k, d + 1) for k in kids.get(i, [])]
    # Overviews leave out what a host cannot name: modules and the plain
    # folders holding them. A category nested in a hidden folder hangs off
    # the nearest directory still drawn.
    overview = categories_only or view == 'hosts'
    keep = [i for i in keep if not (overview and g.nodes[i].kind in ('module', 'folder'))]
    parent = {e.dst: e.src for e in g.edges if e.kind == 'contains'}

    def up(i, shown):
        p = parent.get(i)
        while p is not None and p not in shown:
            p = parent.get(p)
        return p

    def containment(order, shown):
        return [Edge(up(i, shown), i, 'contains') for i in order if up(i, shown) is not None]

    if view == 'tree':
        shown = set(keep)
        return Graph({i: g.nodes[i] for i in keep}, containment(keep, shown),
                     [s for s in starts if s in shown])

    # hosts: every category in range (in its area's container), plus the
    # aggregates that import into it
    shown = {i for i in keep if g.nodes[i].kind in ('category', 'area')}
    imports = []
    for e in g.edges:
        if e.kind != 'imports' or e.dst not in g.nodes:
            continue
        if g.nodes[e.dst].kind == 'module':
            # a module included by name: drawn when its category is
            if category is not None and up(e.dst, shown) is None:
                continue
            shown.add(e.dst)
            imports.append(e)
        elif e.dst in shown or (category is None and g.nodes[e.dst].kind == 'missing'):
            imports.append(e)
    used = {e.src for e in imports}
    nodes = {i: n for i, n in g.nodes.items()
             if i in shown or (n.kind == 'aggregate' and i in used)
             or (n.kind == 'missing' and any(e.dst == i for e in imports))}
    enabled = [e for e in g.edges if e.kind == 'enables'
               and e.src in nodes and e.dst in nodes]
    return Graph(nodes, containment(list(nodes), shown) + imports + enabled, [])
