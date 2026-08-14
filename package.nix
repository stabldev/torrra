{ lib
, python3Packages
, src
, version
}:

python3Packages.buildPythonApplication {
  pname = "torrra";
  inherit version src;

  pyproject = true;

  build-system = with python3Packages; [ hatchling ];

  nativeBuildInputs = with python3Packages; [ pythonRelaxDepsHook ];

  # pyproject.toml lists "libtorrent" (provided by nixpkgs as libtorrent-rasterbar,
  # different name) and "libtorrent-windows-dll" (Windows-only, irrelevant here).
  # Remove both so the runtime deps check doesn't fail;
  # libtorrent-rasterbar is still injected via dependencies below.
  pythonRemoveDeps = [ "libtorrent" "libtorrent-windows-dll" ];

  dependencies = with python3Packages; [
    libtorrent-rasterbar
    textual
    httpx
    click
    diskcache
    platformdirs
    tomli-w
  ];

  pythonImportsCheck = [ "torrra" ];

  meta = {
    description = "Search and download torrents from the CLI, powered by Jackett/Prowlarr and Libtorrent";
    homepage = "https://github.com/stabldev/torrra";
    license = lib.licenses.mit;
    mainProgram = "torrra";
    platforms = lib.platforms.unix;
  };
}
