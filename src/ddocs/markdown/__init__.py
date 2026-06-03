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

__all__ = [
    "convert_all_markdown_files",
    "convert_markdown_to_latex",
    "data_dir",
    "fix_table_column_widths",
    "mark_down_to_latex_cli",
    "replace_utf8_tree_chars",
    "wrap_long_words_in_tables",
]
