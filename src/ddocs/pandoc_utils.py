"""Locate, verify, and install the Pandoc executable for the ddocs pipeline.

The ``ddocs`` Markdown-to-LaTeX conversion shells out to the ``pandoc`` command,
so pandoc must be reachable on ``PATH``. This module verifies that pandoc is
callable, downloads a prebuilt binary via :mod:`pypandoc` when it is missing, and
makes the downloaded binary discoverable by prepending its directory to ``PATH``
for the current process (and any subprocess it spawns).
"""

import os
import sys
import shutil
import subprocess

import pypandoc
from pypandoc.pandoc_download import download_pandoc


def sanity_check() -> bool:
    """Check whether a ``pandoc`` executable is callable from the command line.

    Runs ``pandoc --version`` as a subprocess. On success the detected version is
    printed and ``True`` is returned; if pandoc is missing from ``PATH`` or the
    call fails, ``False`` is returned. This only inspects what is already
    reachable -- it never downloads or installs anything.

    Returns:
        True if ``pandoc --version`` runs successfully, False otherwise.

    Examples:
        - Branch on whether pandoc is available:
            ```python
            >>> from ddocs.pandoc_utils import sanity_check
            >>> if sanity_check():  # doctest: +SKIP
            ...     print("ready to convert")
            ... else:
            ...     print("pandoc missing")
            ready to convert

            ```
        - Use the boolean result to pick a fallback message:
            ```python
            >>> from ddocs.pandoc_utils import sanity_check
            >>> available = sanity_check()  # doctest: +SKIP
            >>> "ok" if available else "install pandoc first"  # doctest: +SKIP
            'ok'

            ```

    See Also:
        check_pandoc_installed: Verify pandoc and download it when it is missing.
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

    Prefers the location reported by ``pypandoc.get_pandoc_path()`` (which knows
    where :func:`download_pandoc` installs the binary). If that returns a bare
    name such as ``"pandoc"``, the absolute path is resolved via
    :func:`shutil.which`. When neither succeeds, the platform-specific default
    install folder used by pypandoc is returned (``~\\AppData\\Local\\Pandoc`` on
    Windows, ``~/.local/bin`` elsewhere), so the caller always gets a usable
    directory string rather than ``None``.

    Returns:
        The directory path containing (or expected to contain) the pandoc
        executable, as a string.

    Examples:
        - Get the directory and use it to build the executable path:
            ```python
            >>> import os
            >>> from ddocs.pandoc_utils import _get_pandoc_dir
            >>> pandoc_dir = _get_pandoc_dir()  # doctest: +SKIP
            >>> os.path.isdir(pandoc_dir) or pandoc_dir.endswith("bin")  # doctest: +SKIP
            True

            ```

    See Also:
        check_pandoc_installed: Adds this directory to ``PATH`` after downloading.
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
    """Ensure ``pandoc`` is callable from the command line.

    If pandoc is already on ``PATH`` this returns immediately. Otherwise a
    prebuilt binary is downloaded via :func:`download_pandoc` and its install
    directory is prepended to this process's ``PATH`` so the binary (and any
    subprocess spawned from this process) can invoke ``pandoc`` directly. The
    ``PATH`` change affects only the current process, not the parent shell.

    Returns:
        True if pandoc is accessible after the call, False if the download
        completed but the binary still could not be located on ``PATH``.

    Raises:
        RuntimeError: If pypandoc cannot download pandoc for the current
            platform (e.g. an unsupported OS or an invalid requested version).
        urllib.error.URLError: If the binary download fails due to network or
            connectivity problems.

    Examples:
        - Guard a conversion step on pandoc being available:
            ```python
            >>> from ddocs.pandoc_utils import check_pandoc_installed
            >>> if check_pandoc_installed():  # doctest: +SKIP
            ...     print("converting")
            converting

            ```
        - Abort early when pandoc cannot be made available:
            ```python
            >>> from ddocs.pandoc_utils import check_pandoc_installed
            >>> ready = check_pandoc_installed()  # doctest: +SKIP
            >>> ready or "could not install pandoc"  # doctest: +SKIP
            True

            ```

    See Also:
        sanity_check: The PATH-only check this function builds on.
        check_pandoc_cli: Thin wrapper that maps the result to an exit code.
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


def check_pandoc_cli(args=None) -> int:
    """CLI handler for the ``check-pandoc`` command.

    Ensures pandoc is available (downloading it if necessary) and maps the
    result to a process exit code suitable for ``sys.exit``.

    Args:
        args: Parsed CLI arguments from argparse. Unused -- accepted only so the
            handler matches the calling convention of the other ``ddocs``
            subcommand handlers. Defaults to None.

    Returns:
        0 if pandoc is accessible, 1 otherwise.

    Examples:
        - Run the check and use the result as a process exit code:
            ```python
            >>> import sys
            >>> from ddocs.pandoc_utils import check_pandoc_cli
            >>> exit_code = check_pandoc_cli()  # doctest: +SKIP
            >>> exit_code  # doctest: +SKIP
            0

            ```
        - The argparse namespace is accepted but ignored:
            ```python
            >>> import argparse
            >>> from ddocs.pandoc_utils import check_pandoc_cli
            >>> ns = argparse.Namespace(command="check-pandoc")
            >>> check_pandoc_cli(ns)  # doctest: +SKIP
            0

            ```

    See Also:
        check_pandoc_installed: The underlying check-and-install routine.
    """
    return 0 if check_pandoc_installed() else 1
