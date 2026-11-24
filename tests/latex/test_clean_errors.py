"""Error-path and helper tests for ``ddocs.latex.clean`` (invalid directories, OSError handling)."""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from ddocs.latex.clean import (
    _is_build_file,
    _remove_file,
    _remove_template_directory,
    clean_latex_build_files,
    clean_latex_cli,
)


class TestIsBuildFile:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("doc.aux", True),
            ("DOC.AUX", True),
            ("doc.synctex.gz", True),
            ("doc.mtc7", True),
            ("doc.mtc", True),
            ("doc.mtcx", False),
            ("doc.tex", False),
            ("doc.pdf", False),
        ],
    )
    def test_extension_matching(self, tmp_path, name, expected):
        """Test _is_build_file classifies regular files by extension, case-insensitively.

        Args:
            tmp_path: Pytest temporary directory.
            name: File name to create.
            expected: Whether it should be treated as a build artifact.
        """
        path = tmp_path / name
        path.write_text("x")

        assert _is_build_file(path) is expected, f"{name}: expected {expected}"

    @pytest.mark.unit
    def test_directory_with_artifact_suffix_is_not_a_build_file(self, tmp_path):
        """Test a directory named like an artifact (``x.aux``) is never selected for deletion."""
        directory = tmp_path / "x.aux"
        directory.mkdir()

        assert _is_build_file(directory) is False, "directories must not be treated as build files"


class TestRemoveHelpers:
    @pytest.mark.unit
    def test_remove_file_reports_oserror(self, tmp_path, capsys):
        """Test _remove_file returns 0 and warns when unlink raises OSError."""
        target = tmp_path / "doc.aux"
        target.write_text("x")

        with patch.object(Path, "unlink", side_effect=OSError("locked")):
            removed = _remove_file(target, tmp_path)

        assert removed == 0, f"expected 0 removed, got {removed}"
        assert "Could not remove" in capsys.readouterr().out, "a warning should be printed"
        assert target.exists(), "file should still exist"

    @pytest.mark.unit
    def test_remove_template_directory_reports_oserror(self, tmp_path, capsys):
        """Test _remove_template_directory returns 0 and warns when rmtree fails."""
        pictures = tmp_path / "pictures"
        pictures.mkdir()
        (pictures / "a.png").write_text("x")

        with patch("ddocs.latex.clean.shutil.rmtree", side_effect=OSError("locked")):
            removed = _remove_template_directory(pictures, tmp_path)

        assert removed == 0, f"expected 0 removed, got {removed}"
        assert "Could not remove" in capsys.readouterr().out, "a warning should be printed"

    @pytest.mark.unit
    def test_remove_template_directory_counts_nested_files(self, tmp_path):
        """Test _remove_template_directory returns the number of files that were inside."""
        pictures = tmp_path / "pictures"
        (pictures / "nested").mkdir(parents=True)
        (pictures / "a.png").write_text("x")
        (pictures / "nested" / "b.png").write_text("x")

        assert _remove_template_directory(pictures, tmp_path) == 2, "both nested files should be counted"
        assert not pictures.exists(), "directory should be gone"


class TestCleanLatexBuildFilesErrors:
    @pytest.mark.unit
    def test_missing_directory_returns_zero(self, tmp_path, capsys):
        """Test a non-existent directory prints an error and removes nothing."""
        assert clean_latex_build_files(tmp_path / "nope") == 0, "nothing should be removed"
        assert "Directory not found" in capsys.readouterr().out, "error message expected"

    @pytest.mark.unit
    def test_path_that_is_a_file_returns_zero(self, tmp_path, capsys):
        """Test a path pointing to a file prints an error and removes nothing."""
        file_path = tmp_path / "doc.aux"
        file_path.write_text("x")

        assert clean_latex_build_files(file_path) == 0, "nothing should be removed"
        assert "not a directory" in capsys.readouterr().out, "error message expected"
        assert file_path.exists(), "the file must be left alone"


class TestCleanLatexCliErrors:
    @pytest.mark.integration
    def test_missing_directory_returns_one(self, tmp_path, capsys):
        """Test the CLI exits with 1 when the directory does not exist."""
        args = argparse.Namespace(directory=tmp_path / "nope", recursive=False, templates=False)

        assert clean_latex_cli(args) == 1, "missing directory should give exit code 1"
        assert "Directory not found" in capsys.readouterr().out, "error message expected"

    @pytest.mark.integration
    def test_file_instead_of_directory_returns_one(self, tmp_path, capsys):
        """Test the CLI exits with 1 when the path is a file."""
        file_path = tmp_path / "doc.tex"
        file_path.write_text("x")
        args = argparse.Namespace(directory=file_path, recursive=False, templates=False)

        assert clean_latex_cli(args) == 1, "file path should give exit code 1"
        assert "not a directory" in capsys.readouterr().out, "error message expected"

    @pytest.mark.integration
    def test_nothing_to_clean_message(self, tmp_path, capsys):
        """Test the CLI reports when no build files are found and still exits with 0."""
        (tmp_path / "doc.tex").write_text("x")
        args = argparse.Namespace(directory=tmp_path, recursive=False, templates=False)

        assert clean_latex_cli(args) == 0, "clean should succeed"
        assert "No LaTeX build files found" in capsys.readouterr().out, "nothing-to-clean message expected"
