from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("torrra")
except PackageNotFoundError:
    __version__ = "dev"
