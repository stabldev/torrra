{
  description = "Nix flake for torrra - Search and download torrents from the CLI";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forEachSystem (pkgs:
        let torrra = pkgs.callPackage ./package.nix { };
        in {
          inherit torrra;
          default = torrra;
        });

      overlays.default = final: _prev: {
        torrra = final.callPackage ./package.nix { };
      };

      nixosModules.default = { pkgs, ... }: {
        nixpkgs.overlays = [ self.overlays.default ];
        environment.systemPackages = [ pkgs.torrra ];
      };
    };
}
