"""End-to-end tests for the get-tex-template CLI command (repo_cloner).

These tests invoke the actual `ddocs` CLI. The help/argument tests run anywhere;
the full clone test hits the private Deltares/LatexInstallation repo, so it needs
valid credentials (a token in ``GITHUB_TOKEN``/``GH_TOKEN`` -- e.g. ``LATEX_REPO_TOKEN``
in ``.env`` bridged by conftest -- or an SSH key with access) and will FAIL without them.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE_SUFFIXES = {".sty", ".cls", ".bst"}


def run_ddocs_command(*args):
    """Run the ddocs CLI in a subprocess and capture the result.

    Args:
        *args: CLI arguments passed after ``ddocs`` (e.g. ``"get-tex-template"``).

    Returns:
        The completed process (``subprocess.CompletedProcess``) with captured
        stdout/stderr.
    """
    cmd = [sys.executable, "-m", "ddocs.cli", *args]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=REPO_ROOT)


class TestGetTexTemplateE2E:
    """End-to-end tests for the `ddocs get-tex-template` command."""

    @pytest.mark.e2e
    def test_help_lists_output_dir_option(self):
        """Test the command's --help describes the output-dir option.

        Test scenario:
            ``get-tex-template --help`` exits 0 and documents ``--output-dir``.
            Needs no network, so it always runs.
        """
        result = run_ddocs_command("get-tex-template", "--help")
        assert result.returncode == 0, f"help should exit 0, got {result.returncode}: {result.stderr}"
        assert "--output-dir" in result.stdout, "help should mention --output-dir"
        assert "Output directory for the template files" in result.stdout, "help should describe --output-dir"

    @pytest.mark.e2e
    def test_missing_required_output_dir_errors(self):
        """Test omitting the required --output-dir fails with a non-zero exit code.

        Test scenario:
            ``get-tex-template`` with no args is rejected by argparse (exit 2),
            mentioning the missing option. Needs no network.
        """
        result = run_ddocs_command("get-tex-template")
        assert result.returncode != 0, "missing --output-dir should fail"
        assert "output-dir" in result.stderr.lower(), f"error should mention output-dir, got: {result.stderr}"

    @pytest.mark.e2e
    def test_get_tex_template_copies_templates(self, tmp_path):
        """Test the full command clones the repo and copies template files.

        Test scenario:
            Runs ``get-tex-template --output-dir <tmp>`` end-to-end; expects exit 0
            and at least one LaTeX template file (.sty/.cls/.bst) in the output dir.
        """
        out_dir = tmp_path / "templates"
        result = run_ddocs_command("get-tex-template", "--output-dir", str(out_dir))

        assert result.returncode == 0, f"command failed ({result.returncode}): {result.stderr}"
        assert out_dir.is_dir(), "output directory should have been created"

        copied = list(out_dir.rglob("*"))
        assert copied, f"output directory should contain copied files, got: {copied}"

        template_files = [p for p in copied if p.suffix in TEMPLATE_SUFFIXES]
        assert template_files, f"expected at least one {TEMPLATE_SUFFIXES} file, got: {[p.name for p in copied]}"
