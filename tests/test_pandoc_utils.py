from unittest.mock import patch, MagicMock
import pytest
from tests.utils import is_linux
from ddocs.pandoc_utils import check_pandoc_installed, _get_pandoc_dir


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
    def test_pandoc_not_found_downloads_and_adds_to_path(self, capsys):
        """Test when pandoc is not found and needs to be downloaded."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils.download_pandoc') as mock_download, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir, \
             patch('os.path.exists') as mock_exists:

            # First call fails (not found), second call succeeds (after download)
            mock_run.side_effect = [
                FileNotFoundError(),
                MagicMock(stdout='pandoc 3.1.8', returncode=0)
            ]
            mock_get_dir.return_value = '/path/to/pandoc'
            mock_exists.return_value = True

            result = check_pandoc_installed()

            assert result is True
            mock_download.assert_called_once()
            captured = capsys.readouterr()
            assert "Pandoc not found. Downloading..." in captured.out
            assert "Added pandoc to PATH:" in captured.out
            assert "Pandoc is now accessible!" in captured.out

    @pytest.mark.mock
    def test_pandoc_download_fails_verification(self, capsys):
        """Test when pandoc downloads but still not accessible."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils.download_pandoc') as mock_download, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir, \
             patch('os.path.exists') as mock_exists:

            # Both calls fail
            mock_run.side_effect = [
                FileNotFoundError(),
                FileNotFoundError()
            ]
            mock_get_dir.return_value = '/path/to/pandoc'
            mock_exists.return_value = True

            result = check_pandoc_installed()

            assert result is False
            mock_download.assert_called_once()
            captured = capsys.readouterr()
            assert "Warning: Pandoc downloaded but not accessible" in captured.out

    @pytest.mark.mock
    def test_pandoc_dir_not_found(self):
        """Test when pandoc directory cannot be determined."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils.download_pandoc') as mock_download, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir:

            mock_run.side_effect = FileNotFoundError()
            mock_get_dir.return_value = None

            result = check_pandoc_installed()

            assert result is False
            mock_download.assert_called_once()

    @pytest.mark.mock
    def test_pandoc_dir_does_not_exist(self):
        """Test when pandoc directory path doesn't exist."""
        with patch('subprocess.run') as mock_run, \
             patch('ddocs.pandoc_utils.download_pandoc') as mock_download, \
             patch('ddocs.pandoc_utils._get_pandoc_dir') as mock_get_dir, \
             patch('os.path.exists') as mock_exists:

            mock_run.side_effect = FileNotFoundError()
            mock_get_dir.return_value = '/nonexistent/path'
            mock_exists.return_value = False

            result = check_pandoc_installed()

            assert result is False
            mock_download.assert_called_once()


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

    # @pytest.mark.mock
    # @pytest.mark.skipif(not is_linux(), reason="Only applicable to Linux")
    # def test_get_pandoc_dir_fallback_linux(self):
    #     """Test fallback to Linux/Mac default location."""
    #     with patch('pypandoc.get_pandoc_path') as mock_get_path, \
    #          patch('sys.platform', 'linux'), \
    #          patch('os.path.expanduser') as mock_expanduser:
    #
    #         mock_get_path.side_effect = Exception("Not found")
    #         mock_expanduser.return_value = '/home/testuser'
    #
    #         result = _get_pandoc_dir()
    #
    #         assert '.local/bin' in result
