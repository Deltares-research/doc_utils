import os
import sys
import shutil
import subprocess

import pypandoc
from pypandoc.pandoc_download import download_pandoc


def sanity_check() -> bool:
    """Check whether a `pandoc` executable is callable from the command line.

    Returns:
        True if `pandoc --version` runs successfully, False otherwise.
    """
    try:
        result = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Found Pandoc: {result.stdout.split()[1]}")
        found = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        found = False
    return found


def _get_pandoc_dir():
    """Return the directory that contains the pandoc executable.

    Prefers the location reported by `pypandoc.get_pandoc_path()` (which knows
    where `download_pandoc` installs the binary). Falls back to the
    platform-specific default install folder used by pypandoc.

    Returns:
        The directory path as a string, or None if it cannot be determined.
    """
    pandoc_dir = None
    try:
        pandoc_path = pypandoc.get_pandoc_path()
        pandoc_dir = os.path.dirname(pandoc_path)
        if not pandoc_dir:
            # get_pandoc_path() may return a bare name (e.g. "pandoc") when
            # pandoc is resolved via PATH; resolve it to an absolute location.
            resolved = shutil.which(pandoc_path)
            pandoc_dir = os.path.dirname(resolved) if resolved else None
    except Exception:
        pandoc_dir = None

    if not pandoc_dir:
        if sys.platform == "win32":
            pandoc_dir = os.path.expanduser("~") + r"\AppData\Local\Pandoc"
        else:
            pandoc_dir = os.path.join(os.path.expanduser("~"), ".local", "bin")

    return pandoc_dir


def check_pandoc_installed() -> bool:
    """Ensure `pandoc` is callable from the command line.

    If pandoc is already on PATH, nothing happens. Otherwise a prebuilt binary
    is downloaded via pypandoc and its install directory is prepended to this
    process's PATH so that the binary (and any subprocess spawned from this
    process) can invoke `pandoc` directly.

    Returns:
        True if pandoc is accessible after the call, False otherwise.
    """
    installed = sanity_check()
    if not installed:
        print("Pandoc not found. Downloading...")
        download_pandoc()

        pandoc_dir = _get_pandoc_dir()
        if pandoc_dir and os.path.exists(pandoc_dir):
            if pandoc_dir not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = pandoc_dir + os.pathsep + os.environ.get("PATH", "")
                print(f"Added pandoc to PATH: {pandoc_dir}")

            installed = sanity_check()
            if installed:
                print("Pandoc is now accessible!")

        if not installed:
            print("Warning: Pandoc downloaded but not accessible from the command line.")

    return installed
