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

Node ids are the kind's prefix and where the thing is, so an id read in a
test or a page URL says what it names:

    area:<name>   cat:<dir>   dir:<dir>   mod:<path>   agg:<path>:<class>   missing:<name>

The renderers number nodes in the order they are added here, so that order
is part of the output: categories by folder, then plain folders, then
modules by path, areas as they are first needed, then each aggregate
followed by any missing names it includes.
"""
from dataclasses import dataclass
from pathlib import PurePosixPath

from .errors import ModuleGraphError

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


@dataclass(frozen=True, order=True)
class Module:
    """One entry of the document's `modules`."""
    path: PurePosixPath
    name: str
    classes: frozenset


@dataclass(frozen=True)
class Host:
    """An aggregate: a module with `includes` for one class, outside every
    category. A module including for two classes is two hosts."""
    id: str
    module: Module
    cls: str
    includes: list           # the names it includes, as the document lists them


def class_order(doc):
    known = list(doc.get('classes') or [])
    return known + [c for c in CLASS_ORDER if c not in known]


def named(per_module):
    """Every name an `includes` or `enables` table mentions."""
    return {name for per_class in per_module.values() for names in per_class.values()
            for name in names}


def graph(doc):
    """The whole model from a document (format version 1)."""
    return Builder(doc).build()


class Builder:
    """Builds the Graph for one document. Each `add_*` step adds one kind of
    node or edge; build() runs them in the order that fixes node numbering."""

    def __init__(self, doc):
        self.doc = doc
        self.modules = sorted(Module(PurePosixPath(m['path']), name, frozenset(m['classes']))
                              for name, m in doc['modules'].items())
        self.dir_of_category = {name: PurePosixPath(c['dir'])
                                for name, c in doc['categories'].items()}
        self.category_at = {d: name for name, d in self.dir_of_category.items()}
        # A plain folder inside a category: drawn as its own node so the two
        # kinds of folder can be told apart. Folders outside every category
        # are not drawn; their modules hang off the area.
        self.folders = sorted({d for m in self.modules for d in m.path.parents
                               if d not in self.category_at and self.in_category(d)})
        self.is_folder = set(self.folders)     # parent() asks once per level per node
        # folder -> the modules anywhere under it, in path order. Built once:
        # asking each module "is this folder above you?" per folder took
        # minutes on a few thousand modules.
        self.under = {}
        for m in self.modules:
            for d in m.path.parents:
                self.under.setdefault(d, []).append(m)
        self.includes = doc.get('includes') or {}
        self.enables = doc.get('enables') or {}
        self.reached_by_name = named(self.includes) | named(self.enables)
        self.nodes, self.edges, self.roots = {}, [], []

    def build(self):
        self.add_categories()
        self.add_folders()
        self.add_modules()
        self.add_containment()
        hosts = self.hosts()
        self.add_hosts_and_imports(hosts)
        self.add_enables(hosts)
        return Graph(self.nodes, self.edges, self.roots)

    # -- where things are

    def in_category(self, path):
        return any(d in self.category_at for d in path.parents)

    def beneath(self, d):
        """The modules anywhere under folder `d`."""
        return self.under.get(d, [])

    def area(self, path):
        """The id of the area `path` sits in, adding it on first use."""
        name = path.parts[0] if len(path.parts) > 1 else TOP_LEVEL
        aid = f'area:{name}'
        if aid not in self.nodes:
            self.nodes[aid] = Node(aid, 'area', name)
            self.roots.append(aid)
        return aid

    def parent(self, path):
        """The nearest category or plain folder holding `path`, else its area."""
        for d in path.parents:
            if d in self.category_at:
                return f'cat:{d}'
            if d in self.is_folder:
                return f'dir:{d}'
        return self.area(path)

    # -- nodes

    def status(self, name, d, subtree):
        """How a category is reached: by name (imported), through a category
        above it that is (inherited), only through a module in it named on
        its own (by-module), or not at all (orphan)."""
        if name in self.reached_by_name:
            return 'imported'
        if any(self.category_at.get(above) in self.reached_by_name for above in d.parents):
            return 'inherited'
        if any(m.name in self.reached_by_name for m in subtree):
            return 'by-module'
        return 'orphan'

    def add_categories(self):
        for d, name in sorted(self.category_at.items()):
            subtree = self.beneath(d)
            classes = frozenset().union(*(m.classes for m in subtree))
            self.nodes[f'cat:{d}'] = Node(f'cat:{d}', 'category', name, classes, len(subtree),
                                          self.status(name, d, subtree))

    def add_folders(self):
        for d in self.folders:
            subtree = self.beneath(d)
            classes = frozenset().union(*(m.classes for m in subtree))
            self.nodes[f'dir:{d}'] = Node(f'dir:{d}', 'folder', d.name, classes, len(subtree))

    def add_modules(self):
        for m in self.modules:
            self.nodes[f'mod:{m.path}'] = Node(f'mod:{m.path}', 'module', m.name, m.classes)

    def add_containment(self):
        """A `contains` edge into every category, folder and module. Areas
        are added here, as they are first needed."""
        for nid in list(self.nodes):
            path = PurePosixPath(nid.split(':', 1)[1])
            self.edges.append(Edge(self.parent(path), nid, 'contains'))

    # -- hosts and what they reach

    def hosts(self):
        """Every aggregate, by module path, then class in the document's
        class order."""
        return [Host(f'agg:{m.path}:{cls}', m, cls, self.includes[m.name][cls])
                for m in self.modules
                if m.name in self.includes and not self.in_category(m.path)
                for cls in class_order(self.doc) if cls in self.includes[m.name]]

    def target(self, name):
        """The node a host's included `name` points at, adding a missing node
        for a name the document doesn't know."""
        if name in self.dir_of_category:
            return f'cat:{self.dir_of_category[name]}'
        if name in self.doc['modules']:
            return f'mod:{self.doc["modules"][name]["path"]}'
        mid = f'missing:{name}'
        self.nodes.setdefault(mid, Node(mid, 'missing', name))
        return mid

    def add_hosts_and_imports(self, hosts):
        for h in hosts:
            self.nodes[h.id] = Node(h.id, 'aggregate', h.module.name, frozenset([h.cls]))
            for name in dict.fromkeys(h.includes):        # each name once, in order
                self.edges.append(Edge(h.id, self.target(name), 'imports', h.cls))

    def reached(self, h):
        """The module names a host reaches: its own, the modules of its class
        under a category it includes, and those of its class it includes by
        name."""
        out = {h.module.name}
        for name in h.includes:
            if name in self.dir_of_category:
                out |= {m.name for m in self.beneath(self.dir_of_category[name])
                        if h.cls in m.classes}
            if name in self.doc['modules'] and h.cls in self.doc['modules'][name]['classes']:
                out.add(name)
        return out

    def add_enables(self, hosts):
        """Host A enables host B when a module A reaches names B, by class
        and name, in its `enables`."""
        host_named = {(h.cls, h.module.name): h.id for h in hosts}
        for h in hosts:
            named_here = {(cls, name) for m in self.reached(h)
                          for cls, names in self.enables.get(m, {}).items() for name in names}
            targets = sorted({host_named[r] for r in named_here
                              if r in host_named and host_named[r] != h.id})
            self.edges += [Edge(h.id, t, 'enables', h.cls) for t in targets]


def children_sorted(g):
    """id -> the ids it `contains`: categories first, then by label."""
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
    starts = starting_points(g, category)
    keep = within_depth(g, starts, depth)
    # Overviews leave out what a host cannot name: modules and the plain
    # folders holding them. A category nested in a hidden folder hangs off
    # the nearest directory still drawn.
    if categories_only or view == 'hosts':
        keep = [i for i in keep if g.nodes[i].kind not in ('module', 'folder')]
    if view == 'tree':
        shown = set(keep)
        return Graph({i: g.nodes[i] for i in keep}, containment(g, keep, shown),
                     [s for s in starts if s in shown])
    return hosts_subgraph(g, keep, category)


def starting_points(g, category):
    """The roots, or the category named by --category."""
    if category is None:
        return list(g.roots)
    starts = [i for i, n in g.nodes.items() if n.kind == 'category' and n.label == category]
    if not starts:
        known = ', '.join(sorted({n.label for n in g.nodes.values() if n.kind == 'category'}))
        raise ModuleGraphError(f"no category {category!r}; categories: {known}")
    return starts


def within_depth(g, starts, depth):
    """Everything under `starts`, breadth first, at most `depth` levels down."""
    kids = children_sorted(g)
    keep, seen, queue = [], set(), [(s, 0) for s in starts]
    while queue:
        i, level = queue.pop(0)
        if i in seen or (depth is not None and level > depth):
            continue
        seen.add(i)
        keep.append(i)
        queue += [(k, level + 1) for k in kids.get(i, [])]
    return keep


def containers(g):
    """id -> the id that `contains` it."""
    return {e.dst: e.src for e in g.edges if e.kind == 'contains'}


def nearest_shown(parent, i, shown):
    """The closest container of `i` that is drawn, or None."""
    p = parent.get(i)
    while p is not None and p not in shown:
        p = parent.get(p)
    return p


def containment(g, ids, shown):
    """A `contains` edge from each id's nearest drawn container."""
    parent, out = containers(g), []
    for i in ids:
        p = nearest_shown(parent, i, shown)
        if p is not None:
            out.append(Edge(p, i, 'contains'))
    return out


def hosts_subgraph(g, keep, category):
    """The hosts view: every category in range (in its area's container),
    the aggregates that import into one, and the modules they name."""
    shown = {i for i in keep if g.nodes[i].kind in ('category', 'area')}
    in_range = {i for i in shown if g.nodes[i].kind == 'category'}
    parent, imports = containers(g), []
    # --category starts below the areas; each category still sits in its
    # area's container, which the page and the static boxes lay out from.
    for i in list(shown):
        top = i
        while top in parent:
            top = parent[top]
        if g.nodes[top].kind == 'area':
            shown.add(top)
    for e in g.edges:
        if e.kind != 'imports' or e.dst not in g.nodes:
            continue
        if g.nodes[e.dst].kind == 'module':
            # a module included by name: drawn when its category is
            if category is not None and nearest_shown(parent, e.dst, in_range) is None:
                continue
            shown.add(e.dst)
            imports.append(e)
        elif e.dst in shown or (category is None and g.nodes[e.dst].kind == 'missing'):
            imports.append(e)
    importers = {e.src for e in imports}
    missing = {e.dst for e in imports}
    nodes = {i: n for i, n in g.nodes.items()
             if i in shown or (n.kind == 'aggregate' and i in importers)
             or (n.kind == 'missing' and i in missing)}
    enabled = [e for e in g.edges if e.kind == 'enables' and e.src in nodes and e.dst in nodes]
    return Graph(nodes, containment(g, list(nodes), shown) + imports + enabled, [])
