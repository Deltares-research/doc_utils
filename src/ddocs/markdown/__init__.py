"""Convert Markdown documentation to LaTeX (Pandoc + Deltares post-processing)."""

from ddocs.markdown.markdown import (
    convert_all_markdown_files,
    convert_markdown_to_latex,
    data_dir,
    fix_table_column_widths,
    mark_down_to_latex_cli,
    replace_utf8_tree_chars,
    wrap_long_words_in_tables,
)
from ddocs.markdown.pandoc_utils import (
    check_pandoc_cli,
    check_pandoc_installed,
    sanity_check,
)

__all__ = [
    "check_pandoc_cli",
    "check_pandoc_installed",
    "sanity_check",
    "convert_all_markdown_files",
    "convert_markdown_to_latex",
    "data_dir",
    "fix_table_column_widths",
    "mark_down_to_latex_cli",
    "replace_utf8_tree_chars",
    "wrap_long_words_in_tables",
]
