# Deltares doc_utils (`ddocs`)

A Python utility package for converting Markdown documentation to LaTeX, designed for
Deltares documentation workflows. It wraps [Pandoc](https://pandoc.org/) with
Deltares-specific LaTeX post-processing and ships a `ddocs` command-line interface, plus
helpers for fetching the Deltares LaTeX templates and provisioning a `pdflatex` toolchain.

📖 **Full documentation:** <https://deltares-research.github.io/doc_utils/>

## Features

- **Markdown → LaTeX conversion** with Deltares-specific post-processing: Unicode/box-drawing
  cleanup, `longtable` column-width fixes, and long-word wrapping in tables.
- **Fragments or standalone documents** — emit includable `.tex` snippets or complete,
  directly-compilable documents.
- **Template retrieval** — clone the private Deltares LaTeX template repository with token or
  SSH authentication.
- **pdfLaTeX provisioning** — install a TeX engine (TinyTeX or apt) and the required packages
  on demand.
- **Build cleanup** — remove LaTeX build artifacts (`.aux`, `.log`, `.bbl`, …).

## Requirements

- **Python ≥ 3.11**
- **Pandoc** — bundled via `pypandoc-binary`; no separate install needed.
- **pdfLaTeX** — optional, only for building PDFs; provisioned via `ddocs pdflatex download`.

## Installation

```bash
pip install "git+https://github.com/Deltares-research/doc_utils.git"
```

See the [installation guide](https://deltares-research.github.io/doc_utils/installation/)
for the `uv` workflow and a development setup.

## Commands

| Command                   | Description                                                          |
|---------------------------|----------------------------------------------------------------------|
| `ddocs markdown-to-latex` | Convert Markdown files to LaTeX fragments or standalone documents.   |
| `ddocs get-tex-template`  | Clone the Deltares LaTeX repository and copy template files.         |
| `ddocs clean`             | Remove LaTeX build artifacts (`.aux`, `.log`, `.bbl`, …).            |
| `ddocs check-pandoc`      | Verify the bundled Pandoc is callable (adds it to `PATH` if needed). |
| `ddocs pdflatex check`    | Probe whether `pdflatex` is already installed (installs nothing).    |
| `ddocs pdflatex download` | Install `pdflatex` and the required TeX packages (apt or TinyTeX).   |

Run `ddocs --help` or `ddocs <command> --help` for the full option list.

## Quick start

```bash
# Convert Markdown to LaTeX fragments
ddocs markdown-to-latex --input docs/mkdocs --output docs/latex

# Generate standalone LaTeX documents
ddocs markdown-to-latex -i docs/mkdocs -o docs/latex --standalone

# Retrieve the Deltares LaTeX templates
ddocs get-tex-template --output-dir ./templates

# Ensure a TeX engine is available, then clean build files afterwards (-r recurses)
ddocs pdflatex download
ddocs clean --directory ./docs/latex --recursive
```

## Development

Install the package with its development dependencies:

```bash
pip install -e ".[dev]"
```

> The project pins its environment outside the repo and uses `uv`. See `CLAUDE.md` for the
> exact `UV_PROJECT_ENVIRONMENT` setup, test commands, and code-style conventions.

### Running the tests

```bash
pytest
```

The suite includes **live** tests (marked `integration` / `e2e`) that clone the private
`Deltares/LatexInstallation` repository and build a PDF. They require network access and
credentials with read access to that repo — a token in `GITHUB_TOKEN` / `GH_TOKEN` (or
`LATEX_REPO_TOKEN` in a local `.env`, which `tests/conftest.py` bridges), or an SSH key.

To run only the fast, hermetic tests (no network, no credentials), deselect them:

```bash
pytest -m "not e2e and not integration"
```

Never commit your `.env` / token — `.env` is git-ignored.

## License

MIT
