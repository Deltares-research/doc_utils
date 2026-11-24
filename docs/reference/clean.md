# `ddocs.latex.clean`

Remove LaTeX build artifacts (`.aux`, `.log`, `.bbl`, ...) from a directory. Backs the
`ddocs clean` command; independent of the Markdown-to-LaTeX conversion.

By default it removes LaTeX build artifacts (`.aux`, `.log`, `.toc`, `.bbl`, minitoc `.mtc*`/`.maf`, nomencl
`.nlo`/`.nls`, …); source `.tex` files and the produced `.pdf` are never touched. With `--templates` it also removes
the files `ddocs get-tex-template` downloads: `deltares_*.cls/.sty/.bst/.ist` and the `pictures/` directory directly
under the cleaned directory.

::: ddocs.latex.clean
    options:
      show_root_heading: true
      show_source: true
