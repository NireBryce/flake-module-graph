"""The colour standard and card text, shared by every renderer and the page.

The look follows nix-topology's: rounded cards with a muted fill and a darker
outline of the same hue, a bold name over a quiet subtitle, and containers
with a small title to group what belongs together. Fills are light and the
text dark on purpose, so a diagram reads the same on a white page and on a
dark theme.

One rule carries the standard. A category -- a folder a host can include by
name -- is the only thing drawn in blue, as a rounded card. A plain folder
inside one is implicit, collected only through the category above it: slate,
square-cornered. Modules are neutral white even when a host names one
directly: importable means a category, never a single module.
"""
from .model import CLASS_LETTER, CLASS_ORDER

INK, QUIET, LINE = '#1e293b', '#64748b', '#94a3b8'
PALETTE = {                         # kind -> (fill, outline)
    'area':      ('#f8fafc', '#cbd5e1'),
    'category':  ('#dbeafe', '#2563eb'),
    'folder':    ('#f1f5f9', '#94a3b8'),
    'module':    ('#ffffff', '#94a3b8'),
    'aggregate': ('#ffffff', '#f59e0b'),
    'missing':   ('#fee2e2', '#ef4444'),
}
ALERT = ('#fff1f2', '#e11d48')      # a category nothing reaches
# One hue per host or home entry point, for its card outline and every import
# edge it draws -- nix-topology's colour-per-network, so one host's imports can
# be followed through the crossing lines. Cycled past six. No blue and no
# red: blue is the category colour and red the alert, and a host drawn in
# either reads as one of those.
HUES = ['#16a34a', '#d97706', '#9333ea', '#db2777', '#0d9488', '#92400e']
# A category drawn as a container: the category colours, paler, so the cards
# inside it still stand out.
BOX_FILL = '#eff6ff'
ENTRY = ('#fefce8', '#fde68a')


def letters(classes):
    known = [CLASS_LETTER[c] for c in CLASS_ORDER if c in classes]
    return ' '.join(known + sorted(c for c in classes if c not in CLASS_LETTER))


def hues(g):
    aggs = [i for i, n in g.nodes.items() if n.kind == 'aggregate']
    return {a: HUES[k % len(HUES)] for k, a in enumerate(aggs)}


def colours(n):
    if n.kind != 'missing' and n.status == 'orphan':
        return ALERT
    return PALETTE[n.kind]


def parts(n):
    """(title, subtitle) of a node's card."""
    if n.kind in ('category', 'folder'):
        return n.label + '/', ' · '.join(x for x in (letters(n.classes), str(n.count)) if x)
    if n.kind == 'module':
        return n.label, letters(n.classes)
    if n.kind == 'missing':
        return n.label, 'no such module'
    if n.kind == 'aggregate':
        return n.label, ', '.join(c for c in CLASS_ORDER if c in n.classes)
    return n.label, ''


def style(n):
    """Mermaid class names for a card."""
    out = [n.kind]
    if n.kind == 'category' and n.status in ('orphan', 'by-module'):
        out.append(n.status.replace('-', ''))
    return out


def box_look(g, b):
    """(fill, outline, dashed, alert) for a container."""
    if b.kind == 'area':
        return (*PALETTE['area'], False, False)
    if b.kind == 'entry':
        return (*ENTRY, False, False)
    n = g.nodes[b.id]
    alert = colours(n) == ALERT
    return BOX_FILL, colours(n)[1], n.status == 'by-module', alert
