{
    description = "Draw a flake's modules tree: Mermaid, Graphviz, and an interactive page (experimental)";

    inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    # For readers new to Nix: everything below is what `nix` commands find in
    # this repository. Each output is built once per system in `systems`:
    #   packages   `nix build`, or `nix profile install`: the module-graph command
    #   apps       `nix run . -- <args>`: runs that command
    #   devShells  `nix develop`: a shell with python3, just, graphviz, chromium
    #   checks     `nix flake check`: the unit tests and a run of the command
    # The tool itself is plain Python (module_graph/); Nix only packages it.
    outputs = { self, nixpkgs }:
        let
            inherit (nixpkgs) lib;
            systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
            # forAll f = { x86_64-linux = f pkgs-for-x86_64-linux; ... }
            forAll  = f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

            # Only these files are copied into the Nix store, so editing the
            # README doesn't rebuild the command.
            src   = lib.fileset.toSource { root = ./.; fileset = ./module_graph; };
            tests = lib.fileset.toSource { root = ./.; fileset = lib.fileset.unions [ ./module_graph ./tests ]; };
        in
        {
            packages = forAll (pkgs: rec {
                # Python stdlib only. `--flake` runs the `nix` already on PATH.
                module-graph = pkgs.writeShellApplication {
                    name          = "module-graph";
                    runtimeInputs = [ pkgs.python3 ];
                    text          = ''PYTHONSAFEPATH=1 PYTHONPATH=${src} exec python3 -m module_graph "$@"'';
                };
                default = module-graph;
            });

            apps = forAll (pkgs: {
                default = {
                    type    = "app";
                    program = lib.getExe self.packages.${pkgs.stdenv.hostPlatform.system}.default;
                    meta.description = "Draw a flake's modules tree from a module-graph document";
                };
            });

            # `nix develop`: what the recipes in justfile need. Chromium only
            # where nixpkgs builds it, for `just browser`.
            devShells = forAll (pkgs: {
                default = pkgs.mkShell {
                    packages = with pkgs; [ just python3 graphviz ]
                        ++ lib.optional pkgs.stdenv.hostPlatform.isLinux chromium;
                };
            });

            checks = forAll (pkgs: let
                unittests = python: pkgs.runCommand "module-graph-tests-${python.version}"
                    { nativeBuildInputs = [ python ]; } ''
                        cp -r ${tests} src && chmod -R u+w src && cd src
                        python3 -m unittest discover -s tests
                        touch $out
                    '';
            in {
                tests = unittests pkgs.python3;
                # the oldest Python pyproject.toml's requires-python allows
                python311 = unittests pkgs.python311;
                # the packaged command, on the browser fixture
                package = pkgs.runCommand "module-graph-package" { } ''
                    ${lib.getExe self.packages.${pkgs.stdenv.hostPlatform.system}.default} \
                        hosts ${./tests/fixtures/browser.json} > $out
                    grep -q 'flowchart TB' $out
                '';
            });
        };
}
