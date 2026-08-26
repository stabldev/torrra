{
  description = "Nix flake for torrra - Search and download torrents from the CLI";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      version = "2.4.0";
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system:
        f nixpkgs.legacyPackages.${system}
      );
    in
    {
      packages = forEachSystem (pkgs: rec {
        torrra = pkgs.callPackage ./package.nix { src = self; inherit version; };
        default = torrra;
      });

      overlays.default = final: _prev: {
        torrra = final.callPackage ./package.nix { src = self; inherit version; };
      };

      nixosModules.default = { lib, pkgs, config, ... }: {
        options.programs.torrra.enable = lib.mkEnableOption "torrra torrent CLI";

        config = lib.mkIf config.programs.torrra.enable {
          nixpkgs.overlays = [ self.overlays.default ];
          environment.systemPackages = [ pkgs.torrra ];
        };
      };
    };
}
