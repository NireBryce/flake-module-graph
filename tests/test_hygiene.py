#!/usr/bin/env python3
"""The package's hygiene, checked like code: the mechanical half of an
audit (skill `audit`). Nothing here understands the model -- these pin the
properties an audit once established by hand: the package spawns no shell,
speaks to no network, builds no HTML from strings, loads no resource from
anywhere (the page works offline), and reads and writes files only as
explicit UTF-8. A failure names the file and line.

    python3 -m unittest discover -s tests -p test_hygiene.py
"""
import pathlib, re, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'module_graph'

# The only URLs in the tree: an XML namespace, never fetched, and pointers
# in error text, never fetched either. A new URL must land here consciously.
URLS = {'http://www.w3.org/2000/svg',
        'https://github.com/NireBryce/dirs-as-categories'}

# sink -> why it must not appear
FORBIDDEN = [
    (r'\bshell\s*=', 'subprocess must take a list, not a shell command'),
    (r'\bos\.(system|popen)\b', 'runs a shell'),
    (r'\b(eval|exec)\(', 'runs code from input'),
    (r'\b(urllib|socket|http\.client|requests)\b', 'reaches the network'),
    (r'innerHTML|outerHTML|insertAdjacentHTML|document\.write',
     'builds HTML from a string; the page builds the DOM with createElement/textContent'),
    (r'<script\s+src|<link\s+href|<img\s+src', 'loads a resource; the page works offline'),
]


def numbered(path):
    return enumerate(path.read_text(encoding='utf-8').splitlines(), 1)


class Hygiene(unittest.TestCase):
    def test_no_shell_no_network_no_html_from_strings(self):
        for path in sorted([*SRC.glob('*.py'), SRC / 'page.html']):
            for n, line in numbered(path):
                for pattern, why in FORBIDDEN:
                    with self.subTest(f'{path.relative_to(ROOT)}:{n}'):
                        self.assertIsNone(re.search(pattern, line),
                                          f'{why}: {line.strip()}')

    def test_the_only_urls_are_namespaces_not_addresses(self):
        for path in sorted([*SRC.glob('*.py'), SRC / 'page.html']):
            for n, line in numbered(path):
                for url in re.findall(r'https?://[^\s"\')]+', line):
                    with self.subTest(f'{path.relative_to(ROOT)}:{n}'):
                        self.assertIn(url, URLS, 'a URL that is not a namespace')

    def test_files_are_read_and_written_as_explicit_utf8(self):
        for path in sorted(SRC.glob('*.py')):
            for n, line in numbered(path):
                for m in re.finditer(r'\.read_text\(|\.write_text\(|(?<![\w.])open\(', line):
                    call = line[m.start():]
                    if re.search(r"['\"][rw]?b['\"]", call):
                        continue        # binary: no encoding to name
                    with self.subTest(f'{path.relative_to(ROOT)}:{n}'):
                        self.assertIn('encoding=', call,
                                      'file I/O without an encoding depends on the locale')


if __name__ == '__main__':
    unittest.main(verbosity=1)
