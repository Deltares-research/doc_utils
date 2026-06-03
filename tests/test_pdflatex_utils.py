"""Unit tests for ddocs.pdflatex_utils (TinyTeX backend), fully mocked."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ddocs import pdflatex_utils
from ddocs.pdflatex_utils import (
    check_pdflatex_cli,
    check_pdflatex_installed,
    find_missing_packages,
    find_tex_bin_dir,
    install_missing_packages,
    install_tlmgr_packages,
    sanity_check,
)


class TestSanityCheck:
    """Tests for sanity_check."""

    @pytest.mark.unit
    def test_returns_true_when_command_runs(self, capsys):
        """Test sanity_check returns True and prints the version when the tool runs.

        Test scenario:
            subprocess.run succeeds -> True and a 'Found' line is printed.
        """
        with patch("subprocess.run", return_value=MagicMock(stdout="pdfTeX 3.14\n...")):
            assert sanity_check("pdflatex") is True, "should detect a working pdflatex"
        assert "Found pdflatex" in capsys.readouterr().out, "should print the detected version"

    @pytest.mark.unit
    @pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.CalledProcessError(1, "pdflatex")])
    def test_returns_false_when_missing_or_fails(self, error):
        """Test sanity_check returns False when the command is missing or errors.

        Args:
            error: The exception subprocess.run raises.

        Test scenario:
            A missing binary (FileNotFoundError) or a non-zero exit both yield False.
        """
        with patch("subprocess.run", side_effect=error):
            assert sanity_check("pdflatex") is False, f"should be False on {type(error).__name__}"


class TestFindMissingPackages:
    """Tests for find_missing_packages."""

    @pytest.mark.unit
    def test_extracts_single_package(self):
        """Test a single missing .sty yields its stem."""
        assert find_missing_packages("! LaTeX Error: File `tikz.sty' not found.") == ["tikz"]

    @pytest.mark.unit
    def test_dedupes_and_preserves_order(self):
        """Test repeated/various missing files are de-duplicated in first-seen order."""
        log = "File `a.sty' not found\nFile `b.cls' not found\nFile `a.sty' not found"
        assert find_missing_packages(log) == ["a", "b"], "should keep order and drop duplicates"

    @pytest.mark.unit
    def test_returns_empty_when_nothing_missing(self):
        """Test a clean log yields no packages."""
        assert find_missing_packages("This is pdfTeX, output written to out.pdf") == []


class TestFindTexBinDir:
    """Tests for find_tex_bin_dir."""

    @pytest.mark.unit
    def test_returns_dir_containing_pdflatex(self):
        """Test the bin dir holding pdflatex is returned.

        Test scenario:
            glob lists one candidate that contains the pdflatex executable.
        """
        with patch("ddocs.pdflatex_utils.platform.system", return_value="Linux"), \
             patch("ddocs.pdflatex_utils.glob.glob", return_value=["/root/.TinyTeX/bin/x86_64-linux"]), \
             patch("os.path.exists", return_value=True):
            assert find_tex_bin_dir() == "/root/.TinyTeX/bin/x86_64-linux", "should return the bin dir"

    @pytest.mark.unit
    def test_returns_none_when_not_installed(self):
        """Test None is returned when no TinyTeX bin dir exists."""
        with patch("ddocs.pdflatex_utils.platform.system", return_value="Linux"), \
             patch("ddocs.pdflatex_utils.glob.glob", return_value=[]):
            assert find_tex_bin_dir() is None, "should be None when nothing matches"


class TestInstallTlmgrPackages:
    """Tests for install_tlmgr_packages."""

    @pytest.mark.unit
    def test_invokes_tlmgr_install_with_packages(self):
        """Test tlmgr install is called with the requested packages.

        Test scenario:
            A successful tlmgr run returns True and passes the package list through.
        """
        with patch("subprocess.run") as mock_run:
            assert install_tlmgr_packages(["tikz", "biber"]) is True, "should report success"
        assert mock_run.call_args.args[0] == ["tlmgr", "install", "tikz", "biber"], "wrong tlmgr command"

    @pytest.mark.unit
    def test_returns_false_when_tlmgr_missing(self):
        """Test a missing tlmgr yields False rather than raising."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            assert install_tlmgr_packages(["tikz"]) is False, "should be False when tlmgr is absent"


class TestInstallMissingPackages:
    """Tests for install_missing_packages."""

    @pytest.mark.unit
    def test_installs_parsed_packages(self):
        """Test parsed missing packages are forwarded to install_tlmgr_packages."""
        with patch("ddocs.pdflatex_utils.install_tlmgr_packages", return_value=True) as mock_install:
            result = install_missing_packages("File `tikz.sty' not found")
        assert result == ["tikz"], "should return the parsed package names"
        mock_install.assert_called_once_with(["tikz"])

    @pytest.mark.unit
    def test_noop_when_nothing_missing(self):
        """Test nothing is installed when the log reports no missing files."""
        with patch("ddocs.pdflatex_utils.install_tlmgr_packages") as mock_install:
            assert install_missing_packages("all good") == [], "should return empty list"
        mock_install.assert_not_called()


class TestCheckPdflatexInstalled:
    """Tests for check_pdflatex_installed."""

    @pytest.mark.unit
    def test_returns_true_when_already_available(self):
        """Test an already-present pdflatex short-circuits without installing.

        Test scenario:
            sanity_check True -> no TinyTeX install attempted.
        """
        with patch("ddocs.pdflatex_utils.sanity_check", return_value=True), \
             patch("ddocs.pdflatex_utils._install_tinytex") as mock_install, \
             patch("ddocs.pdflatex_utils.find_tex_bin_dir") as mock_find:
            assert check_pdflatex_installed() is True, "should report available"
        mock_install.assert_not_called()
        mock_find.assert_not_called()

    @pytest.mark.unit
    def test_uses_existing_tinytex_without_downloading(self):
        """Test an existing TinyTeX is reused: PATH updated, packages installed.

        Test scenario:
            pdflatex missing, find_tex_bin_dir returns a dir -> no installer download.
        """
        with patch("ddocs.pdflatex_utils.sanity_check", side_effect=[False, True]), \
             patch("ddocs.pdflatex_utils.find_tex_bin_dir", return_value="/root/.TinyTeX/bin/x86_64-linux"), \
             patch("ddocs.pdflatex_utils._install_tinytex") as mock_install, \
             patch("ddocs.pdflatex_utils._prepend_to_path") as mock_path, \
             patch("ddocs.pdflatex_utils.install_tlmgr_packages", return_value=True) as mock_pkgs:
            assert check_pdflatex_installed() is True, "should become available"
        mock_install.assert_not_called()
        mock_path.assert_called_once_with("/root/.TinyTeX/bin/x86_64-linux")
        mock_pkgs.assert_called_once()

    @pytest.mark.unit
    def test_downloads_tinytex_when_absent(self):
        """Test the installer runs when no TinyTeX is found, then succeeds.

        Test scenario:
            find_tex_bin_dir returns None first, then a dir after _install_tinytex.
        """
        with patch("ddocs.pdflatex_utils.sanity_check", side_effect=[False, True]), \
             patch("ddocs.pdflatex_utils.find_tex_bin_dir", side_effect=[None, "/bin/dir"]), \
             patch("ddocs.pdflatex_utils._install_tinytex") as mock_install, \
             patch("ddocs.pdflatex_utils._prepend_to_path"), \
             patch("ddocs.pdflatex_utils.install_tlmgr_packages", return_value=True):
            assert check_pdflatex_installed() is True, "should install then succeed"
        mock_install.assert_called_once()

    @pytest.mark.unit
    def test_returns_false_when_still_unavailable(self, capsys):
        """Test a warning + False when pdflatex is unreachable after install."""
        with patch("ddocs.pdflatex_utils.sanity_check", side_effect=[False, False]), \
             patch("ddocs.pdflatex_utils.find_tex_bin_dir", return_value="/bin/dir"), \
             patch("ddocs.pdflatex_utils._prepend_to_path"), \
             patch("ddocs.pdflatex_utils.install_tlmgr_packages", return_value=True):
            assert check_pdflatex_installed() is False, "should report failure"
        assert "not accessible" in capsys.readouterr().out, "should warn about inaccessibility"

    @pytest.mark.unit
    def test_skips_package_install_when_disabled(self):
        """Test install_packages=False skips tlmgr after locating TinyTeX."""
        with patch("ddocs.pdflatex_utils.sanity_check", side_effect=[False, True]), \
             patch("ddocs.pdflatex_utils.find_tex_bin_dir", return_value="/bin/dir"), \
             patch("ddocs.pdflatex_utils._prepend_to_path"), \
             patch("ddocs.pdflatex_utils.install_tlmgr_packages") as mock_pkgs:
            assert check_pdflatex_installed(install_packages=False) is True
        mock_pkgs.assert_not_called()


class TestInternals:
    """Tests for the platform/install helpers."""

    @pytest.mark.unit
    def test_prepend_to_path_is_idempotent(self, monkeypatch):
        """Test _prepend_to_path adds a dir once and not again.

        Test scenario:
            First call prepends; a second call with the same dir is a no-op.
        """
        monkeypatch.setenv("PATH", "/usr/bin")
        pdflatex_utils._prepend_to_path("/new/bin")
        assert pdflatex_utils.os.environ["PATH"].startswith("/new/bin"), "should prepend the dir"
        unchanged = pdflatex_utils.os.environ["PATH"]
        pdflatex_utils._prepend_to_path("/new/bin")
        assert pdflatex_utils.os.environ["PATH"] == unchanged, "should not add a duplicate entry"

    @pytest.mark.unit
    @pytest.mark.parametrize("system, needle", [("Windows", "TinyTeX"), ("Darwin", "Library"), ("Linux", ".TinyTeX")])
    def test_root_candidates_per_platform(self, system, needle, monkeypatch):
        """Test _tinytex_root_candidates returns platform-appropriate roots.

        Args:
            system: The platform.system() value to simulate.
            needle: A substring expected in the first candidate path.
        """
        monkeypatch.setenv("APPDATA", "/appdata")
        with patch("ddocs.pdflatex_utils.platform.system", return_value=system):
            candidates = pdflatex_utils._tinytex_root_candidates()
        assert any(needle in c for c in candidates), f"{system} roots should contain {needle}: {candidates}"

    @pytest.mark.unit
    def test_install_tinytex_unix_downloads_and_runs(self):
        """Test the unix installer is downloaded and executed with sh, then cleaned up."""
        tmp = MagicMock()
        tmp.__enter__.return_value.name = "/tmp/install.sh"
        with patch("ddocs.pdflatex_utils.platform.system", return_value="Linux"), \
             patch("ddocs.pdflatex_utils.tempfile.NamedTemporaryFile", return_value=tmp), \
             patch("ddocs.pdflatex_utils.urllib.request.urlretrieve") as mock_dl, \
             patch("ddocs.pdflatex_utils.subprocess.run") as mock_run, \
             patch("os.path.exists", return_value=True), \
             patch("os.unlink") as mock_unlink:
            pdflatex_utils._install_tinytex()
        mock_dl.assert_called_once()
        assert mock_run.call_args.args[0] == ["sh", "/tmp/install.sh"], "unix should run via sh"
        mock_unlink.assert_called_once_with("/tmp/install.sh")

    @pytest.mark.unit
    def test_install_tinytex_windows_uses_cmd(self):
        """Test the Windows installer is executed via cmd /c."""
        tmp = MagicMock()
        tmp.__enter__.return_value.name = "C:/tmp/install.bat"
        with patch("ddocs.pdflatex_utils.platform.system", return_value="Windows"), \
             patch("ddocs.pdflatex_utils.tempfile.NamedTemporaryFile", return_value=tmp), \
             patch("ddocs.pdflatex_utils.urllib.request.urlretrieve"), \
             patch("ddocs.pdflatex_utils.subprocess.run") as mock_run, \
             patch("os.path.exists", return_value=False), \
             patch("os.unlink"):
            pdflatex_utils._install_tinytex()
        assert mock_run.call_args.args[0] == ["cmd", "/c", "C:/tmp/install.bat"], "windows should run via cmd /c"


class TestBuildPdf:
    """Tests for build_pdf (compile loop), fully mocked."""

    @pytest.mark.unit
    def test_returns_pdf_path_on_success(self, tmp_path):
        """Test a successful compile returns the PDF path and runs a second pass.

        Test scenario:
            pdflatex returns 0 and the PDF exists -> path returned, two runs total.
        """
        tex = tmp_path / "doc.tex"
        tex.write_text("\\documentclass{article}\\begin{document}x\\end{document}", encoding="utf-8")
        pdf = tmp_path / "doc.pdf"

        def fake_run(cmd, **kwargs):
            pdf.write_bytes(b"%PDF-1.5\n")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("ddocs.pdflatex_utils.check_pdflatex_installed", return_value=True), \
             patch("ddocs.pdflatex_utils.subprocess.run", side_effect=fake_run) as mock_run:
            result = pdflatex_utils.build_pdf(tex)
        assert result == pdf, f"should return the pdf path, got {result}"
        assert mock_run.call_count == 2, "should run pdflatex twice (build + refs pass)"

    @pytest.mark.unit
    def test_installs_missing_packages_then_succeeds(self, tmp_path):
        """Test a first-pass failure triggers package install and a retry.

        Test scenario:
            Run 1 fails with a missing-package log -> install_missing_packages -> run 2
            succeeds and produces the PDF.
        """
        tex = tmp_path / "doc.tex"
        tex.write_text("x", encoding="utf-8")
        pdf = tmp_path / "doc.pdf"
        runs = {"n": 0}

        def fake_run(cmd, **kwargs):
            runs["n"] += 1
            if runs["n"] == 1:
                return MagicMock(returncode=1, stdout="! LaTeX Error: File `tikz.sty' not found.", stderr="")
            pdf.write_bytes(b"%PDF-1.5\n")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("ddocs.pdflatex_utils.check_pdflatex_installed", return_value=True), \
             patch("ddocs.pdflatex_utils.install_tlmgr_packages", return_value=True) as mock_pkgs, \
             patch("ddocs.pdflatex_utils.subprocess.run", side_effect=fake_run):
            result = pdflatex_utils.build_pdf(tex)
        assert result == pdf, "should return the pdf path after retrying"
        mock_pkgs.assert_called_once_with(["tikz"])

    @pytest.mark.unit
    def test_raises_when_pdflatex_unavailable(self, tmp_path):
        """Test a RuntimeError is raised when pdflatex cannot be made available."""
        tex = tmp_path / "doc.tex"
        tex.write_text("x", encoding="utf-8")
        with patch("ddocs.pdflatex_utils.check_pdflatex_installed", return_value=False):
            with pytest.raises(RuntimeError, match="pdflatex is not available"):
                pdflatex_utils.build_pdf(tex)

    @pytest.mark.unit
    def test_raises_when_no_pdf_and_nothing_to_install(self, tmp_path):
        """Test a RuntimeError when compilation fails with no installable packages.

        Test scenario:
            pdflatex fails and the log has no missing-file errors -> give up, raise.
        """
        tex = tmp_path / "doc.tex"
        tex.write_text("x", encoding="utf-8")
        with patch("ddocs.pdflatex_utils.check_pdflatex_installed", return_value=True), \
             patch("ddocs.pdflatex_utils.subprocess.run",
                   return_value=MagicMock(returncode=1, stdout="! Undefined control sequence", stderr="")):
            with pytest.raises(RuntimeError, match="did not produce"):
                pdflatex_utils.build_pdf(tex)


class TestCheckPdflatexCli:
    """Tests for check_pdflatex_cli."""

    @pytest.mark.unit
    @pytest.mark.parametrize("available, code", [(True, 0), (False, 1)])
    def test_maps_result_to_exit_code(self, available, code):
        """Test the CLI handler returns 0 when available and 1 otherwise.

        Args:
            available: What check_pdflatex_installed reports.
            code: The expected process exit code.
        """
        with patch("ddocs.pdflatex_utils.check_pdflatex_installed", return_value=available):
            assert check_pdflatex_cli() == code, f"expected exit {code}"
