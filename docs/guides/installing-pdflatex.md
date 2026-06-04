# Installing pdfLaTeX

Turning the generated LaTeX into a PDF needs a TeX engine (`pdflatex`) plus a set of TeX
packages and `biber`. Unlike Pandoc (a single bundled binary), TeX is a large
distribution, so `ddocs` provisions it on demand through the `pdflatex` command group.

For the auto-generated API, see [`ddocs.latex.pdflatex_utils`](../reference/pdflatex_utils.md).

## The two commands

| Command                   | What it does                                                                                    |
|---------------------------|-------------------------------------------------------------------------------------------------|
| `ddocs pdflatex check`    | **Probe only** — is `pdflatex` already callable? Exits `0` if yes, `1` if no. Installs nothing. |
| `ddocs pdflatex download` | **Install** `pdflatex` (and the TeX packages) if it is missing.                                 |

```bash
ddocs pdflatex check        # just verify; good for a fast CI gate
ddocs pdflatex download     # install using the best available backend
```

## Backends

`ddocs pdflatex download` installs TeX using one of two backends, chosen with `--backend`:

| Backend              | When it is used           | Notes                                                                                                                |
|----------------------|---------------------------|----------------------------------------------------------------------------------------------------------------------|
| **apt**              | Debian/Ubuntu with `sudo` | `apt-get install texlive-*` — prebuilt `.deb`s from a fast mirror; by far the quickest on CI. Needs root.            |
| **tinytex**          | everywhere else           | Downloads and runs the official **TinyTeX** installer (root-free, cross-platform) and `tlmgr install`s the packages. |
| **auto** *(default)* | —                         | Use **apt** when `apt-get` is available on Linux, otherwise fall back to **TinyTeX**.                                |

```bash
ddocs pdflatex download --backend auto      # default: apt on Debian/Ubuntu, else TinyTeX
ddocs pdflatex download --backend apt        # force apt (fast; needs sudo)
ddocs pdflatex download --backend tinytex    # force TinyTeX (no root, any OS)
```

## Controlling which packages are installed

By default, `download` installs a set of `texlive-*` / `tlmgr` collections so that a
**bare `pdflatex` call** (i.e. compiling outside of `ddocs`) finds everything a Deltares
document needs. You can trim this for a faster, leaner install:

```bash
# Only the packages you know a document needs (much faster)
ddocs pdflatex download --packages lipsum,tcolorbox,pgf

# Just the engine, no extra packages (rely on on-demand install while building)
ddocs pdflatex download --no-packages
```

- `--packages` takes a comma/space-separated list. For the **tinytex** backend these are
  `tlmgr` package names; the **apt** backend installs its fixed `texlive-*` set.
- `--no-packages` provisions only the engine.

> **Building via `ddocs`?** If you compile with [`build_pdf`](#python-api) instead of a
> bare `pdflatex`, missing packages are installed **on demand** (it parses the LaTeX log
> and `tlmgr install`s what is missing), so a lean install is usually enough.

## Using it in CI

A typical documentation pipeline fetches the Deltares styles, ensures `pdflatex`, then
compiles:

```yaml
- run: pip install "git+https://github.com/Deltares-research/doc_utils.git"
- run: ddocs get-tex-template --output-dir ./latex --no-ssh
- run: ddocs pdflatex download          # auto -> apt on Ubuntu runners (fast)
- run: pdflatex docs/manual.tex          # bare pdflatex; packages are already present
```

On an Ubuntu runner the `auto` backend picks **apt**, so this is fast and the
`texlive-*` packages (e.g. `lipsum.sty`) are available to the bare `pdflatex` step.

### Avoid re-downloading every run

The bytes only need to land once. Cache the TeX install between runs:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.TinyTeX            # or the apt cache for the apt backend
    key: tex-${{ runner.os }}-v1
```

First run downloads; subsequent runs restore from cache in seconds.

## Python API

The same functionality is available programmatically from `ddocs.latex`:

```python
from ddocs.latex import check_pdflatex_installed, build_pdf

# Ensure pdflatex is available (apt or TinyTeX), installing the default packages
check_pdflatex_installed()                       # -> True/False
check_pdflatex_installed(backend="tinytex")       # force a backend
check_pdflatex_installed(packages=["lipsum"])     # lean tinytex package set
check_pdflatex_installed(install_packages=False)  # engine only

# Compile a .tex to PDF, installing any missing packages on demand
pdf = build_pdf("docs/manual.tex")                # -> Path to the produced PDF
```

| Function | Purpose |
| --- | --- |
| `check_pdflatex_installed(install_packages=True, packages=..., backend="auto")` | Ensure `pdflatex` is present; install via apt/TinyTeX if needed. |
| `install_texlive_apt(packages=APT_TEXLIVE_PACKAGES)` | The apt backend (Debian/Ubuntu). |
| `build_pdf(tex_file, ...)` | Compile a `.tex` to PDF, installing missing packages on demand. |
| `sanity_check("pdflatex")` | Pure probe — is the command callable? |

## Caveats

- **apt needs root** (`sudo`). On a machine without passwordless `sudo`, `auto` falls back
  to TinyTeX.
- **TinyTeX downloads from CTAN per package** via `tlmgr`, which is slower than apt — use
  apt on Linux CI, or cache the install.
- `texlive-fonts-extra` (apt) / `collection-fontsextra` (tlmgr) is the heaviest item; drop
  it from `--packages` if your documents do not need exotic fonts.
