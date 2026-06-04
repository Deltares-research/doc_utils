"""Locate, verify, and install pdfLaTeX (via TinyTeX) for the ddocs pipeline.

Building PDFs from the generated LaTeX needs a TeX engine (``pdflatex``) plus a set
of packages and `biber`. Unlike pandoc there is no single downloadable binary, so
this module uses **TinyTeX** -- a lightweight, root-free, cross-platform distribution
built on TeX Live -- as the install backend:

1. `sanity_check` -- is `pdflatex` (or `biber`) already callable?
2. `check_pdflatex_installed` -- if not, install a TeX distribution. On Debian/Ubuntu it
   uses `apt-get install texlive-*` (fast); elsewhere it falls back to TinyTeX (root-free,
   cross-platform) and `tlmgr install`s the requested packages. Either way the packages a
   bare `pdflatex` needs for Deltares documents are provided. Tune via
   `ddocs pdflatex download --backend apt|tinytex|auto`, `--packages ...`, or `--no-packages`.
3. `install_missing_packages` -- a MiKTeX-style helper that scans a LaTeX build log
   for missing files and `tlmgr install`s them on demand (TeX Live does not do this
   natively). `build_pdf` uses it to fetch any package a document still needs.

The `PATH` change affects only the current process and the subprocesses it spawns,
not the parent shell.
"""

import argparse
import glob
import os
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

# Default tlmgr collections installed by ``check_pdflatex_installed`` so consumers that
# compile with a bare ``pdflatex`` (not ``build_pdf``) have the packages Deltares docs
# need. These mirror the ``texlive-*`` apt packages. Pass a smaller list to
# ``check_pdflatex_installed`` / ``ddocs pdflatex download --packages ...`` for a faster,
# leaner install when you know exactly what a document needs; ``build_pdf`` additionally
# installs anything still missing on demand.
REQUIRED_TLMGR_PACKAGES: tuple[str, ...] = (
    "collection-latexextra",
    "collection-fontsrecommended",
    "collection-fontsextra",
    "collection-bibtexextra",
    "collection-mathscience",
    "biber",
    "biblatex",
)

# Debian/Ubuntu ``apt`` packages providing the same TeX coverage. apt pulls prebuilt
# .debs from a fast mirror in parallel, so on a Linux runner with sudo this is far
# quicker than TinyTeX + per-package ``tlmgr`` downloads.
APT_TEXLIVE_PACKAGES: tuple[str, ...] = (
    "texlive-latex-base",
    "texlive-latex-extra",
    "texlive-fonts-recommended",
    "texlive-fonts-extra",
    "texlive-bibtex-extra",
    "texlive-science",
    "biber",
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
            :data:`REQUIRED_TLMGR_PACKAGES` (empty -- nothing is pre-installed).

    Returns:
        True if `tlmgr install` succeeded (or there was nothing to install), False
        otherwise.

    Examples:
        - Calling with no packages is a no-op that succeeds:
            ```python
            >>> from ddocs.latex.pdflatex_utils import install_tlmgr_packages
            >>> install_tlmgr_packages([])
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
    if not package_list:
        return True
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


def install_texlive_apt(packages: tuple[str, ...] | list[str] = APT_TEXLIVE_PACKAGES) -> bool:
    """Install a TeX Live subset on Debian/Ubuntu via `apt-get`.

    Runs `apt-get update` then `apt-get install -y <packages>` (prefixed with `sudo`
    when not already root). This is much faster than the TinyTeX / `tlmgr` backend on CI
    runners, but it requires `apt-get` and root privileges.

    Args:
        packages: The apt package names to install. Defaults to
            :data:`APT_TEXLIVE_PACKAGES`.

    Returns:
        True if the packages were installed, False if `apt-get` is unavailable or the
        install failed (e.g. no usable `sudo`).

    Examples:
        - Install the default TeX Live packages on Ubuntu:
            ```python
            >>> from ddocs.latex.pdflatex_utils import install_texlive_apt
            >>> install_texlive_apt()  # doctest: +SKIP
            True

            ```

    See Also:
        check_pdflatex_installed: Selects this backend automatically on Debian/Ubuntu.
    """
    if shutil.which("apt-get") is None:
        return False
    is_root = getattr(os, "geteuid", lambda: 1)() == 0
    sudo = [] if is_root else (["sudo"] if shutil.which("sudo") else [])
    package_list = list(packages)
    print(f"Installing TeX Live via apt-get: {' '.join(package_list)}")
    try:
        subprocess.run([*sudo, "apt-get", "update"], check=True)
        subprocess.run([*sudo, "apt-get", "install", "-y", *package_list], check=True)
        ok = True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        ok = False
    return ok


def check_pdflatex_installed(
    install_packages: bool = True,
    packages: tuple[str, ...] | list[str] = REQUIRED_TLMGR_PACKAGES,
    backend: str = "auto",
) -> bool:
    """Ensure `pdflatex` is callable, installing a TeX distribution when it is missing.

    If pdflatex is already on `PATH` this returns immediately. Otherwise a backend is
    used to install it:

    - **apt** -- on Debian/Ubuntu (with `sudo`) install the `texlive-*` packages via
      `apt-get`. Much faster on CI than `tlmgr`.
    - **tinytex** -- download and run the official TinyTeX installer (root-free,
      cross-platform), prepend its `bin` to `PATH`, and `tlmgr install` `packages`.

    With ``backend="auto"`` (default) apt is used when available, else TinyTeX. Either
    way the requested packages are installed so a bare `pdflatex` can compile Deltares
    documents; `build_pdf` additionally installs anything still missing on demand.

    Args:
        install_packages: When True (default), install the package set (apt: the
            `texlive-*` list; tinytex: `tlmgr install packages`). When False, only the
            engine is provisioned.
        packages: tlmgr packages/collections for the **tinytex** backend. Defaults to
            :data:`REQUIRED_TLMGR_PACKAGES`. Ignored by the apt backend, which uses
            :data:`APT_TEXLIVE_PACKAGES`.
        backend: ``"auto"`` (default), ``"apt"``, or ``"tinytex"``.

    Returns:
        True if pdflatex is accessible after the call, False otherwise.

    Raises:
        urllib.error.URLError: If the TinyTeX installer cannot be downloaded.
        subprocess.CalledProcessError: If the TinyTeX installer script fails.

    Examples:
        - Guard a PDF build on pdflatex being available:
            ```python
            >>> from ddocs.latex.pdflatex_utils import check_pdflatex_installed
            >>> if check_pdflatex_installed():  # doctest: +SKIP
            ...     print("building pdf")
            building pdf

            ```

    See Also:
        install_texlive_apt: The apt backend.
        sanity_check: The PATH-only probe this builds on.
        check_pdflatex_cli: Thin wrapper mapping the result to an exit code.
    """
    installed = sanity_check("pdflatex")
    if not installed:
        if backend == "auto":
            use_apt = platform.system() == "Linux" and shutil.which("apt-get") is not None
        else:
            use_apt = backend == "apt"

        if use_apt:
            apt_packages = APT_TEXLIVE_PACKAGES if install_packages else ("texlive-latex-base",)
            install_texlive_apt(apt_packages)
            installed = sanity_check("pdflatex")
            if installed:
                print("pdflatex is now accessible!")

        if not installed and backend != "apt":
            bin_dir = find_tex_bin_dir()
            if bin_dir is None:
                _install_tinytex()
                bin_dir = find_tex_bin_dir()

            if bin_dir:
                _prepend_to_path(bin_dir)
                if install_packages:
                    install_tlmgr_packages(packages)
                installed = sanity_check("pdflatex")
                if installed:
                    print("pdflatex is now accessible!")

        if not installed:
            print("Warning: pdflatex could not be made available from the command line.")
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


def pdflatex_check_cli(args: argparse.Namespace | None = None) -> int:
    """CLI handler for `ddocs pdflatex check`: report whether pdflatex is callable.

    This only probes `PATH` (via :func:`sanity_check`); it never downloads or installs
    anything. Use `ddocs pdflatex download` to install it.

    Args:
        args: Parsed CLI arguments from argparse. Unused; accepted for a uniform handler
            signature. Defaults to None.

    Returns:
        0 if `pdflatex` is already callable, 1 otherwise.

    Examples:
        - Probe for pdflatex and use the result as an exit code:
            ```python
            >>> from ddocs.latex.pdflatex_utils import pdflatex_check_cli
            >>> pdflatex_check_cli()  # doctest: +SKIP
            0

            ```

    See Also:
        pdflatex_download_cli: Installs pdflatex when it is missing.
    """
    return 0 if sanity_check("pdflatex") else 1


def pdflatex_download_cli(args: argparse.Namespace | None = None) -> int:
    """CLI handler for `ddocs pdflatex download`: install pdflatex and TeX packages.

    Ensures pdflatex is available (installing it via apt or TinyTeX if necessary) and
    maps the result to a process exit code suitable for :func:`sys.exit`.

    Honours optional argparse fields: ``no_packages`` (only ensure pdflatex, install no
    extra TeX packages), ``packages`` (a comma/space-separated string overriding the
    default :data:`REQUIRED_TLMGR_PACKAGES`), and ``backend`` (auto/apt/tinytex).

    Args:
        args: Parsed CLI arguments from argparse, or None to use the defaults.

    Returns:
        0 if pdflatex is accessible after the call, 1 otherwise.

    Examples:
        - Install pdflatex and use the result as a process exit code:
            ```python
            >>> from ddocs.latex.pdflatex_utils import pdflatex_download_cli
            >>> pdflatex_download_cli()  # doctest: +SKIP
            0

            ```

    See Also:
        check_pdflatex_installed: The underlying check-and-install routine.
    """
    install_packages = True
    packages: tuple[str, ...] | list[str] = REQUIRED_TLMGR_PACKAGES
    backend = "auto"

    if args is not None:
        if getattr(args, "no_packages", False):
            install_packages = False
        elif getattr(args, "packages", None):
            packages = [p for p in args.packages.replace(",", " ").split() if p]
        backend = getattr(args, "backend", None) or "auto"

    accessible = check_pdflatex_installed(
        install_packages=install_packages, packages=packages, backend=backend,
    )
    return 0 if accessible else 1


def check_pdflatex_cli(args: argparse.Namespace | None = None) -> int:
    """Deprecated alias for :func:`pdflatex_download_cli` (the old ``check-pdflatex``).

    Args:
        args: Parsed CLI arguments from argparse, or None to use the defaults.

    Returns:
        0 if pdflatex is accessible after the call, 1 otherwise.
    """
    return pdflatex_download_cli(args)
