# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html), and the format is maintained by [Commitizen](https://commitizen-tools.github.io/commitizen/) using [Conventional Commits](https://www.conventionalcommits.org/).

## Unreleased

### Breaking changes

- **CLI: `ddocs check-pdflatex` removed.** Use `ddocs pdflatex download` (install) or
  `ddocs pdflatex check` (probe only) instead. Consumers calling `check-pdflatex` (e.g.
  CI pipelines) must update the command.
- **Package layout: modules moved into subpackages.** `ddocs.repo_cloner`,
  `ddocs.pandoc_utils`, and `ddocs.pdflatex_utils` no longer exist at the top level.
  Import from the new locations (or the subpackage facades):
  `ddocs.templates.repo_cloner` / `from ddocs.templates import …`,
  `ddocs.markdown.pandoc_utils` / `from ddocs.markdown import …`,
  `ddocs.latex.pdflatex_utils` / `from ddocs.latex import …`.

### Added

- `pdflatex` command group with `check` and `download`, an apt install backend
  (`--backend auto|apt|tinytex`), and `--packages` / `--no-packages` options.
- `markdown-to-latex` improvements, a `clean` command, `get-tex-template` authentication
  flags, and an mkdocs documentation site with guides.


