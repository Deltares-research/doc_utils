# `ddocs.latex.pdflatex_utils`

Locate, verify, and install pdfLaTeX. Confirms that `pdflatex` (and `biber`) are
callable and, when missing, installs the root-free **TinyTeX** installer (the default on every platform) or,
opt-in, TeX Live via **apt** (Debian/Ubuntu with `sudo`), selected with `--backend auto|tinytex|apt`. TinyTeX's `bin` directory is prepended to `PATH` and the
`tlmgr` package collections that mirror the `texlive-*` packages are installed. Also
provides `build_pdf`, which compiles a `.tex` file and installs packages reported
missing in the build log on demand, plus the `pdflatex check` / `pdflatex download`
CLI handlers. See [Installing pdfLaTeX](../guides/installing-pdflatex.md).

::: ddocs.latex.pdflatex_utils
    options:
      show_root_heading: true
      show_source: true
