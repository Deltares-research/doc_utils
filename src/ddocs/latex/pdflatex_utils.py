"""Locate, verify, and install pdfLaTeX (via TinyTeX) for the ddocs pipeline.

Building PDFs from the generated LaTeX needs a TeX engine (``pdflatex``) plus a set
of packages and `biber`. Unlike pandoc there is no single downloadable binary, so
this module uses **TinyTeX** -- a lightweight, root-free, cross-platform distribution
built on TeX Live -- as the install backend:

1. `sanity_check` -- is `pdflatex` (or `biber`) already callable?
2. `check_pdflatex_installed` -- if not, download and run the official TinyTeX
   installer (no admin rights), add its `bin` directory to `PATH` for the current
   process, and `tlmgr install` the package collections that mirror the
   `texlive-*` apt packages.
3. `install_missing_packages` -- a MiKTeX-style helper that scans a LaTeX build log
   for missing files and `tlmgr install`s them (TeX Live does not do this natively).

The `PATH` change affects only the current process and the subprocesses it spawns,
not the parent shell.
"""

import argparse
import glob
import os
import platform
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

# tlmgr collections/packages mirroring the texlive-* apt packages ddocs builds need:
#   texlive-latex-extra      -> collection-latexextra
#   texlive-fonts-recommended-> collection-fontsrecommended
#   texlive-fonts-extra      -> collection-fontsextra
#   texlive-bibtex-extra     -> collection-bibtexextra
#   texlive-science          -> collection-mathscience
#   biber                    -> biber (+ biblatex)
REQUIRED_TLMGR_PACKAGES = (
    "collection-latexextra",
    "collection-fontsrecommended",
    "collection-fontsextra",
    "collection-bibtexextra",
    "collection-mathscience",
    "biber",
    "biblatex",
)

_UNIX_INSTALLER_URL = "https://yihui.org/tinytex/install-bin-unix.sh"
# Use the PowerShell installer directly: the .bat wrapper runs `curl -O 'URL'`, whose
# single-quoted URL is mis-parsed by cmd.exe (curl error 3 / bad URL).
_WINDOWS_INSTALLER_URL = "https://tinytex.yihui.org/install-bin-windows.ps1"
# yihui.org rejects the default urllib User-Agent (HTTP 403), so send a browser-like one.
_DOWNLOAD_HEADERS = {"User-Agent": "Mozilla/5.0"}

# Matches lines such as: ! LaTeX Error: File `tikz.sty' not found.
_MISSING_FILE_RE = re.compile(r"File `([^']+\.(?:sty|cls|tex|fd|cfg))' not found")


def sanity_check(command: str = "pdflatex") -> bool:
    """Check whether a TeX command is callable from the command line.

    Runs `<command> --version` as a subprocess. This only inspects what is already
    reachable on `PATH` -- it never downloads or installs anything.

    Args:
        command: The executable to probe, e.g. `"pdflatex"` or `"biber"`.

    Returns:
        True if `<command> --version` runs successfully, False otherwise.

    Examples:
        - Branch on whether pdflatex is available:
            ```python
            >>> from ddocs.latex.pdflatex_utils import sanity_check
            >>> if sanity_check():  # doctest: +SKIP
            ...     print("ready to build PDFs")
            ready to build PDFs

            ```
        - Probe a different tool such as biber:
            ```python
            >>> from ddocs.latex.pdflatex_utils import sanity_check
            >>> sanity_check("biber")  # doctest: +SKIP
            True

            ```

    See Also:
        check_pdflatex_installed: Verify pdflatex and install TinyTeX when missing.
    """
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        first_line = result.stdout.splitlines()[0] if result.stdout else command
        print(f"Found {command}: {first_line}")
        found = True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        found = False
    return found


def _tinytex_root_candidates() -> list[str]:
    """Return the platform-specific directories where TinyTeX may be installed."""
    home = os.path.expanduser("~")
    system = platform.system()
    if system == "Windows":
        candidates = [os.path.join(os.environ.get("APPDATA", home), "TinyTeX")]
    elif system == "Darwin":
        candidates = [os.path.join(home, "Library", "TinyTeX"), os.path.join(home, ".TinyTeX")]
    else:
        candidates = [os.path.join(home, ".TinyTeX")]
    return candidates


def find_tex_bin_dir() -> str | None:
    """Locate the TinyTeX `bin` directory that contains `pdflatex`.

    TinyTeX installs the binaries under `<root>/bin/<platform>` (e.g.
    `bin/x86_64-linux` or `bin/windows`); the exact platform folder is resolved by
    globbing so it works across architectures.

    Returns:
        The absolute path of the directory containing the `pdflatex` executable, or
        None if no TinyTeX installation is found.

    Examples:
        - Get the bin directory if TinyTeX is installed:
            ```python
            >>> from ddocs.latex.pdflatex_utils import find_tex_bin_dir
            >>> bin_dir = find_tex_bin_dir()  # doctest: +SKIP
            >>> bin_dir.endswith("bin") or "bin" in bin_dir  # doctest: +SKIP
            True

            ```
    """
    exe = "pdflatex.exe" if platform.system() == "Windows" else "pdflatex"
    found = None
    for root in _tinytex_root_candidates():
        for candidate in sorted(glob.glob(os.path.join(root, "bin", "*"))):
            if os.path.exists(os.path.join(candidate, exe)):
                found = candidate
                break
        if found:
            break
    return found


def _prepend_to_path(directory: str) -> None:
    """Prepend `directory` to this process's `PATH` if not already present."""
    if directory and directory not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")
        print(f"Added TeX to PATH: {directory}")


def _install_tinytex() -> None:
    """Download and run the official TinyTeX installer for the current platform.

    Raises:
        urllib.error.URLError: If the installer script cannot be downloaded.
        subprocess.CalledProcessError: If the installer script exits non-zero.
    """
    system = platform.system()
    print("pdflatex not found. Installing TinyTeX (this may take a few minutes)...")
    if system == "Windows":
        url = _WINDOWS_INSTALLER_URL
        suffix = ".ps1"
        runner = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    else:
        url, suffix, runner = _UNIX_INSTALLER_URL, ".sh", ["sh"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        script_path = handle.name
    try:
        request = urllib.request.Request(url, headers=_DOWNLOAD_HEADERS)
        with urllib.request.urlopen(request) as response, open(script_path, "wb") as out:
            out.write(response.read())
        subprocess.run([*runner, script_path], check=True)
    finally:
        if os.path.exists(script_path):
            os.unlink(script_path)


def install_tlmgr_packages(packages: tuple[str, ...] | list[str] = REQUIRED_TLMGR_PACKAGES) -> bool:
    """Install TeX packages with `tlmgr`.

    Args:
        packages: The tlmgr package/collection names to install. Defaults to
            :data:`REQUIRED_TLMGR_PACKAGES`, which mirror the `texlive-*` apt set.

    Returns:
        True if `tlmgr install` succeeded, False otherwise.

    Examples:
        - Install the default package set after TinyTeX is on `PATH`:
            ```python
            >>> from ddocs.latex.pdflatex_utils import install_tlmgr_packages
            >>> install_tlmgr_packages()  # doctest: +SKIP
            True

            ```
        - Install a specific package:
            ```python
            >>> from ddocs.latex.pdflatex_utils import install_tlmgr_packages
            >>> install_tlmgr_packages(["tikz"])  # doctest: +SKIP
            True

            ```
    """
    package_list = list(packages)
    if package_list:
        print(f"Installing TeX packages via tlmgr: {' '.join(package_list)}")
    try:
        subprocess.run(["tlmgr", "install", *package_list], check=True)
        ok = True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        ok = False
    return ok


def find_missing_packages(log_text: str) -> list[str]:
    """Extract package names for files reported missing in a LaTeX build log.

    Scans for `File `name.sty' not found` style errors and returns the file stems
    (the usual tlmgr package name). Duplicates are removed while preserving order.

    Args:
        log_text: The contents of a `.log` file (or pdflatex stdout/stderr).

    Returns:
        A list of candidate tlmgr package names, in first-seen order.

    Examples:
        - Pull one missing package from a log fragment:
            ```python
            >>> from ddocs.latex.pdflatex_utils import find_missing_packages
            >>> find_missing_packages("! LaTeX Error: File `tikz.sty' not found.")
            ['tikz']

            ```
        - De-duplicate and keep order across several errors:
            ```python
            >>> from ddocs.latex.pdflatex_utils import find_missing_packages
            >>> log = "File `a.sty' not found\\nFile `b.cls' not found\\nFile `a.sty' not found"
            >>> find_missing_packages(log)
            ['a', 'b']

            ```
    """
    names: list[str] = []
    for match in _MISSING_FILE_RE.finditer(log_text):
        stem = match.group(1).rsplit(".", 1)[0]
        if stem not in names:
            names.append(stem)
    return names


def install_missing_packages(log_text: str) -> list[str]:
    """Install packages for any files a LaTeX log reports as missing.

    This is the TeX Live equivalent of MiKTeX's install-on-build behaviour: parse the
    log, `tlmgr install` whatever was missing, and let the caller recompile.

    Args:
        log_text: The contents of a LaTeX `.log` file (or build output).

    Returns:
        The list of package names install was attempted for (empty if none missing).

    Examples:
        - No missing files means nothing is installed:
            ```python
            >>> from ddocs.latex.pdflatex_utils import install_missing_packages
            >>> install_missing_packages("This is pdfTeX ... output written")
            []

            ```

    See Also:
        find_missing_packages: The log parser this builds on.
        install_tlmgr_packages: Runs the actual `tlmgr install`.
    """
    packages = find_missing_packages(log_text)
    if packages:
        install_tlmgr_packages(packages)
    return packages


def check_pdflatex_installed(install_packages: bool = True) -> bool:
    """Ensure `pdflatex` is callable, installing TinyTeX when it is missing.

    If pdflatex is already on `PATH` this returns immediately. Otherwise an existing
    TinyTeX install is located (or the official installer is downloaded and run), its
    `bin` directory is prepended to `PATH` for this process, and the required
    package collections are installed with `tlmgr`.

    Args:
        install_packages: When True (default), run `tlmgr install` for
            :data:`REQUIRED_TLMGR_PACKAGES` after a fresh TinyTeX install.

    Returns:
        True if pdflatex is accessible after the call, False otherwise.

    Raises:
        urllib.error.URLError: If the TinyTeX installer cannot be downloaded.
        subprocess.CalledProcessError: If the installer script fails.

    Examples:
        - Guard a PDF build on pdflatex being available:
            ```python
            >>> from ddocs.latex.pdflatex_utils import check_pdflatex_installed
            >>> if check_pdflatex_installed():  # doctest: +SKIP
            ...     print("building pdf")
            building pdf

            ```

    See Also:
        sanity_check: The PATH-only probe this builds on.
        check_pdflatex_cli: Thin wrapper mapping the result to an exit code.
    """
    installed = sanity_check("pdflatex")
    if not installed:
        bin_dir = find_tex_bin_dir()
        if bin_dir is None:
            _install_tinytex()
            bin_dir = find_tex_bin_dir()

        if bin_dir:
            _prepend_to_path(bin_dir)
            if install_packages:
                install_tlmgr_packages()
            installed = sanity_check("pdflatex")
            if installed:
                print("pdflatex is now accessible!")

        if not installed:
            print("Warning: TinyTeX was installed but pdflatex is not accessible from the command line.")
    return installed


def build_pdf(tex_file: str | Path, max_runs: int = 4, install_missing: bool = True) -> Path:
    """Compile a `.tex` file to PDF with `pdflatex`, installing missing packages.

    Ensures `pdflatex` is available (installing TinyTeX if needed), then runs it from
    the source file's directory so a document class and relative assets resolve. After a
    failed run it parses the log for missing packages and `tlmgr install`s them before
    retrying (the MiKTeX-style behaviour); on success it runs a second pass to resolve
    cross-references and the table of contents.

    Args:
        tex_file: Path to the `.tex` file to compile.
        max_runs: Maximum number of `pdflatex` attempts before giving up.
        install_missing: When True, `tlmgr install` packages reported missing in the
            log between attempts.

    Returns:
        The :class:`pathlib.Path` of the produced PDF (`<stem>.pdf` next to the source).

    Raises:
        RuntimeError: If pdflatex cannot be made available, or no PDF is produced.

    Examples:
        - Build a PDF from a LaTeX file (requires a TeX engine):
            ```python
            >>> from ddocs.latex.pdflatex_utils import build_pdf
            >>> pdf = build_pdf("report.tex")  # doctest: +SKIP
            >>> pdf.name  # doctest: +SKIP
            'report.pdf'

            ```

    See Also:
        check_pdflatex_installed: Ensures the engine is present.
        install_missing_packages: Installs packages reported missing in the log.
    """
    tex_path = Path(tex_file)
    work_dir = tex_path.parent
    pdf_path = work_dir / f"{tex_path.stem}.pdf"

    if not check_pdflatex_installed():
        raise RuntimeError("pdflatex is not available and TinyTeX could not be installed")

    succeeded = False
    for _ in range(max_runs):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path.name],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
        )
        log = f"{result.stdout}\n{result.stderr}"
        if result.returncode == 0:
            succeeded = True
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path.name],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
            )
            break
        if not (install_missing and install_missing_packages(log)):
            break

    if not (succeeded and pdf_path.exists()):
        raise RuntimeError(f"pdflatex did not produce {pdf_path.name}")
    return pdf_path


def check_pdflatex_cli(args: argparse.Namespace | None = None) -> int:
    """CLI handler for the `check-pdflatex` command.

    Ensures pdflatex is available (installing TinyTeX if necessary) and maps the result
    to a process exit code suitable for :func:`sys.exit`.

    Args:
        args: Parsed CLI arguments from argparse. Unused -- accepted only so the handler
            matches the calling convention of the other `ddocs` subcommand handlers.
            Defaults to None.

    Returns:
        0 if pdflatex is accessible, 1 otherwise.

    Examples:
        - Run the check and use the result as a process exit code:
            ```python
            >>> from ddocs.latex.pdflatex_utils import check_pdflatex_cli
            >>> exit_code = check_pdflatex_cli()  # doctest: +SKIP
            >>> exit_code  # doctest: +SKIP
            0

            ```

    See Also:
        check_pdflatex_installed: The underlying check-and-install routine.
    """
    return 0 if check_pdflatex_installed() else 1
