# Deltares doc_utils

`ddocs` is a Python utility package for converting Markdown documentation to
LaTeX, designed for Deltares documentation workflows. It wraps Pandoc with
Deltares-specific LaTeX post-processing and ships a `ddocs` command-line
interface, plus helpers for fetching the Deltares LaTeX templates and
provisioning a `pdflatex` toolchain.

## What it does

- **Convert Markdown → LaTeX** with Deltares-specific post-processing (Unicode
  cleanup, table-width fixes, long-word wrapping) — see
  [Converting Markdown to LaTeX](guides/converting-markdown-to-latex.md).
- **Fetch the Deltares LaTeX templates** from the private template repository,
  with token/SSH authentication — see
  [RepoCloner & authentication](guides/repo-cloner-authentication.md).
- **Provision pdfLaTeX** (TinyTeX or apt) and the required TeX packages on demand —
  see [Installing pdfLaTeX](guides/installing-pdflatex.md).
- **Clean up** LaTeX build artifacts when you're done.

## Commands

| Command | Description |
| --- | --- |
| `ddocs markdown-to-latex` | Convert Markdown files to LaTeX fragments or standalone documents. |
| `ddocs get-tex-template` | Clone the Deltares LaTeX repository and copy template files. |
| `ddocs clean` | Remove LaTeX build artifacts (`.aux`, `.log`, `.bbl`, …). |
| `ddocs check-pandoc` | Verify the bundled Pandoc is callable (adds it to `PATH` if needed). |
| `ddocs pdflatex check` | Probe whether `pdflatex` is already installed (installs nothing). |
| `ddocs pdflatex download` | Install `pdflatex` and the required TeX packages (apt or TinyTeX). |

Run `ddocs --help` (or `ddocs <command> --help`) to see every option.

## Installation

```bash
pip install "git+https://github.com/Deltares-research/doc_utils.git"
```

See [Installation](installation.md) for requirements, the `uv` workflow, and a
development setup.

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

## Where to next

- New here? Start with [Installation](installation.md), then
  [Converting Markdown to LaTeX](guides/converting-markdown-to-latex.md).
- Building PDFs in CI? See [Installing pdfLaTeX](guides/installing-pdflatex.md) and
  [RepoCloner & authentication](guides/repo-cloner-authentication.md).
- Looking for module-level docs? See the [API Reference](reference/index.md).
