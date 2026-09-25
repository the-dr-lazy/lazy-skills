{
  description = "Toolchain for type-checking the Haskell, TypeScript, and C++ examples in skills/";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { nixpkgs, ... }:
    let
      forAllSystems = f: nixpkgs.lib.genAttrs [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ]
        (system: f nixpkgs.legacyPackages.${system});
    in {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.haskellPackages.ghcWithPackages (p: with p; [
              QuickCheck hedgehog containers mtl transformers text free polysemy polysemy-plugin
              effectful effectful-core effectful-th lens optics aeson hspec time
            ]))
            pkgs.gcc14
            pkgs.rapidcheck
            pkgs.nodejs_22
            pkgs.python3
          ];
          CXX = "g++";
          CXXFLAGS = "-I${pkgs.rapidcheck.dev}/include";
        };
      });
    };
}
