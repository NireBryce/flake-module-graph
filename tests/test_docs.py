#!/usr/bin/env python3
"""The docs, checked like code: the rules doc/style.md, wiki/styleguide.md
and skill `new-skill` set, that links and anchors resolve, that the flags
the docs name exist, and that the wiki's examples do
what it says. Each failure names the file and what to fix.

    python3 -m unittest discover -s tests -p test_docs.py      # or `just test`, with the rest
"""
import contextlib, io, json, pathlib, re, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from module_graph import graph, loads, mermaid, select  # noqa: E402
from module_graph.__main__ import main  # noqa: E402

SKILLS = ROOT / '.agents' / 'skills'
WIKI = ROOT / 'wiki'
# Every Markdown file a reader can follow a link from.
DOCS = sorted([ROOT / 'README.md', ROOT / 'AGENTS.md', ROOT / 'CONTRIBUTING.md',
               *ROOT.glob('doc/*.md'), *WIKI.glob('*.md'), *SKILLS.glob('*/SKILL.md')])
DOCS = [p for p in DOCS if p.exists()]
# Flags of other commands (nix, uvx, tests/*.py) the docs may name.
OTHER_FLAGS = {'--json', '--extra-experimental-features', '--override-input', '--update'}


def rel(p):
    return p.relative_to(ROOT)


def prose(path):
    """The file's lines outside fenced code blocks; a fence closes only
    with the character that opened it."""
    out, fence = [], None
    for line in path.read_text().splitlines():
        mark = re.match(r' {0,3}(`{3,}|~{3,})', line)
        if fence:
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence):
                fence = None
        elif mark:
            fence = mark.group(1)
        else:
            out.append(line)
    return out


def links(path):
    """The targets of the file's Markdown links, outside code."""
    text = re.sub(r'`[^`\n]*`', '', '\n'.join(prose(path)))    # inline code
    return re.findall(r'\]\(([^)\s]+)\)', text)


def anchors(path):
    """GitHub's anchors for a file's headings: lowercase, punctuation
    dropped, spaces to hyphens; a repeated one gets -1, -2, ..."""
    out, seen = set(), {}
    for line in prose(path):
        if re.match(r'#{1,6} ', line):
            slug = re.sub(r'[^\w\- ]', '', line.lstrip('#').strip().lower()).replace(' ', '-')
            n = seen.get(slug, 0)
            seen[slug] = n + 1
            out.add(f'{slug}-{n}' if n else slug)
    return out


def frontmatter(test, path):
    """({key: value}, body). Fails the test, rather than crashing, on
    frontmatter that isn't plain one-line `key: value` pairs."""
    text = path.read_text()
    head = re.match(r'---\n(.*?)\n---\n', text, re.S)
    test.assertIsNotNone(head, 'no --- frontmatter --- at the top')
    meta = {}
    for line in head.group(1).splitlines():
        pair = re.fullmatch(r'([a-z_-]+): (\S.*)', line)
        test.assertIsNotNone(pair, f'not a one-line `key: value`: {line!r}')
        meta[pair.group(1)] = pair.group(2)
    return meta, text[head.end():]


class Skills(unittest.TestCase):
    """Skill `new-skill`'s rules for the frontmatter every harness reads."""

    def test_frontmatter(self):
        for path in SKILLS.glob('*/SKILL.md'):
            with self.subTest(rel(path)):
                meta, body = frontmatter(self, path)
                self.assertLessEqual(set(meta), {'name', 'description', 'when_to_use'},
                                     'only name, description and when_to_use are read')
                self.assertEqual(meta['name'], path.parent.name)
                for key in ('description', 'when_to_use'):
                    value = meta.get(key, '')
                    self.assertFalse(value.startswith(('"', "'")), f'{key} opens with a quote')
                    self.assertNotIn(': ', value, f'{key} holds ": ", which YAML reads as a key')
                    self.assertNotIn(' #', value, f'{key} holds " #", which YAML reads as a comment')
                self.assertLessEqual(len(meta['description']) + len(meta.get('when_to_use', '')), 1536)
                self.assertRegex(body.lstrip(), r'^# .+\n\n## Applies to\n',
                                 '`## Applies to` comes right after the title')

    def test_agents_md_lists_every_skill(self):
        listed = set(re.findall(r'^\| `([\w-]+)` \|', (ROOT / 'AGENTS.md').read_text(), re.M))
        present = {p.parent.name for p in SKILLS.glob('*/SKILL.md')}
        self.assertEqual(present - listed, set(), 'skills missing from AGENTS.md')


class Wiki(unittest.TestCase):
    """wiki/styleguide.md's "Every page"."""

    def test_every_page(self):
        index = (WIKI / '00-INDEX.md').read_text()
        for path in WIKI.glob('*.md'):
            with self.subTest(rel(path)):
                lines = path.read_text().splitlines()
                self.assertRegex(lines[0], r'^# ')
                self.assertRegex(lines[2], r'^_Last modified: \d{4}-\d{2}-\d{2}_$')
                if path.name == '00-INDEX.md':
                    continue
                self.assertIn(f']({path.name})', index, 'not listed in 00-INDEX.md')
                headings = [l[3:] for l in prose(path) if l.startswith('## ')]
                if len([h for h in headings if h != 'Contents']) >= 3:
                    contents = re.findall(r'^- \[(.+?)\]\(#', path.read_text(), re.M)
                    self.assertEqual(contents, [h for h in headings if h != 'Contents'],
                                     '## Contents must list every ## heading, in order')
                if len(path.read_text().split()) > 1000:
                    self.assertEqual(headings[:2], ['Contents', 'Quick facts'],
                                     'a page over ~1,000 words opens with Quick facts')


class Links(unittest.TestCase):
    """A relative link reaches a file, and its #anchor a heading in it."""

    def test_relative_links_and_anchors_resolve(self):
        for path in DOCS:
            for target in links(path):
                if re.match(r'[a-z]+:', target):
                    continue
                file, _, anchor = target.partition('#')
                dest = (path.parent / file).resolve() if file else path
                with self.subTest(file=str(rel(path)), link=target):
                    self.assertTrue(dest.exists(), 'no such file')
                    if anchor:
                        self.assertIn(anchor, anchors(dest), 'no such heading')


class NamedInTheDocs(unittest.TestCase):
    """The flags the docs name exist. (The error messages wiki/using-the-tool.md
    lists are pinned word for word by the unit tests that raise them.)"""

    def test_every_flag_the_docs_name_exists(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            main(['--help'])
        flags = set(re.findall(r'--[a-z][a-z-]+', out.getvalue())) | OTHER_FLAGS
        for path in DOCS:
            if path.is_relative_to(SKILLS):
                continue        # skills name git's and gh's flags
            # not after `<!`: an HTML comment such as `<!--module-graph:`
            named = set(re.findall(r'(?<![\w!-])--[a-z][a-z0-9-]+', path.read_text()))
            with self.subTest(rel(path)):
                self.assertEqual(named - flags, set(), 'not a flag of module-graph (or OTHER_FLAGS)')


class WikiExamples(unittest.TestCase):
    """wiki/using-the-tool.md's examples do what it says. The page's counts
    are checked in a browser by tests/browser.py (page `example`)."""

    def test_the_example_hosts_view(self):
        # "two cards in the 'hosts and home' box -- laptop and me-home --
        # arrows from laptop to base and desktop, from me-home to shell,
        # and a dashed enables arrow from laptop to me-home"
        g = select(graph(loads((ROOT / 'tests' / 'fixtures' / 'example.json').read_text())), 'hosts')
        label = {i: n.label for i, n in g.nodes.items()}
        self.assertEqual({(label[e.src], label[e.dst], e.kind) for e in g.edges if e.kind != 'contains'},
                         {('laptop', 'base', 'imports'), ('laptop', 'desktop', 'imports'),
                          ('me-home', 'shell', 'imports'), ('laptop', 'me-home', 'enables')})
        self.assertIn('-. enables .->', mermaid(g))

    def test_the_smallest_document_draws_laptop_into_base(self):
        text = (WIKI / 'using-the-tool.md').read_text()
        section = text.split('## Without dirs-as-categories', 1)[1]
        doc = json.loads(re.search(r'```json\n(.*?)```', section, re.S).group(1))
        g = select(graph(loads(json.dumps(doc))), 'hosts')
        self.assertEqual([(g.nodes[e.src].label, g.nodes[e.dst].label) for e in g.edges
                          if e.kind == 'imports'], [('laptop', 'base')])


    def test_the_readme_drawing_is_current(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.chdir(ROOT):
            main(['markdown', 'tests/fixtures/example.json', '--file', 'README.md', '--check'])
        self.assertEqual(out.getvalue(), 'README.md: 1 drawing, all current\n')


if __name__ == '__main__':
    unittest.main(verbosity=1)
