# Installation

`ddocs` is a Python package. It installs the `ddocs` command-line tool and the importable
`ddocs` library.

## Requirements

| Requirement | Needed for | Notes |
|-------------|------------|-------|
| **Python ≥ 3.11** | everything | Declared in `pyproject.toml`. |
| **Pandoc** | `markdown-to-latex` | **Bundled** — ships with the `pypandoc-binary` dependency and is added to `PATH` automatically. No separate install needed. |
| **pdfLaTeX + TeX packages** | compiling the LaTeX to PDF | *Optional*, and only when you build PDFs. Provisioned on demand via `ddocs pdflatex download` — see [Installing pdfLaTeX](guides/installing-pdflatex.md). |
| **Git + repo credentials** | `get-tex-template` | Only when fetching the private Deltares templates — see [RepoCloner & authentication](guides/repo-cloner-authentication.md). |

## Install

The package is hosted on GitHub. Install the latest version directly from the repository:

=== "pip"

    ```bash
    pip install "git+https://github.com/Deltares-research/doc_utils.git"
    ```

=== "uv"

    ```bash
    uv pip install "git+https://github.com/Deltares-research/doc_utils.git"
    ```

To pin a specific release, append a tag:

```bash
pip install "git+https://github.com/Deltares-research/doc_utils.git@0.2.2"
```

## Verify the installation

```bash
ddocs --version
ddocs --help
ddocs check-pandoc      # confirms the bundled Pandoc is callable
```

`ddocs --help` lists every subcommand; see the [Home page](index.md) for the command
overview or the [API Reference](reference/index.md) for module-level documentation.

## Development install

To work on `ddocs` itself, clone the repository and install it in editable mode with the
development and docs dependency groups:

```bash
git clone https://github.com/Deltares-research/doc_utils.git
cd doc_utils
uv sync --group dev --group docs
```

`dev` (tests, linting) and `docs` (MkDocs + mkdocstrings to build this site) are dependency
groups, not extras, so `pip install ".[dev]"` does not work. With pip ≥ 25.1 use
`pip install -e . --group dev --group docs`.

> **Contributors:** the project pins its environment outside the repo and uses `uv`. See
> `CLAUDE.md` in the repository root for the exact `UV_PROJECT_ENVIRONMENT` setup, the test
> commands, and the code-style conventions.

### Building the documentation locally

With the `docs` group installed:

```bash
mkdocs serve            # live-reload preview at http://127.0.0.1:8000
mkdocs build --strict   # one-shot build; fails on broken links/refs
```

This site is versioned and published to GitHub Pages with
[`mike`](https://github.com/jimporter/mike) via the **Deploy MkDocs** workflow.
