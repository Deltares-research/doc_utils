"""End-to-end test: fetch the Deltares LaTeX templates and build a PDF from them.

This test exercises the full pipeline:

1. ``clone_repo_cli`` downloads the private Deltares template repo (needs a token in
   ``GITHUB_TOKEN`` / ``GH_TOKEN`` -- e.g. ``LATEX_REPO_TOKEN`` in ``.env`` bridged by
   conftest -- or an SSH key with access).
2. A ``test.tex`` is written that uses the ``deltares_report`` document class.
3. ``ddocs.pdflatex_utils.build_pdf`` compiles it (installing TinyTeX + missing TeX
   packages if pdflatex is not already available).
"""
import pytest

from ddocs.pdflatex_utils import build_pdf
from ddocs.templates.repo_cloner import clone_repo_cli

TEST_DOCUMENT = (
    "\\documentclass[a4paper]{deltares_report}\n"
    "\\begin{document}\n"
    "Hello Deltares. This PDF was produced by an end-to-end test.\n"
    "\\end{document}\n"
)


@pytest.mark.e2e
def test_build_pdf_from_deltares_template(tmp_path):
    """Test the templates can be fetched and compiled into a PDF.

    Test scenario:
        Clone the templates, drop a ``test.tex`` that uses ``deltares_report`` next to
        them (so the class and ``pictures/`` assets resolve), then build it with
        ``build_pdf`` and expect a non-empty ``test.pdf``.
    """
    templates = tmp_path / "templates"
    assert clone_repo_cli(templates) == 0, "template clone should return 0"

    tex_file = templates / "test.tex"
    tex_file.write_text(TEST_DOCUMENT, encoding="utf-8")

    pdf_path = build_pdf(tex_file)

    assert pdf_path.exists(), f"expected a PDF at {pdf_path}"
    assert pdf_path.stat().st_size > 0, "the produced PDF should not be empty"
