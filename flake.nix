{
    description = "Draw a flake's modules tree: Mermaid, Graphviz, and an interactive page (experimental)";

    inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    # For readers new to Nix: everything below is what `nix` commands find in
    # this repository. Each output is built once per system in `systems`:
    #   packages   `nix build`, or `nix profile install`: the module-graph command
    #   apps       `nix run . -- <args>`: runs that command
    #   devShells  `nix develop`: a shell with python3, just, graphviz, chromium
    #   checks     `nix flake check`: the unit tests and a run of the command
    #   lib        functions for other flakes: a drawing, or a check, built by Nix
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

            # The command, built from whichever nixpkgs `pkgs` is: this flake's
            # for `packages`, the caller's for `lib`. Python stdlib only.
            # `--flake` runs the `nix` already on PATH.
            mkModuleGraph = pkgs: pkgs.writeShellApplication {
                name          = "module-graph";
                runtimeInputs = [ pkgs.python3 ];
                text          = ''PYTHONSAFEPATH=1 PYTHONPATH=${src} exec python3 -m module_graph "$@"'';
            };

            # A document as Nix data (a flake's `moduleGraph`), as a file the
            # command reads: `$graphPath` in the build.
            withGraph = graph: { graph = builtins.toJSON graph; passAsFile = [ "graph" ]; };
            # `config` is a path (./module-graph.toml), copied into the store
            # for the build; a string path outside the store isn't visible there.
            configFlag = config: lib.optionalString (config != null) "--config ${lib.escapeShellArg "${config}"}";
        in
        {
            packages = forAll (pkgs: rec {
                module-graph = mkModuleGraph pkgs;
                default = module-graph;
            });

            # For a flake that publishes `moduleGraph`, with `pkgs` its own
            # nixpkgs (wiki/using-the-tool.md, "Drawings built by Nix"):
            #
            #   packages.x86_64-linux.modules-html = flake-module-graph.lib.render {
            #       inherit pkgs; graph = self.moduleGraph; view = "html";
            #   };
            #   checks.x86_64-linux.drawings = flake-module-graph.lib.checkMarkdown {
            #       inherit pkgs; graph = self.moduleGraph; src = self; files = [ "README.md" ];
            #   };
            lib = {
                # One drawing as a file: `view` is tree, hosts, dot or html;
                # `args` are the filters (`[ "--depth" "1" ]`), `config` a
                # layout file, as a path.
                render = { pkgs, graph, view ? "html", args ? [ ], config ? null }:
                    pkgs.runCommand "module-graph-${view}"
                        (withGraph graph // { nativeBuildInputs = [ (mkModuleGraph pkgs) ]; }) ''
                        module-graph ${lib.escapeShellArg view} "$graphPath" ${configFlag config} \
                            ${lib.escapeShellArgs args} -o "$out"
                    '';
                # Fails when a module-graph block in `files` (paths inside
                # `src`) is stale; the message names the file and how to fix it.
                checkMarkdown = { pkgs, graph, src, files, config ? null }:
                    pkgs.runCommand "module-graph-markdown-check"
                        (withGraph graph // { nativeBuildInputs = [ (mkModuleGraph pkgs) ]; }) ''
                        cd ${src}
                        module-graph markdown --check "$graphPath" ${configFlag config} \
                            ${lib.concatMapStringsSep " " (f: "--file ${lib.escapeShellArg f}") files}
                        touch "$out"
                    '';
            };

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
                # lib, as another flake calls it: the same bytes as the saved views
                render = let
                    drawn = self.lib.render {
                        inherit pkgs; graph = lib.importJSON ./tests/fixtures/golden.json;
                        view = "hosts"; config = ./tests/fixtures/golden.toml;
                    };
                in pkgs.runCommand "module-graph-lib-render" { } ''
                    cmp ${drawn} ${./tests/expected/golden/hosts.mmd} && touch $out
                '';
                markdown = self.lib.checkMarkdown {
                    inherit pkgs; graph = lib.importJSON ./tests/fixtures/golden.json;
                    src = ./tests/fixtures; files = [ "drawings.md" ]; config = ./tests/fixtures/golden.toml;
                };
            });
        };
}
