"""LaTeX tooling for ddocs: provisioning pdfLaTeX (TinyTeX) and building PDFs."""

from ddocs.latex.clean import clean_latex_build_files, clean_latex_cli
from ddocs.latex.pdflatex_utils import (
    APT_TEXLIVE_PACKAGES,
    REQUIRED_TLMGR_PACKAGES,
    build_pdf,
    check_pdflatex_cli,
    check_pdflatex_installed,
    find_missing_packages,
    find_tex_bin_dir,
    install_missing_packages,
    install_texlive_apt,
    install_tlmgr_packages,
    pdflatex_check_cli,
    pdflatex_download_cli,
    sanity_check,
)

__all__ = [
    "APT_TEXLIVE_PACKAGES",
    "REQUIRED_TLMGR_PACKAGES",
    "build_pdf",
    "check_pdflatex_cli",
    "check_pdflatex_installed",
    "clean_latex_build_files",
    "clean_latex_cli",
    "find_missing_packages",
    "find_tex_bin_dir",
    "install_missing_packages",
    "install_texlive_apt",
    "install_tlmgr_packages",
    "pdflatex_check_cli",
    "pdflatex_download_cli",
    "sanity_check",
]
