# API Reference

The `ddocs` package provides utilities for converting Markdown documentation to
LaTeX, retrieving Deltares LaTeX templates, and managing the Pandoc toolchain.
Its public command-line entry point is `ddocs` (see [`cli`](cli.md)).

## Modules

| Module | Responsibility |
| --- | --- |
| [`ddocs.cli`](cli.md) | Argparse-based command-line interface and subcommand dispatch. |
| [`ddocs.markdown`](markdown.md) | Markdown-to-LaTeX conversion, Deltares post-processing, and build-file cleanup. |
| [`ddocs.pandoc_utils`](pandoc_utils.md) | Locate, verify, and auto-install the Pandoc executable. |
| [`ddocs.latex.pdflatex_utils`](pdflatex_utils.md) | Locate, verify, and install pdfLaTeX via TinyTeX. |
| [`ddocs.templates.repo_cloner`](repo_cloner.md) | Clone the Deltares LaTeX template repository and copy files out of it. |

## Package

::: ddocs
    options:
      show_root_heading: true
      show_source: false
      members: false
