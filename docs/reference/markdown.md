# `ddocs.markdown`

Core Markdown-to-LaTeX conversion logic plus the Deltares-specific
post-processing (UTF-8 tree-character replacement, table column-width fixes, and
long-word wrapping in tables). Also re-exports the Pandoc helpers from
[`ddocs.markdown.pandoc_utils`](pandoc_utils.md). The `clean` command lives in
[`ddocs.latex.clean`](clean.md).

::: ddocs.markdown
    options:
      show_root_heading: true
      show_source: true
