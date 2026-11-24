"""Tests for the extended artifact list and the ``--templates`` option of ``ddocs clean``."""

import argparse
from pathlib import Path

import pytest

from ddocs.cli import create_parser
from ddocs.latex.clean import clean_latex_build_files, clean_latex_cli

EXTRA_ARTIFACTS = [
    "doc.maf", "doc.mtc", "doc.mtc0", "doc.mtc12", "doc.nlo", "doc.nls", "doc.nlg",
    "doc.bcf", "doc.run.xml", "doc.glo", "doc.gls", "doc.glg", "doc.lol", "doc.loe", "doc.tdo",
]
TEMPLATE_FILES = [
    "deltares_report.cls", "deltares_footer.sty", "deltares_chicago_like.bst", "deltares_nomentbl.ist",
]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A document directory with sources, artifacts, downloaded templates and a pictures/ dir."""
    (tmp_path / "doc.tex").write_text("x")
    (tmp_path / "doc.pdf").write_text("x")
    (tmp_path / "version.tex").write_text("x")
    for name in EXTRA_ARTIFACTS + TEMPLATE_FILES:
        (tmp_path / name).write_text("x")
    (tmp_path / "pictures").mkdir()
    (tmp_path / "pictures" / "logo.pdf").write_text("x")
    (tmp_path / "pictures" / "nested").mkdir()
    (tmp_path / "pictures" / "nested" / "a.png").write_text("x")
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "intro.tex").write_text("x")
    (tmp_path / "chapters" / "intro.aux").write_text("x")
    return tmp_path


class TestExtendedArtifacts:
    @pytest.mark.unit
    def test_minitoc_and_nomencl_artifacts_are_removed(self, workspace):
        """Test that minitoc/nomencl/biblatex/glossary artifacts are cleaned, sources and pdf are kept.

        Test scenario:
            Non-recursive clean of a directory holding every newly supported artifact.
        """
        removed = clean_latex_build_files(workspace, pattern="*")

        assert removed == len(EXTRA_ARTIFACTS), f"expected {len(EXTRA_ARTIFACTS)} removed, got {removed}"
        for name in EXTRA_ARTIFACTS:
            assert not (workspace / name).exists(), f"{name} should have been removed"
        for kept in ["doc.tex", "doc.pdf", "version.tex", *TEMPLATE_FILES]:
            assert (workspace / kept).exists(), f"{kept} must not be removed without --templates"
        assert (workspace / "chapters" / "intro.aux").exists(), "non-recursive clean must skip subdirectories"

    @pytest.mark.unit
    def test_recursive_clean_reaches_subdirectories(self, workspace):
        """Test that the recursive clean also removes artifacts in subdirectories."""
        clean_latex_build_files(workspace)

        assert not (workspace / "chapters" / "intro.aux").exists(), "recursive clean should remove nested .aux"
        assert (workspace / "chapters" / "intro.tex").exists(), "sources must be kept"


class TestTemplatesOption:
    @pytest.mark.unit
    def test_templates_removed_when_requested(self, workspace):
        """Test that templates=True removes template files and the pictures/ directory."""
        removed = clean_latex_build_files(workspace, pattern="*", templates=True)

        assert removed == len(EXTRA_ARTIFACTS) + len(TEMPLATE_FILES) + 2, f"unexpected removed count: {removed}"
        for name in TEMPLATE_FILES:
            assert not (workspace / name).exists(), f"{name} should have been removed"
        assert not (workspace / "pictures").exists(), "pictures/ should have been removed"
        for kept in ["doc.tex", "doc.pdf", "version.tex"]:
            assert (workspace / kept).exists(), f"{kept} must never be removed"
        assert (workspace / "chapters" / "intro.tex").exists(), "user content must be kept"

    @pytest.mark.unit
    def test_only_deltares_prefixed_style_files_are_template_files(self, tmp_path):
        """Test that user-owned .cls/.sty/.bst/.ist files without the deltares_ prefix survive."""
        for name in ["mystyle.sty", "custom.cls", "refs.bst", "deltares_report.cls"]:
            (tmp_path / name).write_text("x")

        clean_latex_build_files(tmp_path, pattern="*", templates=True)

        assert (tmp_path / "mystyle.sty").exists(), "non-template .sty must be kept"
        assert (tmp_path / "custom.cls").exists(), "non-template .cls must be kept"
        assert (tmp_path / "refs.bst").exists(), "non-template .bst must be kept"
        assert not (tmp_path / "deltares_report.cls").exists(), "template .cls should be removed"

    @pytest.mark.unit
    def test_templates_without_pictures_dir_is_fine(self, tmp_path):
        """Test that a missing pictures/ directory is not an error."""
        (tmp_path / "deltares_report.cls").write_text("x")

        assert clean_latex_build_files(tmp_path, pattern="*", templates=True) == 1, "only the .cls is removed"

    @pytest.mark.unit
    def test_pictures_only_removed_directly_under_directory(self, tmp_path):
        """Test that a nested pictures/ directory is left alone even for a recursive clean."""
        nested = tmp_path / "sub" / "pictures"
        nested.mkdir(parents=True)
        (nested / "mine.png").write_text("x")

        clean_latex_build_files(tmp_path, templates=True)

        assert (nested / "mine.png").exists(), "nested pictures/ is not a downloaded template"

    @pytest.mark.integration
    def test_cli_templates_flag(self, workspace, capsys):
        """Test that clean_latex_cli forwards --templates and reports the summary."""
        args = argparse.Namespace(directory=workspace, recursive=False, templates=True)

        assert clean_latex_cli(args) == 0, "clean should succeed"
        assert not (workspace / "pictures").exists(), "pictures/ should be removed via the CLI"
        assert "Cleaned" in capsys.readouterr().out, "summary line should be printed"

    @pytest.mark.integration
    def test_cli_without_templates_attribute(self, workspace):
        """Test that a Namespace lacking ``templates`` (older callers) behaves as templates=False."""
        args = argparse.Namespace(directory=workspace, recursive=False)

        assert clean_latex_cli(args) == 0, "clean should succeed"
        assert (workspace / "pictures").exists(), "templates must be kept by default"

    @pytest.mark.unit
    def test_parser_defaults_and_flag(self):
        """Test that --templates is off by default and set by the flag."""
        parser = create_parser()

        assert parser.parse_args(["clean", "-d", "x"]).templates is False, "default must be opt-out"
        assert parser.parse_args(["clean", "-d", "x", "--templates"]).templates is True, "flag should enable it"
