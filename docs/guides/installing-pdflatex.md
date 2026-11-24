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
| **tinytex**          | everywhere                | Downloads and runs the official **TinyTeX** installer (root-free, cross-platform) and `tlmgr install`s the packages. All packages come from one TeX Live release, so versions are consistent. |
| **apt**              | opt-in; Debian/Ubuntu with `sudo` | `apt-get install texlive-*` — prebuilt `.deb`s from a fast mirror. Needs root, and the distro's package versions can be mutually incompatible (see [Troubleshooting](#troubleshooting-ubuntu-2604-captiontocbasic-error)). |
| **auto** *(default)* | —                         | Same as **tinytex** on every platform.                                                                               |

```bash
ddocs pdflatex download --backend auto      # default: TinyTeX
ddocs pdflatex download --backend apt        # opt in to apt (faster; needs sudo)
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
- run: ddocs pdflatex download          # auto -> TinyTeX
- run: pdflatex docs/manual.tex          # bare pdflatex; packages are already present
```

The `auto` backend installs **TinyTeX**, so every TeX package (e.g. `caption`, `tocbasic`, `lipsum.sty`) comes from
one consistent TeX Live release and works the same on any runner image. The project's own CI builds the Deltares
templates this way on `ubuntu-latest` (Ubuntu 26.04).

### Avoid re-downloading every run

The bytes only need to land once. Cache the TeX install between runs:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.TinyTeX
    key: tex-${{ runner.os }}-v1
```

First run downloads; subsequent runs restore from cache in seconds.

## Python API

The same functionality is available programmatically from `ddocs.latex`:

```python
from ddocs.latex import check_pdflatex_installed, build_pdf

# Ensure pdflatex is available (TinyTeX by default), installing the default packages
check_pdflatex_installed()                       # -> True/False
check_pdflatex_installed(backend="apt")           # opt in to apt (Debian/Ubuntu + sudo)
check_pdflatex_installed(packages=["lipsum"])     # lean tinytex package set
check_pdflatex_installed(install_packages=False)  # engine only

# Compile a .tex to PDF, installing any missing packages on demand
pdf = build_pdf("docs/manual.tex")                # -> Path to the produced PDF
```

| Function | Purpose |
| --- | --- |
| `check_pdflatex_installed(install_packages=True, packages=..., backend="auto")` | Ensure `pdflatex` is present; install via TinyTeX (or apt, opt-in) if needed. |
| `install_texlive_apt(packages=APT_TEXLIVE_PACKAGES)` | The opt-in apt backend (Debian/Ubuntu). |
| `build_pdf(tex_file, ...)` | Compile a `.tex` to PDF, installing missing packages on demand. |
| `sanity_check("pdflatex")` | Pure probe — is the command callable? |

## Troubleshooting: Ubuntu 26.04 `caption`/`tocbasic` error

**Symptom.** Building a Deltares document with the **apt** backend (or a distro-installed `pdflatex`) on Ubuntu 26.04
fails with:

```text
! LaTeX Error: Unknown message 'caption-code-by-class-deactivated' for module
(LaTeX)        'tocbasic'.
```

The `RuntimeError` raised by `build_pdf` includes this error plus a log excerpt starting at it.

**Cause.** The apt TeX Live on 26.04 (`2025.20260124`) ships `caption` v3.6o (2023/08/05) together with a newer
KOMA-Script `tocbasic`. The older `caption` raises a message that the newer `tocbasic` no longer defines, and the
Deltares document classes load `caption`. See [issue #14](https://github.com/Deltares-research/doc_utils/issues/14).

**Fix.** Use the default **TinyTeX** backend (`ddocs pdflatex download`, or `--backend tinytex`), which installs every
package from one TeX Live release. Do not install the apt `texlive-*` packages in the same job, because `ddocs` skips
the install when a `pdflatex` is already on `PATH`.

**Check whether you are affected.** Print the installed versions:

```bash
kpsewhich -all tocbasic.sty caption.sty
grep -m1 ProvidesPackage "$(kpsewhich caption.sty)"   # 2023/08/05 v3.6o means the old caption is installed
```

## Caveats

- **apt is opt-in and needs root** (`sudo`). It is faster, but the distro's TeX package versions can be
  inconsistent (see the Ubuntu 26.04 note above).
- **TinyTeX downloads from CTAN per package** via `tlmgr`, which is slower than apt — cache `~/.TinyTeX` on CI.
- `texlive-fonts-extra` (apt) / `collection-fontsextra` (tlmgr) is the heaviest item; drop
  it from `--packages` if your documents do not need exotic fonts.
- The **TinyTeX backend downloads and runs the official upstream installer script** (from
  `yihui.org` over HTTPS) — i.e. it executes remote code, the same trust model as the
  documented `curl … | sh` install. There is no checksum/signature pinning. If that is not
  acceptable in your environment, use `--backend apt` (or pre-install TeX yourself) instead.
