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

!!! warning "Ubuntu 26.04 runners"
    On `ubuntu-latest` (now Ubuntu 26.04) the apt TeX Live currently fails to build the Deltares
    templates. Until this is fixed, pin the job to `ubuntu-24.04`. See
    [Troubleshooting](#troubleshooting-ubuntu-2604-captiontocbasic-error).

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

## Troubleshooting: Ubuntu 26.04 `caption`/`tocbasic` error

**Symptom.** Building a Deltares document (e.g. with `build_pdf` or a bare `pdflatex`) on Ubuntu 26.04
(`ubuntu-latest` on GitHub Actions) fails with:

```text
! LaTeX Error: Unknown message 'caption-code-by-class-deactivated' for module
(LaTeX)        'tocbasic'.
```

The `RuntimeError` raised by `build_pdf` includes this error plus a log excerpt starting at it.

**Cause.** The apt TeX Live on 26.04 (`2025.20260124`) ships `caption` v3.6o (2023/08/05) together with a newer
KOMA-Script `tocbasic`. The older `caption` raises a message that the newer `tocbasic` no longer defines, and the
Deltares document classes load `caption`. Adding `texlive-latex-recommended` does **not** help, because both packages
already come from it. Tracked in
[issue #14](https://github.com/Deltares-research/doc_utils/issues/14).

**Workarounds** (until #14 is fixed):

1. **Pin the runner to Ubuntu 24.04** *(verified: this is what the project's own CI does)*. Its TeX Live ships a
   matching `caption`/`tocbasic` pair.

    ```yaml
    jobs:
      build-docs:
        runs-on: ubuntu-24.04   # not ubuntu-latest, until issue #14 is fixed
    ```

2. **Use the TinyTeX backend** *(not yet tested against this error)*. TinyTeX installs every package from one TeX Live
   release via `tlmgr`, so the versions should be consistent. Do not install the apt `texlive-*` packages in the same
   job, because `ddocs` skips the install when a `pdflatex` is already on `PATH`.

    ```bash
    ddocs pdflatex download --backend tinytex
    ```

**Check whether you are affected.** On the runner, print the installed versions:

```bash
kpsewhich -all tocbasic.sty caption.sty
grep -m1 ProvidesPackage "$(kpsewhich caption.sty)"   # 2023/08/05 v3.6o means the old caption is installed
```

Remove the pin once issue #14 is resolved.

## Caveats

- **apt needs root** (`sudo`). On a machine without passwordless `sudo`, `auto` falls back
  to TinyTeX.
- **TinyTeX downloads from CTAN per package** via `tlmgr`, which is slower than apt — use
  apt on Linux CI, or cache the install.
- `texlive-fonts-extra` (apt) / `collection-fontsextra` (tlmgr) is the heaviest item; drop
  it from `--packages` if your documents do not need exotic fonts.
- The **TinyTeX backend downloads and runs the official upstream installer script** (from
  `yihui.org` over HTTPS) — i.e. it executes remote code, the same trust model as the
  documented `curl … | sh` install. There is no checksum/signature pinning. If that is not
  acceptable in your environment, use `--backend apt` (or pre-install TeX yourself) instead.
