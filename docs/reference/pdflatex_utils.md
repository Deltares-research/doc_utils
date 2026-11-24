# `ddocs.latex.pdflatex_utils`

Locate, verify, and install pdfLaTeX. Confirms that `pdflatex` (and `biber`) are
callable and, when missing, installs TeX Live via **apt** (Debian/Ubuntu with `sudo`)
or the root-free **TinyTeX** installer (everywhere else), selected with
`--backend auto|apt|tinytex`. TinyTeX's `bin` directory is prepended to `PATH` and the
`tlmgr` package collections that mirror the `texlive-*` packages are installed. Also
provides `build_pdf`, which compiles a `.tex` file and installs packages reported
missing in the build log on demand, plus the `pdflatex check` / `pdflatex download`
CLI handlers. See [Installing pdfLaTeX](../guides/installing-pdflatex.md).

::: ddocs.latex.pdflatex_utils
    options:
      show_root_heading: true
      show_source: true
