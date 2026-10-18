# List the recipes
default:
    @just --list

# Unit tests
test:
    python3 -m unittest discover -s tests

# Every view against its saved output; `just golden --update` rewrites them
golden *args:
    python3 tests/golden.py {{args}}

# The page in headless Chromium, against tests/expected/browser.json
browser:
    python3 tests/browser.py

# nix flake check: the unit tests and the packaged command
check:
    nix flake check

# The packaged command on the graph dirs-as-categories publishes, at a pinned
# revision: bump it on purpose, with any change the new graph needs here.
dirs-as-categories := "github:NireBryce/dirs-as-categories/f2c44941d0cf4866cf25d1868c39bb04965dcd41"
e2e:
    #!/usr/bin/env bash
    set -euo pipefail
    graph=$(mktemp)
    trap 'rm -f "$graph"' EXIT
    nix eval --json '{{dirs-as-categories}}#tests.main' --apply 'm: m.graph' > "$graph"
    # captured first: `cmd | grep -q` fails under pipefail when grep exits early
    hosts=$(nix run . -- hosts "$graph"); grep -q 'enables' <<<"$hosts"
    html=$(nix run . -- html "$graph"); grep -q '"title":"hm-agg"' <<<"$html"
    echo 'e2e: hosts and html drew the published graph'

# Everything CI runs (the browser check needs chromium: `nix develop`)
preflight: test browser check e2e
