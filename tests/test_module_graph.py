#!/usr/bin/env python3
"""Tests for module-graph's model and renderers.

The diagram's job is to make the silent cases visible -- a category nothing
reaches, a name no module declares -- so these build small documents, break
them on purpose, and assert the graph says so. Pure stdlib:

    python3 -m unittest discover -s tests      # from the repository root
"""
import contextlib, io, json, pathlib, re, sys, tempfile, time, types, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import importlib  # noqa: E402
from module_graph import document, layout as lay  # noqa: E402
from module_graph.errors import ModuleGraphError  # noqa: E402
pg = importlib.import_module('module_graph.page')   # the module, not the function __init__ re-exports
from module_graph.__main__ import main  # noqa: E402
from module_graph.dot import GRID, dot  # noqa: E402
from module_graph.layout import Layout, boxed, boxes, layout_links, walk, arrows  # noqa: E402
from module_graph.look import ALERT, BOX_FILL, HUES, PALETTE, colours, hues, style  # noqa: E402
from module_graph.mermaid import mermaid  # noqa: E402
from module_graph.model import Edge, Graph, Node, graph, select  # noqa: E402
import golden  # noqa: E402  (tests/golden.py)

# The placement the hosts-view tests assume: a host's and a user's own areas
# above the hosts, homelab beside them, three shared areas in order.
LAYOUT = Layout(top=('host-config', 'users-config'), behind=('host-config',),
                beside=('homelab-config',), far=('users-config',),
                shared=('general-config', 'hardware-config', 'packages-config'))


def stem(path):
    return pathlib.PurePosixPath(path).stem


class Doc:
    """Builds a format-v1 document the way a test describes a tree."""

    def __init__(self):
        self.cats, self.mods, self.includes, self.enables = {}, {}, {}, {}

    def category(self, d):
        self.cats[d.rsplit('/', 1)[-1]] = d

    def module(self, path, *classes):
        self.mods[stem(path)] = (path, list(classes))

    def host(self, path, cls, *names):
        """An entry point: a module whose only content is `includes.<cls>`."""
        self.mods[stem(path)] = (path, [cls])
        self.includes[stem(path)] = {cls: list(names)}

    def turns_on(self, path, cls, *targets):
        """A module of class `cls` naming other classes' modules in `enables`,
        as `homeManager.home`."""
        self.module(path, cls)
        for t in targets:
            c, n = t.split('.')
            self.enables.setdefault(stem(path), {}).setdefault(c, []).append(n)

    def build(self):
        return {'version': 1, 'classes': ['nixos', 'homeManager', 'darwin'],
                'categories': {n: {'dir': d, 'members': [], 'nested': [], 'flag': None}
                               for n, d in self.cats.items()},
                'folders': [],
                'modules': {n: {'path': p, 'classes': c} for n, (p, c) in self.mods.items()},
                'includes': self.includes, 'enables': self.enables, 'defaults': [], 'admin': []}


class Tree(unittest.TestCase):
    def setUp(self):
        self.d = Doc()
        self.d.category('area/used')
        self.d.module('area/used/a.nix', 'nixos', 'homeManager')
        self.d.category('area/used/sub')
        self.d.module('area/used/sub/b.nix', 'homeManager')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'used')

    def g(self):
        return graph(self.d.build())

    def cat(self, g, name):
        (n,) = [n for n in g.nodes.values() if n.kind == 'category' and n.label == name]
        return n

    def kinds(self, g, kind):
        return {(e.src, e.dst) for e in g.edges if e.kind == kind}

    def cli(self, *argv, stdin=None, run=None):
        """main() on this test's document, from a file; (exit code, stdout)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / 'doc.json'
            path.write_text(json.dumps(self.d.build()))
            argv = [a.replace('DOC', str(path)) for a in argv]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = main(list(argv), **({'run': run} if run else {}))
            return rc, out.getvalue()


class Model(Tree):
    def test_containment_classes_and_counts(self):
        g = self.g()
        used, sub = self.cat(g, 'used'), self.cat(g, 'sub')
        self.assertEqual(used.classes, {'nixos', 'homeManager'})
        self.assertEqual((used.count, sub.count), (2, 1))   # nested counts upward
        self.assertEqual(sub.classes, {'homeManager'})
        contains = self.kinds(g, 'contains')
        self.assertIn(('cat:area/used', 'cat:area/used/sub'), contains)
        self.assertIn(('cat:area/used/sub', 'mod:area/used/sub/b.nix'), contains)
        self.assertIn(('cat:area/used', 'mod:area/used/a.nix'), contains)
        self.assertEqual(g.roots, ['area:area', 'area:hosts'])

    def test_orphan_category_is_flagged(self):
        self.d.category('area/lonely')
        self.d.module('area/lonely/l.nix', 'nixos')
        g = self.g()
        self.assertEqual(self.cat(g, 'lonely').status, 'orphan')
        self.assertIn('orphan', style(self.cat(g, 'lonely')))
        self.assertEqual(self.cat(g, 'used').status, 'imported')
        self.assertEqual(self.cat(g, 'sub').status, 'inherited')   # via its parent

    def test_category_reached_only_through_a_named_module(self):
        self.d.category('area/never-whole')
        self.d.module('area/never-whole/picked.nix', 'nixos')
        self.d.module('area/never-whole/other.nix', 'nixos')
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'used', 'picked')
        self.assertEqual(self.cat(self.g(), 'never-whole').status, 'by-module')

    def test_host_edges_carry_the_class_and_missing_names_show(self):
        self.d.host('hosts/home.nix', 'homeManager', 'sub', 'ghost')
        g = self.g()
        imports = {(e.src, e.dst, e.cls) for e in g.edges if e.kind == 'imports'}
        self.assertIn(('agg:hosts/alpha-configuration.nix:nixos', 'cat:area/used', 'nixos'), imports)
        self.assertIn(('agg:hosts/home.nix:homeManager', 'cat:area/used/sub', 'homeManager'), imports)
        self.assertEqual(g.nodes['missing:ghost'].kind, 'missing')

    def test_a_module_with_includes_inside_a_category_is_not_a_host(self):
        # a desktop module including a base module: it reaches the base,
        # but it is a module of its category, not an entry point
        self.d.category('area/desk')
        self.d.host('area/desk/full/full.nix', 'nixos', 'base')
        self.d.module('area/desk/base/base.nix', 'nixos')
        g = self.g()
        aggs = {n.label for n in g.nodes.values() if n.kind == 'aggregate'}
        self.assertEqual(aggs, {'alpha-configuration'})
        self.assertEqual(self.cat(g, 'desk').status, 'by-module')   # base is still included

    def test_an_enables_target_counts_as_reached(self):
        self.d.category('area/homes')
        self.d.module('area/homes/h.nix', 'homeManager')
        self.d.turns_on('hosts/x.nix', 'nixos', 'homeManager.homes')
        self.assertEqual(self.cat(self.g(), 'homes').status, 'imported')


class Standard(Tree):
    """The colour standard: a category is importable; a plain folder inside
    one is implicit; a module is never importable, even when a host names it."""

    def setUp(self):
        super().setUp()
        self.d.module('area/used/grp/c.nix', 'nixos')
        self.d.category('area/used/grp/inner')
        self.d.module('area/used/grp/inner/d.nix', 'nixos')

    def test_plain_directory_is_an_implicit_folder(self):
        g = self.g()
        self.assertEqual(g.nodes['dir:area/used/grp'].kind, 'folder')
        self.assertEqual(g.nodes['dir:area/used/grp'].count, 2)   # c, and inner's d
        contains = self.kinds(g, 'contains')
        self.assertIn(('cat:area/used', 'dir:area/used/grp'), contains)
        self.assertIn(('dir:area/used/grp', 'mod:area/used/grp/c.nix'), contains)
        self.assertIn(('dir:area/used/grp', 'cat:area/used/grp/inner'), contains)
        self.assertNotIn('dir:area/used/grp/inner', g.nodes)      # a category, not a folder

    def test_directories_outside_categories_are_not_folders(self):
        self.d.module('hosts/sub/e.nix', 'nixos')
        self.assertNotIn('dir:hosts/sub', self.g().nodes)

    def test_overviews_drop_folders_and_relink_nested_categories(self):
        for view in ('tree', 'hosts'):
            g = select(self.g(), view, categories_only=True)
            self.assertFalse(any(n.kind == 'folder' for n in g.nodes.values()), view)
            self.assertIn(('cat:area/used', 'cat:area/used/grp/inner'), self.kinds(g, 'contains'))

    def test_host_hues_never_reuse_the_category_or_alert_colour(self):
        self.assertNotIn(PALETTE['category'][1], HUES)
        self.assertNotIn(ALERT[1], HUES)

    def test_a_named_module_is_not_drawn_as_importable(self):
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'c')
        g = select(self.g(), 'hosts')
        node = g.nodes['mod:area/used/grp/c.nix']
        self.assertEqual(style(node), ['module'])
        self.assertEqual(colours(node), PALETTE['module'])
        cid = f'n{list(g.nodes).index("mod:area/used/grp/c.nix")}'
        self.assertNotRegex(mermaid(g), rf'class [\w,]*\b{cid}\b[\w,]* category')

    def test_renderers_draw_the_two_directory_kinds_apart(self):
        g = select(self.g(), 'tree')
        out = dot(g)
        self.assertRegex(out, r'<b>grp/</b>.*shape=folder')
        self.assertRegex(out, rf'label=<<b>used/</b>.*\n.*color="{PALETTE["category"][1]}"')
        m = mermaid(g)
        self.assertIn('["<b>grp/</b>', m)        # square: implicit
        self.assertIn('("<b>inner/</b>', m)      # rounded: importable
        ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
        self.assertIn(f'{ids["dir:area/used/grp"]} -.-> {ids["cat:area/used/grp/inner"]}', m)
        self.assertIn(f'{ids["dir:area/used/grp"]} --> {ids["mod:area/used/grp/c.nix"]}', m)


class Selecting(Tree):
    def test_depth_and_categories_only(self):
        g = select(self.g(), 'tree', depth=1, categories_only=True)
        self.assertEqual({n.label for n in g.nodes.values() if n.kind == 'category'}, {'used'})
        self.assertFalse(any(n.kind == 'module' for n in g.nodes.values()))
        deep = select(self.g(), 'tree', categories_only=True)
        self.assertIn('sub', {n.label for n in deep.nodes.values()})

    def test_category_filter_roots_at_the_category(self):
        g = select(self.g(), 'tree', category='sub')
        self.assertEqual({n.label for n in g.nodes.values()}, {'sub', 'b'})
        one = select(self.g(), 'tree', category='used', depth=1)
        self.assertEqual({n.label for n in one.nodes.values()}, {'used', 'a', 'sub'})

    def test_unknown_category_is_an_error_naming_the_real_ones(self):
        with self.assertRaises(ModuleGraphError) as cm:
            select(self.g(), 'tree', category='nope')
        self.assertIn('used', str(cm.exception))

    def test_hosts_view_keeps_orphans_and_drops_modules(self):
        self.d.category('area/lonely')
        self.d.module('area/lonely/l.nix', 'nixos')
        g = select(self.g(), 'hosts')
        self.assertIn('cat:area/lonely', g.nodes)        # drawn, with no host edge
        self.assertFalse(any(e.dst == 'cat:area/lonely' for e in g.edges if e.kind == 'imports'))
        self.assertFalse(any(n.kind == 'module' for n in g.nodes.values()))
        self.assertIn('agg:hosts/alpha-configuration.nix:nixos', g.nodes)

    def test_hosts_view_category_filter_drops_unrelated_hosts(self):
        self.d.category('area/other')
        self.d.module('area/other/o.nix', 'nixos')
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'other')
        g = select(self.g(), 'hosts', category='other')
        self.assertEqual({n.label for n in g.nodes.values() if n.kind == 'aggregate'},
                         {'beta-configuration'})

    def test_hosts_view_draws_a_module_a_host_names(self):
        self.d.category('area/never-whole')
        self.d.module('area/never-whole/picked.nix', 'nixos')
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'picked')
        self.assertIn('mod:area/never-whole/picked.nix', select(self.g(), 'hosts').nodes)


class HostsLayout(Tree):
    """The hosts view flows down from the hosts, with each host's own
    category (an area in layout.top) drawn above it."""

    def setUp(self):
        super().setUp()
        self.d.category('host-config/alpha')
        self.d.module('host-config/alpha/hw.nix', 'nixos')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'alpha', 'used')
        self.d.host('hosts/home.nix', 'homeManager', 'used')
        self.g_ = select(self.g(), 'hosts')
        self.ids = {i: f'n{k}' for k, i in enumerate(self.g_.nodes)}
        self.agg = self.ids['agg:hosts/alpha-configuration.nix:nixos']
        self.own = self.ids['cat:host-config/alpha']
        self.sub = self.ids['cat:area/used/sub']   # first in used's box: where its edges land

    def test_mermaid_runs_top_down_with_the_hosts_own_category_above(self):
        out = mermaid(self.g_, layout=LAYOUT)
        self.assertIn('\nflowchart TB\n', out)
        self.assertIn(f'{self.own} --- {self.agg}', out)   # category-first: ranks it above
        self.assertNotIn(f'{self.agg} --> {self.own}', out)   # no arrow back: no cycle
        box = re.search(r'subgraph (g\d+)\["<b>used/</b>', out).group(1)
        self.assertIn(f'{self.agg} --> {box}', out)        # shared ones flow down, into the box

    def test_without_a_layout_nothing_sits_above(self):
        out = mermaid(self.g_)
        self.assertIn(f'{self.agg} --> {self.own}', out)
        self.assertNotIn(' --- ', out)

    def test_mermaid_link_styles_land_on_the_hosts_own_edges(self):
        out = mermaid(self.g_, layout=LAYOUT)
        links = [l.strip() for l in out.splitlines()
                 if re.search(r' (-->|-\.->|---|~{3,}|-\. enables \.->) ', l)]
        for idx, colour in re.findall(r'linkStyle ([\d,]+) stroke:(#\w+)', out):
            for k in map(int, idx.split(',')):
                self.assertNotIn('~', links[k], (k, links[k]))   # never an invisible link
        hue = hues(self.g_)['agg:hosts/alpha-configuration.nix:nixos']
        mine = [k for idx, c in re.findall(r'linkStyle ([\d,]+) stroke:(#\w+)', out)
                if c == hue for k in map(int, idx.split(','))]
        box = re.search(r'subgraph (g\d+)\["<b>used/</b>', out).group(1)
        self.assertEqual(sorted(links[k] for k in mine),
                         sorted([f'{self.own} --- {self.agg}', f'{self.agg} --> {box}']))

    def test_dot_reverses_the_upward_edge_but_keeps_the_arrowhead(self):
        out = dot(self.g_, layout=LAYOUT)
        self.assertIn('rankdir=TB', out)
        self.assertRegex(out, rf'{self.own} -> {self.agg} \[dir=back ')
        self.assertRegex(out, rf'{self.agg} -> {self.sub} \[color=[^\]]* lhead=cluster_\d+\]')

    def test_dot_pins_unimported_shared_categories_below_the_hosts(self):
        self.d.category('area/lonely')
        self.d.module('area/lonely/l.nix', 'nixos')
        g = select(self.g(), 'hosts')
        ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
        out = dot(g, layout=LAYOUT)
        self.assertRegex(out, rf'n\d+ -> {ids["cat:area/lonely"]} \[style=invis minlen=1\]')
        self.assertNotRegex(out, rf'-> {ids["cat:host-config/alpha"]} \[style=invis')   # above, not below

    def test_users_area_sits_above_the_hosts_too(self):
        self.d.category('users-config/u')
        self.d.module('users-config/u/acct.nix', 'nixos')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'alpha', 'u', 'used')
        g = select(self.g(), 'hosts')
        ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
        agg = ids['agg:hosts/alpha-configuration.nix:nixos']
        out = dot(g, layout=LAYOUT)
        self.assertIn(f'{ids["cat:users-config/u"]} -> {agg} [dir=back', out)
        self.assertIn(f'{ids["cat:host-config/alpha"]} -> {agg} [dir=back', out)
        self.assertRegex(out, rf'{agg} -> {ids["cat:area/used/sub"]} \[color=[^\]]* lhead=')

    def test_tree_view_stays_left_to_right(self):
        self.assertIn('rankdir=LR', dot(select(self.g(), 'tree'), layout=LAYOUT))


class Wrapping(Tree):
    """Shared areas wrap at `wrap` categories per row; each row sits far
    enough below the last to clear its nested categories."""

    def setUp(self):
        super().setUp()
        tops = [f'c{k}' for k in range(7)]
        for c in tops:
            self.d.category(f'area/{c}')
            self.d.module(f'area/{c}/m{c}.nix', 'nixos')
        for k in range(6):                       # c0 has six nested: two rows at wrap 5
            self.d.category(f'area/c0/k{k}')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', *tops, 'used')
        self.g_ = select(self.g(), 'hosts')

    def links(self, wrap=5):
        return {b.split(':')[-1]: n for _, b, n in layout_links(self.g_, wrap)}

    def test_every_card_gets_its_rank_below_the_hosts(self):
        # top row c0..c4, then c5 c6 used. c0 is a box holding k0..k4 then
        # k5, and takes no rank of its own: its rows start at 1, so the
        # area's next row starts at 1 + 2.
        self.assertEqual(self.links(), {
            'area/c0/k0': 1, 'area/c0/k1': 1, 'area/c0/k2': 1, 'area/c0/k3': 1,
            'area/c0/k4': 1, 'area/c0/k5': 2,
            'area/c1': 1, 'area/c2': 1, 'area/c3': 1, 'area/c4': 1,
            'area/c5': 3, 'area/c6': 3, 'area/used/sub': 3})

    def test_links_all_start_at_the_first_host(self):
        self.assertEqual({a for a, _, _ in layout_links(self.g_)},
                         {'agg:hosts/alpha-configuration.nix:nixos'})

    def test_wrap_zero_is_one_row(self):
        self.assertEqual(set(self.links(0).values()), {1})

    def test_dot_keeps_every_host_on_one_row(self):
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'c6')
        g = select(self.g(), 'hosts')
        ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
        aggs = [ids[i] for i, n in g.nodes.items() if n.kind == 'aggregate']
        self.assertEqual(len(aggs), 2)
        self.assertIn('{ rank=same; ' + ' '.join(aggs) + ' }', dot(g))

    def test_tree_view_is_never_wrapped(self):
        self.assertEqual(layout_links(select(self.g(), 'tree')), [])

    def test_renderers_draw_the_same_links(self):
        g = self.g_
        ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
        a, b = ids['agg:hosts/alpha-configuration.nix:nixos'], ids['cat:area/c5']
        self.assertIn(f'{a} -> {b} [style=invis minlen=3];', dot(g))
        self.assertIn(f'{a} ~~~~~ {b}', mermaid(g))       # 3 tildes is 1 rank, +1 per rank

    def test_cli_wrap_flag_reaches_the_renderer(self):
        _, out = self.cli('dot', 'DOC', '--view', 'hosts', '--wrap', '0')
        self.assertNotIn('minlen=3', out)


class Boxes(Tree):
    """A category holding a nested category is drawn as a box around it."""

    def test_only_a_category_with_a_nested_category_is_boxed(self):
        self.assertEqual(boxed(select(self.g(), 'tree')), {'cat:area/used'})   # sub holds only b

    def test_the_box_holds_its_whole_subtree(self):
        g = select(self.g(), 'tree')
        (used,) = [b for b in walk(boxes(g)) if b.id == 'cat:area/used']
        self.assertEqual(set(used.items), {'mod:area/used/a.nix', 'cat:area/used/sub',
                                           'mod:area/used/sub/b.nix'})
        self.assertEqual(set(used.top), {'mod:area/used/a.nix', 'cat:area/used/sub'})  # direct only

    def test_containment_is_the_box_not_an_arrow(self):
        g = select(self.g(), 'tree')
        self.assertFalse(any(e.src == 'cat:area/used' for e in arrows(g)))
        self.assertIn(('cat:area/used/sub', 'mod:area/used/sub/b.nix'),
                      {(e.src, e.dst) for e in arrows(g)})   # sub is a card: arrows stay

    def test_a_box_is_not_also_drawn_as_a_card(self):
        g = select(self.g(), 'hosts')
        ids = {i: f'n{k}' for k, i in enumerate(g.nodes)}
        self.assertNotRegex(dot(g), rf'(?m)^\s+{ids["cat:area/used"]} \[')
        self.assertNotRegex(mermaid(g), rf'(?m)^\s+{ids["cat:area/used"]}\(')

    def test_box_status_styling(self):
        self.d.category('area/lonely')
        self.d.category('area/lonely/inner')
        self.d.module('area/lonely/inner/l.nix', 'nixos')
        self.d.category('area/picked')
        self.d.category('area/picked/inner2')
        self.d.module('area/picked/inner2/p.nix', 'nixos')
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'p')
        out = dot(select(self.g(), 'hosts'))
        lonely = re.search(r'label=<<b>lonely/</b>.*\n(.*)', out).group(1)
        self.assertIn(f'color="{ALERT[1]}"', lonely)
        self.assertIn('penwidth=2.5', lonely)
        picked = re.search(r'label=<<b>picked/</b>.*\n(.*)', out).group(1)
        self.assertIn('dashed', picked)                          # reached by module only
        m = mermaid(select(self.g(), 'hosts'))
        self.assertRegex(m, rf'style g\d+ fill:{BOX_FILL},stroke:{ALERT[1]}.*stroke-width:2.5px')


# What Nix 2.34 printed for three common mistakes, paths made generic.
NIX_NO_ATTRIBUTE = """\
error: flake 'git+file:///home/me/flake' does not provide attribute 'packages.x86_64-linux.moduleGraph', 'legacyPackages.x86_64-linux.moduleGraph' or 'moduleGraph'
       Did you mean module-graph?
"""
NIX_UNTRACKED = """\
warning: Git tree '/home/me/flake' is dirty
error:
       … while calling the 'import' builtin
         at /home/me/flake/flake.nix:1:32:
            1| { outputs = _: { moduleGraph = import ./g.nix; }; }
             |                                ^
            2|

       error: Path 'g.nix' in the repository "/home/me/flake" is not tracked by Git.

       To make it visible to Nix, run:

       git -C "/home/me/flake" add "g.nix"
"""
NIX_UNDEFINED = """\
warning: Git tree '/home/me/flake' is dirty
error: undefined variable 'undefinedThing'
       at /home/me/flake/flake.nix:1:32:
            1| { outputs = _: { moduleGraph = undefinedThing; }; }
             |                                ^
            2|
"""


class FakeNix:
    """Stands in for subprocess.run: answers `nix ... eval --json <ref>` from
    a dict keyed by ref. A ref it doesn't know fails, printing `stderr`;
    `missing=True` acts as if nix is absent."""

    def __init__(self, answers, missing=False, stderr=NIX_NO_ATTRIBUTE):
        self.answers, self.missing, self.stderr, self.calls = answers, missing, stderr, []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if self.missing:
            raise FileNotFoundError('nix')
        ref = cmd[-1]
        if ref not in self.answers:
            return types.SimpleNamespace(returncode=1, stdout='', stderr=self.stderr)
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(self.answers[ref]), stderr='')


class Documents(Tree):
    """Reading the document: from a file, stdin, or a flake."""

    def test_a_flake_ref_defaults_to_moduleGraph(self):
        fake = FakeNix({'.#moduleGraph': self.d.build()})
        self.assertEqual(document.from_flake('.', fake), self.d.build())
        self.assertEqual(fake.calls[0][-3:], ['eval', '--json', '.#moduleGraph'])
        fake = FakeNix({'.#other': self.d.build()})
        document.from_flake('.#other', fake)
        self.assertEqual(fake.calls[0][-1], '.#other')

    def test_flakes_need_not_be_turned_on_already(self):
        # nix-command and flakes are still experimental: without this, a
        # fresh Nix install refuses `nix eval` before reading the flake
        fake = FakeNix({'.#moduleGraph': self.d.build()})
        document.from_flake('.', fake)
        self.assertEqual(fake.calls[0][:3], ['nix', '--extra-experimental-features', 'nix-command flakes'])

    def test_nix_errors_name_the_cause_and_what_to_do(self):
        cases = {   # stderr -> (the cause, the hint)
            NIX_NO_ATTRIBUTE: ("does not provide attribute 'packages.x86_64-linux.moduleGraph'",
                               "doesn't publish `moduleGraph`"),
            NIX_UNTRACKED: ("Path 'g.nix' in the repository \"/home/me/flake\" is not tracked by Git.",
                            '`git add`'),
            NIX_UNDEFINED: ("undefined variable 'undefinedThing'",
                            'nix eval --json .#moduleGraph'),
        }
        for stderr, (cause, hint) in cases.items():
            with self.assertRaises(ModuleGraphError) as cm:
                document.from_flake('.', FakeNix({}, stderr=stderr))
            first, *rest = str(cm.exception).splitlines()
            self.assertTrue(first.startswith('module-graph document: nix eval .#moduleGraph failed: '))
            self.assertIn(cause, first)
            self.assertIn(hint, '\n'.join(rest))

    def test_evaluation_failures_say_why(self):
        with self.assertRaises(ModuleGraphError) as cm:
            document.from_flake('.', FakeNix({}, stderr='something odd\n'))
        self.assertIn('something odd', str(cm.exception))   # no `error:` line: the last line
        with self.assertRaises(ModuleGraphError) as cm:
            document.from_flake('.', FakeNix({}, missing=True))
        self.assertIn('nix is not installed', str(cm.exception))

    def test_a_wrong_document_is_refused_with_a_reason(self):
        good = self.d.build()
        cases = {
            'version 2': {**good, 'version': 2},
            '`modules` must be an object': {**good, 'modules': []},
            'categories.x: needs a string `dir`': {**good, 'categories': {'x': {}}},
            'modules.m: needs a string `path`': {**good, 'modules': {'m': {'path': 'm.nix'}}},
            'includes.h: must map classes': {**good, 'includes': {'h': ['used']}},
        }
        for needle, doc in cases.items():
            with self.assertRaises(ModuleGraphError) as cm:
                document.loads(json.dumps(doc))
            self.assertIn(needle, str(cm.exception))
        with self.assertRaises(ModuleGraphError) as cm:
            document.loads('{not json')
        self.assertIn('not JSON', str(cm.exception))

    def test_cli_reads_a_file_stdin_or_a_flake(self):
        rc, out = self.cli('tree', 'DOC')
        self.assertEqual(rc, 0)
        self.assertIn('used/', out)
        old = sys.stdin
        sys.stdin = io.StringIO(json.dumps(self.d.build()))
        try:
            rc, out = self.cli('tree', '-')
        finally:
            sys.stdin = old
        self.assertIn('used/', out)
        rc, out = self.cli('tree', '--flake', 'x', run=FakeNix({'x#moduleGraph': self.d.build()}))
        self.assertIn('used/', out)

    def test_cli_needs_exactly_one_source(self):
        with self.assertRaises(SystemExit) as cm:
            self.cli('tree', 'DOC', '--flake', 'x')
        self.assertEqual(str(cm.exception), 'error: give a DOCUMENT or --flake, not both')
        with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
            with self.assertRaises(SystemExit) as cm:
                self.cli('tree')
        self.assertIn('no flake.nix here', str(cm.exception))

    def test_with_no_document_a_flake_here_is_read(self):
        fake = FakeNix({'.#moduleGraph': self.d.build()})
        with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
            pathlib.Path('flake.nix').write_text('{ outputs = _: { }; }')
            rc, out = self.cli('tree', run=fake)
        self.assertEqual((rc, fake.calls[0][-1]), (0, '.#moduleGraph'))
        self.assertIn('used/', out)

    def test_a_missing_file_is_an_error_not_a_traceback(self):
        for argv in (['tree', 'nope.json'], ['tree', 'DOC', '--config', 'nope.toml']):
            with self.assertRaises(SystemExit) as cm:
                self.cli(*argv)
            self.assertRegex(str(cm.exception), r"^error: nope\.(json|toml): no such file$")

    def test_a_layout_file_that_is_not_toml_says_where(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / 'l.toml'
            bad.write_text('[layout\n')
            with self.assertRaises(ModuleGraphError) as cm:
                lay.load_layout(bad)
        self.assertIn('l.toml: not TOML (', str(cm.exception))


class Layouts(unittest.TestCase):
    def write(self, text):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.toml', delete=False)
        tmp.write(text)
        tmp.close()
        self.addCleanup(pathlib.Path(tmp.name).unlink)
        return tmp.name

    def test_a_layout_file_fills_every_place(self):
        path = self.write('[layout]\ntop = ["a"]\nbehind = ["a"]\nbeside = ["b"]\n'
                          'far = ["c"]\nshared = ["d", "e"]\n')
        self.assertEqual(lay.load_layout(path),
                         Layout(top=('a',), behind=('a',), beside=('b',), far=('c',), shared=('d', 'e')))

    def test_no_layout_table_is_the_default(self):
        self.assertEqual(lay.load_layout(self.write('')), Layout())

    def test_mistakes_are_refused(self):
        for text, needle in (('[layout]\nabove = ["a"]\n', 'unknown [layout] keys: above'),
                             ('[layout]\ntop = "a"\n', 'top must be a list')):
            with self.assertRaises(ModuleGraphError) as cm:
                lay.load_layout(self.write(text))
            self.assertIn(needle, str(cm.exception))


class Page(Tree):
    """`html`: the hosts view as an interactive page. The page's behaviour is
    JS and is checked in a browser (tests/browser.py); these pin what Python
    hands it."""

    def setUp(self):
        super().setUp()
        self.d.category('host-config/alpha')
        self.d.module('host-config/alpha/hw.nix', 'nixos')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'alpha', 'used', 'ghost')
        self.d.host('hosts/home.nix', 'homeManager', 'sub')

    def data(self, layout=LAYOUT):
        return pg.page_data(select(self.g(), 'hosts'), layout)

    def test_areas_hold_their_tree_and_know_their_place(self):
        self.d.category('users-config/u')
        self.d.module('users-config/u/acct.nix', 'nixos')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'alpha', 'u', 'used', 'ghost')
        areas = {a['title']: a for a in self.data()['areas']}
        self.assertEqual({k: a['place'] for k, a in areas.items()},
                         {'host-config': 'behind', 'users-config': 'user',
                          'area': 'shared', 'not found': 'shared'})
        (used,) = areas['area']['children']
        self.assertEqual((used['id'], used['kind'], used['status']),
                         ('cat:area/used', 'category', 'imported'))
        self.assertEqual([c['id'] for c in used['children']], ['cat:area/used/sub'])

    def test_without_a_layout_every_area_is_shared_alphabetically(self):
        areas = self.data(Layout())['areas']
        self.assertEqual({a['place'] for a in areas}, {'shared'})
        titles = [a['title'] for a in areas if a['title'] != 'not found']
        self.assertEqual(titles, sorted(titles))

    def test_hosts_carry_their_hue_and_imports(self):
        d = self.data()
        hosts = {h['title']: h for h in d['hosts']}
        self.assertEqual(set(hosts), {'alpha-configuration', 'home'})
        self.assertEqual(hosts['alpha-configuration']['sub'], 'nixos')
        self.assertNotEqual(hosts['alpha-configuration']['hue'], hosts['home']['hue'])
        self.assertEqual(d['imports'][hosts['home']['id']], ['cat:area/used/sub'])

    def test_a_name_no_module_declares_gets_a_not_found_area(self):
        areas = {a['title']: a for a in self.data()['areas']}
        self.assertEqual([c['title'] for c in areas['not found']['children']], ['ghost'])

    def test_style_comes_from_the_python_palette(self):
        style_ = self.data()['style']
        self.assertEqual(style_['palette']['category'], list(PALETTE['category']))
        self.assertEqual((style_['alert'], style_['boxFill']), (list(ALERT), BOX_FILL))

    def test_page_fills_the_template_once(self):
        out = pg.page(select(self.g(), 'hosts'))
        self.assertTrue(out.startswith('<!doctype html>'))
        self.assertNotIn(pg.PLACEHOLDER, out)
        self.assertIn('"title":"alpha-configuration"', out)

    def test_data_cannot_close_the_script_element(self):
        g = Graph({'area:x': Node('area:x', 'area', 'x'),
                   'cat:x/evil': Node('cat:x/evil', 'category', '</script><b>'),
                   'agg:h:nixos': Node('agg:h:nixos', 'aggregate', 'h', frozenset(['nixos']))},
                  [Edge('area:x', 'cat:x/evil', 'contains'),
                   Edge('agg:h:nixos', 'cat:x/evil', 'imports', 'nixos')], [])
        out = pg.page(g)
        script = out[out.index('const DATA'):]
        self.assertNotIn('</script><b>', script.split('\n')[0])
        self.assertIn('<\\/script><b>', out)
        self.assertEqual(out.count('</script>'), 1)          # only the template's own

    def test_a_template_without_one_placeholder_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = pathlib.Path(tmp) / 'template.html'
            bad.write_text('<!doctype html><script>const DATA = null;</script>')
            with self.assertRaises(ModuleGraphError):
                pg.page(select(self.g(), 'hosts'), template=bad)

    def test_cli_html(self):
        rc, out = self.cli('html', 'DOC')
        self.assertEqual(rc, 0)
        self.assertIn('<title>Module graph</title>', out)
        self.assertIn('"id":"cat:host-config/alpha"', out)


class Places(Tree):
    """Where the page puts each area."""

    def test_areas_get_their_place_and_shared_ones_their_order(self):
        areas = ('packages-config/p', 'general-config/g', 'hardware-config/w',
                 'homelab-config/h', 'zz-config/z', 'host-config/x')
        for area in areas:
            self.d.category(area)
            self.d.module(f'{area}/{area.split("/")[1]}m.nix', 'nixos')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', *(a.split('/')[1] for a in areas))
        d = pg.page_data(select(self.g(), 'hosts'), LAYOUT)
        places = [(a['title'], a['place']) for a in d['areas']]
        shared = [t for t, p in places if p == 'shared']
        self.assertEqual(shared[:3], ['general-config', 'hardware-config', 'packages-config'])
        self.assertEqual(sorted(shared[3:]), shared[3:])            # the rest, alphabetically
        self.assertIn(('homelab-config', 'beside'), places)
        self.assertIn(('host-config', 'behind'), places)


class Enables(Tree):
    """A host does not include its home configuration: a module it reaches
    names it in `enables`. That is the `enables` edge."""

    def setUp(self):
        super().setUp()
        self.d.host('hosts/home.nix', 'homeManager', 'sub')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'used')

    def enabled(self):
        return {(e.src, e.dst, e.cls) for e in self.g().edges if e.kind == 'enables'}

    HOST, HOMEID = 'agg:hosts/alpha-configuration.nix:nixos', 'agg:hosts/home.nix:homeManager'

    def test_a_module_the_host_reaches_enables_it(self):
        self.d.turns_on('area/used/turn-on.nix', 'nixos', 'homeManager.home')
        self.assertEqual(self.enabled(), {(self.HOST, self.HOMEID, 'nixos')})

    def test_no_enables_no_edge(self):
        self.assertEqual(self.enabled(), set())

    def test_only_modules_of_the_hosts_class_count(self):
        # the darwin twin sits in the same category; a nixos host never gets it
        self.d.turns_on('area/used/turn-on-darwin.nix', 'darwin', 'homeManager.home')
        self.assertEqual(self.enabled(), set())

    def test_a_module_included_by_name_counts(self):
        self.d.category('area/never-whole')
        self.d.turns_on('area/never-whole/picked.nix', 'nixos', 'homeManager.home')
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'picked')
        self.assertEqual(self.enabled(), {(self.HOST, self.HOMEID, 'nixos')})

    def test_the_hosts_own_enables_count(self):
        self.d.host('hosts/alpha-configuration.nix', 'nixos', 'used')
        self.d.enables['alpha-configuration'] = {'homeManager': ['home']}
        self.assertEqual(self.enabled(), {(self.HOST, self.HOMEID, 'nixos')})

    def test_an_enables_target_that_is_no_aggregate_draws_no_edge(self):
        self.d.turns_on('area/used/turn-on.nix', 'nixos', 'homeManager.sub')
        self.assertEqual(self.enabled(), set())

    def test_page_splits_hosts_from_the_homes_they_enable(self):
        self.d.turns_on('area/used/turn-on.nix', 'nixos', 'homeManager.home')
        d = pg.page_data(select(self.g(), 'hosts'))
        self.assertEqual([h['title'] for h in d['hosts']], ['alpha-configuration'])
        self.assertEqual([h['title'] for h in d['homes']], ['home'])
        self.assertEqual(d['enables'][self.HOST], [self.HOMEID])
        self.assertEqual(d['enables'][self.HOMEID], [])

    def test_renderers_draw_it_dashed(self):
        self.d.turns_on('area/used/turn-on.nix', 'nixos', 'homeManager.home')
        g = select(self.g(), 'hosts')
        self.assertIn('-. enables .->', mermaid(g))
        self.assertRegex(dot(g), r'style=dashed penwidth=1.2 label="enables"')


class Rendering(Tree):
    def test_mermaid_marks_orphans(self):
        self.d.category('area/lonely')
        self.d.module('area/lonely/lonely-m.nix', 'nixos')
        g = select(self.g(), 'tree')
        out = mermaid(g)
        self.assertTrue(out.startswith('%%{init:'))
        self.assertIn('\nflowchart LR\n', out)
        self.assertIn('subgraph g0["area"]', out)     # an area is a container
        area = f'n{list(g.nodes).index("area:area")}'
        self.assertNotRegex(out, rf'(?m)^\s+{area} ')   # containment, not arrows
        self.assertRegex(out, r'class [\w,]+ orphan')
        self.assertIn('<b>a</b><br/><i>n h</i>', out)

    def test_mermaid_hosts_colours_each_hosts_edges(self):
        self.d.host('hosts/beta-configuration.nix', 'nixos', 'used', 'sub')
        out = mermaid(select(self.g(), 'hosts'))
        styles = re.findall(r'(?m)^\s+linkStyle ([\d,]+) stroke:(#\w+)', out)
        self.assertEqual(len(styles), 2)                  # one per host
        self.assertNotEqual(styles[0][1], styles[1][1])   # in different hues
        self.assertEqual(sorted(len(s.split(',')) for s, _ in styles), [1, 2])
        self.assertIn('<i>nixos</i>', out)                # class on the host card
        self.assertNotIn('-->|', out)                     # not on every edge

    def test_hosts_view_boxes_nested_categories_in_their_area(self):
        g = select(self.g(), 'hosts')
        (area,) = [b for b in boxes(g) if b.id == 'area:area']
        (used,) = area.subs
        self.assertEqual((used.id, used.items), ('cat:area/used', ['cat:area/used/sub']))

    def test_dot_without_arrows_lays_areas_out_as_a_grid(self):
        for k in range(6):
            self.d.category(f'area/c{k}')
        out = dot(select(self.g(), 'tree', depth=1, categories_only=True))
        self.assertIn('rankdir=TB', out)
        self.assertEqual(out.count('[style=invis]'), 7 - GRID)

    def test_dot_is_well_formed_and_escaped(self):
        out = dot(select(self.g(), 'hosts'))
        self.assertTrue(out.startswith('digraph modules {') and out.endswith('}'))
        self.assertEqual(out.count('{'), out.count('}'))
        self.assertIn('label=<<b>sub/</b><br/><font', out)    # HTML label
        self.assertIn('label=<<b>used/</b>  <font', out)     # a box's title
        self.assertNotIn('[style=dotted]', out)       # used -> sub is the box, not an arrow

    def test_cli_prints_mermaid(self):
        rc, out = self.cli('tree', 'DOC', '--categories-only')
        self.assertEqual(rc, 0)
        self.assertIn('used/', out)


class Markdown(Tree):
    """`markdown`: drawings kept inside a Markdown file, between markers,
    rewritten in place or checked for staleness."""

    STALE = (
        '# Modules\n\n'
        '<!-- module-graph: tree --categories-only -->\n'
        'old drawing\n'
        '<!-- /module-graph -->\n\n'
        'Hosts:\n\n'
        '<!-- module-graph: hosts --category used -->\n'
        '<!-- /module-graph -->\n'
        'the end\n')

    def md(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = pathlib.Path(tmp.name) / 'README.md'
        path.write_text(text)
        return path

    def test_blocks_are_rewritten_between_their_markers(self):
        path = self.md(self.STALE)
        rc, out = self.cli('markdown', 'DOC', '--file', str(path))
        self.assertEqual((rc, out), (0, f'updated {path}: 2 drawings\n'))
        text = path.read_text()
        tree = self.cli('tree', 'DOC', '--categories-only')[1]
        hosts = self.cli('hosts', 'DOC', '--category', 'used')[1]
        self.assertEqual(text, (
            '# Modules\n\n'
            '<!-- module-graph: tree --categories-only -->\n'
            f'```mermaid\n{tree}```\n'
            '<!-- /module-graph -->\n\n'
            'Hosts:\n\n'
            '<!-- module-graph: hosts --category used -->\n'
            f'```mermaid\n{hosts}```\n'
            '<!-- /module-graph -->\n'
            'the end\n'))

    def test_rewriting_again_changes_nothing(self):
        path = self.md(self.STALE)
        self.cli('markdown', 'DOC', '--file', str(path))
        once = path.read_text()
        rc, out = self.cli('markdown', 'DOC', '--file', str(path))
        self.assertEqual((rc, out, path.read_text()), (0, f'{path}: 2 drawings, all current\n', once))

    def test_check_fails_on_a_stale_file_and_leaves_it_alone(self):
        path = self.md(self.STALE)
        with self.assertRaises(SystemExit) as cm:
            self.cli('markdown', 'DOC', '--file', str(path), '--check')
        self.assertEqual(str(cm.exception),
                         f'error: {path}: 2 of 2 drawings are stale; '
                         f'run `module-graph markdown --file {path}` to update them')
        self.assertEqual(path.read_text(), self.STALE)
        self.cli('markdown', 'DOC', '--file', str(path))
        self.assertEqual(self.cli('markdown', 'DOC', '--file', str(path), '--check')[0], 0)

    def test_a_bad_marker_names_its_line(self):
        cases = {
            '<!-- module-graph: tree -->\nno end\n': 'line 1: no `<!-- /module-graph -->` after it',
            'x\n<!-- module-graph: dot --view hosts -->\n<!-- /module-graph -->\n':
                "line 2: `dot` can't go in Markdown; use tree or hosts",
            '<!-- module-graph: tree --flake . -->\n<!-- /module-graph -->\n':
                'line 1: --flake belongs on the command line, not in a marker',
            '<!-- module-graph: tree --nope -->\n<!-- /module-graph -->\n':
                'line 1: unrecognized arguments: --nope',
        }
        for text, needle in cases.items():
            path = self.md(text)
            with self.assertRaises(SystemExit) as cm:
                self.cli('markdown', 'DOC', '--file', str(path))
            self.assertEqual(str(cm.exception), f'error: {path}: {needle}')

    def test_markdown_needs_a_file(self):
        with self.assertRaises(SystemExit) as cm:
            self.cli('markdown', 'DOC')
        self.assertEqual(str(cm.exception), 'error: markdown needs --file FILE')


class Saved(unittest.TestCase):
    """Every view of tests/fixtures/golden.json, byte for byte against
    tests/expected/golden/. A change meant to move the drawing: check the
    diff by eye, then `python3 tests/golden.py --update`."""

    def test_every_view_matches_its_saved_output(self):
        diffs = golden.differences()
        self.assertFalse(diffs, '\n' + ''.join(diffs.values()))


class CommandLine(Tree):
    """What the command does around the drawing: where it writes, what it
    warns about, and how a mistake reaches the user."""

    def test_output_goes_to_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'tree.mmd'
            rc, printed = self.cli('tree', 'DOC', '-o', str(out))
            self.assertEqual((rc, printed), (0, ''))
            self.assertEqual(out.read_text(), self.cli('tree', 'DOC')[1])

    def test_a_failure_leaves_no_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'tree.mmd'
            with self.assertRaises(SystemExit):
                self.cli('tree', 'DOC', '--category', 'nope', '-o', str(out))
            self.assertFalse(out.exists())

    def test_library_errors_reach_the_user_as_one_line(self):
        with self.assertRaises(SystemExit) as cm:
            self.cli('tree', 'DOC', '--category', 'nope')
        self.assertEqual(str(cm.exception), "error: no category 'nope'; categories: sub, used")

    def test_mermaid_past_its_default_limits_is_warned_about(self):
        small = io.StringIO()
        with contextlib.redirect_stderr(small):
            self.cli('tree', 'DOC')
        self.assertEqual(small.getvalue(), '')
        for k in range(800):
            self.d.module(f'area/used/many/m{k:03}.nix', 'nixos')
        big = io.StringIO()
        with contextlib.redirect_stderr(big):
            rc, out = self.cli('tree', 'DOC')
        self.assertEqual(rc, 0)
        self.assertGreater(len(out), 50000)
        self.assertIn(f'warning: this Mermaid diagram is {len(out) - 1} characters', big.getvalue())
        self.assertIn('warning: this Mermaid diagram has 801 links', big.getvalue())   # many/ -> 800 modules, sub -> b
        self.assertIn('--category', big.getvalue())


class Scale(unittest.TestCase):
    """A few thousand modules is a real flake's size, not a stress test."""

    def test_five_thousand_modules_build_in_seconds(self):
        cats, mods = {}, {}
        for c in range(200):
            cats[f'c{c}'] = {'dir': f'area{c % 10}/c{c}'}
            for m in range(25):
                mods[f'm{c}-{m}'] = {'path': f'area{c % 10}/c{c}/sub{m % 3}/m{m}.nix',
                                     'classes': ['nixos']}
        mods['laptop'] = {'path': 'hosts/laptop.nix', 'classes': ['nixos']}
        doc = {'version': 1, 'categories': cats, 'modules': mods,
               'includes': {'laptop': {'nixos': [f'c{c}' for c in range(0, 200, 7)]}}}
        start = time.monotonic()
        g = graph(doc)
        self.assertLess(time.monotonic() - start, 5)       # was about 120s
        self.assertEqual(sum(n.kind == 'module' for n in g.nodes.values()), 5001)


if __name__ == '__main__':
    unittest.main(verbosity=1)
