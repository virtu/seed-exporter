{
  description = "Bitcoin seed exporter";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
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
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication;
    in
    {
      packages = {
        seed-exporter = mkPoetryApplication {
          projectDir = ./.;
        };
        default = self.packages.${system}.seed-exporter;
      };

      devShells.default = pkgs.mkShell {
        packages = with pkgs; [ poetry ];
      };
    });
}
