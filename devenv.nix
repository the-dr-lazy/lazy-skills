{
  pkgs,
  lib,
  config,
  ...
}:

let
  # GHC with every package the Haskell examples in skills/ import.
  ghc = pkgs.haskellPackages.ghcWithPackages (
    p: with p; [
      QuickCheck
      hedgehog
      containers
      mtl
      transformers
      text
      free
      polysemy
      polysemy-plugin
      effectful
      effectful-core
      effectful-th
      lens
      optics
      aeson
      hspec
      time
    ]
  );
  langs = config.languages;
  python = langs.python.package;

  # Wrappers carry their toolchain, so git hooks work outside the shell too.
  check-skills = pkgs.writeShellScriptBin "check-skills" ''
    exec ${python}/bin/python3 "$(git rev-parse --show-toplevel)/tools/check_skills.py" "$@"
  '';
  check-examples = pkgs.writeShellScriptBin "check-examples" ''
    export GHC=${langs.haskell.package}/bin/ghc
    export CXX=${config.stdenv.cc}/bin/clang++
    export CXXFLAGS="-I${pkgs.rapidcheck.dev}/include ''${CXXFLAGS:-}"
    export PATH=${lib.makeBinPath [ langs.javascript.package ]}:$PATH
    exec ${python}/bin/python3 "$(git rev-parse --show-toplevel)/tools/check_examples.py" "$@"
  '';
in
{
  cachix.pull = [ "the-dr-lazy" ];
  cachix.push = "the-dr-lazy";

  # Clang instead of GCC for the whole shell (sets CC/CXX). Packages add their
  # include paths to NIX_CFLAGS_COMPILE, so no CXXFLAGS/GHC env is needed here.
  stdenv = pkgs.clangStdenv;

  languages.haskell = {
    enable = true;
    package = ghc;
    cabal.enable = true;
    lsp.enable = true;
  };
  languages.cplusplus.enable = true;
  languages.typescript.enable = true;

  # TypeScript toolchain for the examples (typescript, fast-check, effect):
  # `npm clean-install` in tools/ts whenever package-lock.json changes.
  languages.javascript = {
    enable = true;
    package = pkgs.nodejs_22;
    directory = "tools/ts";
    npm = {
      enable = true;
      install.enable = true;
    };
  };

  languages.python = {
    enable = true;
    package = pkgs.python3.withPackages (p: [ p.pyyaml ]);
  };

  languages.nix.enable = true;

  # Hooks run on commit and in `devenv test`, not on every shell entry.
  tasks."devenv:git-hooks:run".before = lib.mkForce [ ];

  git-hooks.hooks = {
    check-skills = {
      enable = true;
      name = "check-skills";
      description = "Validate SKILL.md frontmatter, links, and manifests";
      entry = "${check-skills}/bin/check-skills";
      files = ''^(skills/|README\.md$|\.claude-plugin/)'';
      pass_filenames = false;
    };
    # Type-check only the code blocks of the Markdown files being committed.
    check-examples = {
      enable = true;
      name = "check-examples";
      description = "Type-check Haskell, TypeScript, and C++ blocks in changed skills";
      entry = "${check-examples}/bin/check-examples";
      files = ''^skills/.*\.md$'';
    };
    actionlint.enable = true;
    check-json.enable = true;
    nixfmt.enable = true;
  };

  enterShell = ''
    echo "lazy-skills: check-skills, check-examples [--lang haskell|typescript|cpp] [paths...]"
  '';

  # Every hook on every file: check-skills, check-examples, check-json, nixfmt.
  enterTest = ''
    ${lib.getExe config.git-hooks.package} run --all-files --show-diff-on-failure
  '';

  packages = [
    pkgs.rapidcheck
    pkgs.nixfmt
    check-skills
    check-examples
  ];
}
