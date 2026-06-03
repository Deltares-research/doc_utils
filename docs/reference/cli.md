# `ddocs.cli`

Command-line interface for `ddocs`. Builds the argument parser, wires up the
`markdown-to-latex`, `get-tex-template`, `clean`, and `check-pandoc` subcommands,
and dispatches to their handlers. Installed as the `ddocs` console script.

::: ddocs.cli
    options:
      show_root_heading: true
      show_source: true
