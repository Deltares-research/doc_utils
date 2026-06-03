# `ddocs.pdflatex_utils`

Locate, verify, and install pdfLaTeX using **TinyTeX** as the backend. Confirms that
`pdflatex` (and `biber`) are callable, downloads and runs the root-free TinyTeX
installer when missing, prepends its `bin` directory to `PATH`, and installs the
`tlmgr` package collections that mirror the `texlive-*` packages. Also provides a
MiKTeX-style helper that installs packages reported missing in a LaTeX build log.

::: ddocs.pdflatex_utils
    options:
      show_root_heading: true
      show_source: true
