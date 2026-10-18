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

# nix flake check: the unit tests (also on Python 3.11) and the packaged command
check:
    nix flake check

# Everything CI runs (the browser check needs chromium: `nix develop`)
preflight: test browser check
