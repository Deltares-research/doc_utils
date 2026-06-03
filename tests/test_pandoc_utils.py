import os
import argparse
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from ddocs.pandoc_utils import (
    check_pandoc_installed,
    check_pandoc_cli,
    sanity_check,
    _get_pandoc_dir,
)


class TestCheckPandocInstalled:
    """Tests for check_pandoc_installed function."""

    @pytest.mark.mock
    def test_pandoc_already_installed(self, capsys):
        """Test when pandoc is already available in PATH."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='pandoc 3.1.8\nCompiled with...',
                returncode=0
            )

            result = check_pandoc_installed()

            assert result is True
            mock_run.assert_called_once()
            captured = capsys.readouterr()
            assert "Found Pandoc:" in captured.out

    @pytest.mark.mock
    def test_pandoc_not_on_path_uses_bundled_and_adds_to_path(self, capsys):
        """Test the bundled pandoc is exposed on PATH when not already callable.

        Test scenario:
            pandoc is missing first, its (bundled) directory is located and added to
            PATH, and the re-check then succeeds. No download occurs.
        """
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir, \
             patch('os.path.exists') as mock_exists:

            # First call fails (not found), second succeeds (after PATH is updated).
            mock_run.side_effect = [
                FileNotFoundError(),
                MagicMock(stdout='pandoc 3.1.8', returncode=0)
            ]
            mock_get_dir.return_value = '/path/to/pandoc'
            mock_exists.return_value = True

            result = check_pandoc_installed()

            assert result is True
            captured = capsys.readouterr()
            assert "Added pandoc to PATH:" in captured.out
            assert "Pandoc is now accessible!" in captured.out

    @pytest.mark.mock
    def test_bundled_pandoc_not_accessible(self, capsys):
        """Test a warning + False when the bundled binary still is not callable."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir, \
             patch('os.path.exists') as mock_exists:

            # Both probes fail even after the PATH update.
            mock_run.side_effect = [
                FileNotFoundError(),
                FileNotFoundError()
            ]
            mock_get_dir.return_value = '/path/to/pandoc'
            mock_exists.return_value = True

            result = check_pandoc_installed()

            assert result is False
            captured = capsys.readouterr()
            assert "Warning: bundled Pandoc could not be located" in captured.out

    @pytest.mark.mock
    def test_pandoc_dir_not_found(self):
        """Test False is returned when the pandoc directory cannot be determined."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir:

            mock_run.side_effect = FileNotFoundError()
            mock_get_dir.return_value = None

            assert check_pandoc_installed() is False

    @pytest.mark.mock
    def test_pandoc_dir_does_not_exist(self):
        """Test False is returned when the located pandoc directory does not exist."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir, \
             patch('os.path.exists') as mock_exists:

            mock_run.side_effect = FileNotFoundError()
            mock_get_dir.return_value = '/nonexistent/path'
            mock_exists.return_value = False

            assert check_pandoc_installed() is False

    @pytest.mark.mock
    def test_pandoc_dir_already_on_path_not_readded(self, capsys):
        """Test that PATH is not modified when the dir is already present.

        Test scenario:
            Pandoc is missing and its (bundled) directory already appears on PATH;
            expect success without re-adding (no "Added pandoc to PATH").
        """
        pandoc_dir = os.path.join("already", "on", "path")
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils._get_pandoc_dir', return_value=pandoc_dir), \
             patch('os.path.exists', return_value=True), \
             patch.dict('os.environ', {'PATH': pandoc_dir}, clear=False):

            mock_run.side_effect = [
                FileNotFoundError(),
                MagicMock(stdout='pandoc 3.1.8', returncode=0)
            ]

            result = check_pandoc_installed()

            assert result is True, f"Expected True when dir already on PATH, got {result}"
            captured = capsys.readouterr()
            assert "Added pandoc to PATH" not in captured.out, (
                f"PATH should not be re-added, got: {captured.out!r}"
            )


class TestSanityCheck:
    """Tests for sanity_check function."""

    @pytest.mark.mock
    def test_returns_true_and_prints_version(self, capsys):
        """Test sanity_check returns True and prints the detected version.

        Test scenario:
            subprocess.run succeeds with a version banner; expect True and a
            "Found Pandoc: <version>" line on stdout.
        """
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='pandoc 3.1.8\nCompiled with...',
                returncode=0
            )

            result = sanity_check()

            assert result is True, f"Expected True when pandoc runs, got {result}"
            captured = capsys.readouterr()
            assert "Found Pandoc: 3.1.8" in captured.out, (
                f"Version banner not printed, got: {captured.out!r}"
            )

    @pytest.mark.mock
    @pytest.mark.parametrize(
        "error",
        [
            FileNotFoundError(),
            subprocess.CalledProcessError(returncode=1, cmd=['pandoc', '--version']),
        ],
    )
    def test_returns_false_when_missing_or_fails(self, error):
        """Test sanity_check returns False when pandoc is absent or errors.

        Args:
            error: Exception raised by subprocess.run to simulate the failure.

        Test scenario:
            FileNotFoundError (pandoc not installed) and CalledProcessError
            (non-zero exit) must both yield False.
        """
        with patch('subprocess.run', side_effect=error):
            result = sanity_check()

        assert result is False, (
            f"Expected False on {type(error).__name__}, got {result}"
        )


class TestCheckPandocCli:
    """Tests for check_pandoc_cli function."""

    @pytest.mark.mock
    def test_returns_zero_when_available(self):
        """Test check_pandoc_cli returns 0 when pandoc is accessible.

        Test scenario:
            check_pandoc_installed reports True; expect exit code 0.
        """
        with patch('ddocs.pandoc_utils.check_pandoc_installed', return_value=True):
            result = check_pandoc_cli()

        assert result == 0, f"Expected exit code 0 when available, got {result}"

    @pytest.mark.mock
    def test_returns_one_when_unavailable(self):
        """Test check_pandoc_cli returns 1 when pandoc cannot be provided.

        Test scenario:
            check_pandoc_installed reports False; expect exit code 1.
        """
        with patch('ddocs.pandoc_utils.check_pandoc_installed', return_value=False):
            result = check_pandoc_cli()

        assert result == 1, f"Expected exit code 1 when unavailable, got {result}"

    @pytest.mark.mock
    def test_accepts_and_ignores_args_namespace(self):
        """Test check_pandoc_cli accepts an argparse namespace and ignores it.

        Test scenario:
            Passing a populated Namespace must not change the 0/1 mapping.
        """
        namespace = argparse.Namespace(command="check-pandoc")
        with patch('ddocs.pandoc_utils.check_pandoc_installed', return_value=True):
            result = check_pandoc_cli(namespace)

        assert result == 0, f"Expected exit code 0 with args namespace, got {result}"


class TestGetPandocDir:
    """Tests for _get_pandoc_dir function."""

    @pytest.mark.mock
    def test_get_pandoc_dir_from_pypandoc(self):
        """Test getting pandoc directory from pypandoc.get_pandoc_path()."""
        with patch('pypandoc.get_pandoc_path') as mock_get_path:
            mock_get_path.return_value = '/usr/local/bin/pandoc'

            result = _get_pandoc_dir()

            assert result == '/usr/local/bin'

    @pytest.mark.mock
    def test_get_pandoc_dir_fallback_windows(self):
        """Test fallback to Windows default location."""
        with patch('pypandoc.get_pandoc_path') as mock_get_path, \
             patch('sys.platform', 'win32'), \
             patch('os.path.expanduser') as mock_expanduser:

            mock_get_path.side_effect = Exception("Not found")
            mock_expanduser.return_value = 'C:\\Users\\TestUser'

            result = _get_pandoc_dir()

            assert 'AppData\\Local\\Pandoc' in result

    @pytest.mark.mock
    def test_get_pandoc_dir_resolves_bare_name_via_which(self):
        """Test resolving a bare 'pandoc' name to its directory via PATH.

        Test scenario:
            get_pandoc_path() returns a bare name (no directory), so the
            absolute location is resolved with shutil.which and its dirname
            is returned.
        """
        resolved = os.path.join('/opt', 'pandoc', 'pandoc')
        with patch('pypandoc.get_pandoc_path', return_value='pandoc'), \
             patch('shutil.which', return_value=resolved):

            result = _get_pandoc_dir()

            expected = os.path.dirname(resolved)
            assert result == expected, f"Expected {expected}, got {result}"

    @pytest.mark.mock
    def test_get_pandoc_dir_bare_name_unresolved_falls_back(self):
        """Test fallback when a bare name cannot be resolved on PATH.

        Test scenario:
            get_pandoc_path() returns a bare name and shutil.which finds
            nothing, so the platform default (Linux) is used.
        """
        with patch('pypandoc.get_pandoc_path', return_value='pandoc'), \
             patch('shutil.which', return_value=None), \
             patch('sys.platform', 'linux'), \
             patch('os.path.expanduser', return_value='/home/testuser'):

            result = _get_pandoc_dir()

            assert os.path.join('.local', 'bin') in result, (
                f"Expected a '.local/bin' fallback, got {result}"
            )

    @pytest.mark.mock
    def test_get_pandoc_dir_fallback_linux(self):
        """Test fallback to the Linux/Mac default location.

        Test scenario:
            get_pandoc_path() raises on a non-Windows platform, so the
            '~/.local/bin' default is returned.
        """
        with patch('pypandoc.get_pandoc_path', side_effect=Exception("Not found")), \
             patch('sys.platform', 'linux'), \
             patch('os.path.expanduser', return_value='/home/testuser'):

            result = _get_pandoc_dir()

            assert os.path.join('.local', 'bin') in result, (
                f"Expected a '.local/bin' fallback, got {result}"
            )
