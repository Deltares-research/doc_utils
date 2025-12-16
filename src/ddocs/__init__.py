"""TSVKW."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("Deltares-HMS-Docs")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "unknown"
