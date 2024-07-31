{
  description = "Bitcoin seed exporter";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }: {
    nixosModules.seedExporter = import ./module.nix self;
  } // flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication mkPoetryEnv;
    in
    {
      packages = {
        seed-exporter = mkPoetryApplication {
          projectDir = ./.;
        };
        default = self.packages.${system}.seed-exporter;
      };

      devShell = pkgs.mkShell {
        buildInputs = with pkgs; [
          pylint
          poetry
          (mkPoetryEnv {
            projectDir = ./.;
            editablePackageSources = {
              seed-exporter = ./src;
            };
          })
        ];
      };
    }
  );
}
