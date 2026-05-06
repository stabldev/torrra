{
  lib,
  python3Packages,
  fetchPypi,
}:
python3Packages.buildPythonApplication rec {
  pname = "torrra";
  version = "2.0.7";

  pyproject = true;

  src = fetchPypi {
    inherit pname version;
    hash = "sha256-eg7v/MKLSm6bnBEtSEVR+/jMnSnEzhbZHH8V3RzRnlo=";
  };

  build-system = with python3Packages; [hatchling];

  nativeBuildInputs = with python3Packages; [pythonRelaxDepsHook];

  # The wheel declares "libtorrent" (provided by nixpkgs as libtorrent-rasterbar,
  # different name) and "libtorrent-windows-dll" (Windows-only, irrelevant here).
  # Remove both from wheel metadata so the runtime deps check doesn't fail;
  # libtorrent-rasterbar is still injected via dependencies below.
  pythonRemoveDeps = ["libtorrent" "libtorrent-windows-dll"];

  dependencies = with python3Packages; [
    libtorrent-rasterbar
    textual
    httpx
    click
    diskcache
    platformdirs
    tomli-w
  ];

  pythonImportsCheck = ["torrra"];

  meta = with lib; {
    description = "Search and download torrents from the CLI, powered by Jackett/Prowlarr and Libtorrent";
    homepage = "https://github.com/stabldev/torrra";
    license = licenses.mit;
    mainProgram = "torrra";
    platforms = platforms.unix;
  };
}
