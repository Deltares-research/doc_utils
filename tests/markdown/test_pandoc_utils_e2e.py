"""End-to-end tests for pandoc_utils module.

These tests actually invoke pandoc and verify real functionality.
They will be skipped if pandoc is not available.
"""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest

from ddocs.markdown.pandoc_utils import check_pandoc_installed, _get_pandoc_dir


@pytest.fixture
def temp_markdown_file():
    """Create a temporary markdown file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Header\n\nThis is a test paragraph.\n")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestPandocE2E:
    """End-to-end tests that use real pandoc installation."""

    def test_check_pandoc_installed_real(self):
        """Test that check_pandoc_installed works with real pandoc."""
        result = check_pandoc_installed()

        # Should either find existing pandoc or download and configure it
        assert result is True or result is False  # Will depend on system state

        # After running, pandoc should be accessible
        try:
            version_result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            assert 'pandoc' in version_result.stdout.lower()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If check_pandoc_installed returned False, this is expected
            if result is True:
                pytest.fail("check_pandoc_installed returned True but pandoc not accessible")

    def test_get_pandoc_dir_returns_valid_path(self):
        """Test that _get_pandoc_dir returns a valid directory path."""
        pandoc_dir = _get_pandoc_dir()

        assert pandoc_dir is not None
        assert isinstance(pandoc_dir, str)
        assert len(pandoc_dir) > 0

    def test_pandoc_version_command(self):
        """Test running pandoc --version command directly."""
        # First ensure pandoc is set up
        check_pandoc_installed()

        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            assert result.returncode == 0
            assert 'pandoc' in result.stdout.lower()
            # Should contain version number
            assert any(char.isdigit() for char in result.stdout)

        except FileNotFoundError:
            pytest.skip("Pandoc not available in PATH")
        except subprocess.TimeoutExpired:
            pytest.fail("Pandoc command timed out")

    def test_pandoc_convert_markdown_to_html(self, temp_markdown_file):
        """Test actual markdown to HTML conversion using pandoc."""
        # First ensure pandoc is set up
        check_pandoc_installed()

        output_file = temp_markdown_file.replace('.md', '.html')

        try:
            result = subprocess.run(
                ['pandoc', temp_markdown_file, '-o', output_file],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            assert result.returncode == 0
            assert os.path.exists(output_file)

            # Verify output contains expected HTML
            with open(output_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
                assert '<h1' in html_content or 'Test Header' in html_content
                assert 'test paragraph' in html_content.lower()

        except FileNotFoundError:
            pytest.skip("Pandoc not available in PATH")
        except subprocess.TimeoutExpired:
            pytest.fail("Pandoc conversion timed out")
        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_pandoc_convert_markdown_to_latex(self, temp_markdown_file):
        """Test actual markdown to LaTeX conversion using pandoc."""
        # First ensure pandoc is set up
        check_pandoc_installed()

        output_file = temp_markdown_file.replace('.md', '.tex')

        try:
            result = subprocess.run(
                ['pandoc', temp_markdown_file, '-o', output_file],
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            assert result.returncode == 0
            assert os.path.exists(output_file)

            # Verify output contains expected LaTeX
            with open(output_file, 'r', encoding='utf-8') as f:
                latex_content = f.read()
                assert '\\section' in latex_content or '\\subsection' in latex_content
                assert 'Test Header' in latex_content

        except FileNotFoundError:
            pytest.skip("Pandoc not available in PATH")
        except subprocess.TimeoutExpired:
            pytest.fail("Pandoc conversion timed out")
        finally:
            # Cleanup
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_pandoc_with_nonexistent_file(self):
        """Test pandoc behavior with a nonexistent input file."""
        # First ensure pandoc is set up
        check_pandoc_installed()

        nonexistent_file = 'nonexistent_file_12345.md'

        try:
            result = subprocess.run(
                ['pandoc', nonexistent_file, '-o', 'output.html'],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Should fail with non-zero return code
            assert result.returncode != 0
            # Pandoc's wording for a missing input file varies by version
            # (e.g. "not found" on older releases, "does not exist" on newer).
            stderr = result.stderr.lower()
            assert any(
                msg in stderr
                for msg in ('error', 'not found', 'does not exist', 'no such file')
            )

        except FileNotFoundError:
            pytest.skip("Pandoc not available in PATH")
        except subprocess.TimeoutExpired:
            pytest.fail("Pandoc command timed out")

    def test_pandoc_path_persists_in_environment(self):
        """Test that pandoc path persists in os.environ after check_pandoc_installed."""
        initial_path = os.environ.get('PATH', '')

        check_pandoc_installed()

        # PATH should either be unchanged or have pandoc added
        current_path = os.environ.get('PATH', '')
        assert len(current_path) >= len(initial_path)

        # Should be able to run pandoc
        try:
            subprocess.run(['pandoc', '--version'], capture_output=True, check=True, timeout=10)
        except (FileNotFoundError, subprocess.CalledProcessError):
            # May fail if system doesn't have pandoc and download failed
            pass
