# Converting Markdown to LaTeX

`ddocs markdown-to-latex` is the core command of the package. It converts a directory of
Markdown files into LaTeX using [Pandoc](https://pandoc.org/), then applies a set of
**Deltares-specific post-processing** fixes so the output drops cleanly into a Deltares
LaTeX document.

For the auto-generated API reference, see [`ddocs.markdown`](../reference/markdown.md).

## Prerequisites

The conversion shells out to `pandoc`. You do **not** need to install Pandoc separately —
it ships bundled with the `pypandoc-binary` dependency, and `markdown-to-latex` makes the
bundled binary discoverable automatically before converting. You can verify this up front:

```bash
ddocs check-pandoc
```

See [Installation](../installation.md) for the full prerequisite list.

## The command

```bash
ddocs markdown-to-latex --input docs/mkdocs --output docs/latex
```

| Option | Required | Default | What it does |
|--------|----------|---------|--------------|
| `--input`, `-i` | ✅ | — | Directory containing the Markdown files to convert. |
| `--output`, `-o` | ✅ | — | Directory for the generated `.tex` files (created if it does not exist). |
| `--template` | — | bundled Deltares template | A custom Pandoc LaTeX template to use instead of the default. |
| `--standalone` | — | off (fragments) | Emit complete, compilable LaTeX documents instead of includable fragments. |
| `--pattern` | — | `*.md` | Glob pattern selecting which files to convert. |

Each `<name>.md` in the input directory is converted to `<name>.tex` in the output
directory.

> **The default pattern is not recursive.** `*.md` matches only the top level of
> `--input`. To walk subdirectories, pass a recursive glob: `--pattern "**/*.md"`.

> **Recursive matches are flattened.** Every output file is written directly into `--output` as
> `<name>.tex`, so the subdirectory structure is not preserved. If two files share a name (for example
> `a/intro.md` and `b/intro.md`), the second silently overwrites the first and the run still reports
> success. Keep file names unique when converting recursively.

## Fragments vs. standalone documents

This is the most important choice, set by `--standalone`:

| Mode | Flag | Template used | Output |
|------|------|---------------|--------|
| **Fragment** *(default)* | *(none)* | `deltares_fragment_template.tex` | A LaTeX snippet meant to be `\input{}`/`\include{}`d into a larger document. A small compatibility preamble (`\tightlist`, `\passthrough`) is prepended so it also works on its own. |
| **Standalone** | `--standalone` | `deltares_template.tex` | A complete document with preamble and `\begin{document}…\end{document}`, ready to compile directly with `pdflatex`. |

```bash
# Fragments to include from a master .tex (default)
ddocs markdown-to-latex -i docs/mkdocs -o docs/latex

# Complete, directly-compilable documents
ddocs markdown-to-latex -i docs/mkdocs -o docs/latex --standalone
```

Use **fragments** when you maintain one master Deltares `.tex` that pulls chapters in;
use **standalone** when each Markdown file should become its own PDF.

## What Pandoc is told to do

Every conversion runs Pandoc `--from markdown --to latex` with two fixed options:

- `--listings` — render fenced code blocks with the `listings` package.
- `--number-sections` — number the generated sections.

In standalone mode `--standalone` is added, and in both modes the chosen template is
passed via `--template`.

## Deltares post-processing

After Pandoc runs, `ddocs` rewrites the generated `.tex` to fix issues that commonly break
a Deltares build. This is the value the command adds over a bare `pandoc` call:

| Step | Function | What it fixes |
|------|----------|---------------|
| UTF-8 → LaTeX | `replace_utf8_tree_chars` | Converts box-drawing characters (`├ │ └ ─ …`) and symbols (`✓ ✗ ⚠ → ← … — –`, smart quotes) to LaTeX-safe equivalents, and strips emoji variation selectors. Prevents "Unicode character not set up for use with LaTeX" errors. |
| Table widths | `fix_table_column_widths` | Heuristically rebalances `longtable` column widths so wide tables (e.g. CLI option tables) don't overlap or overflow the text block. |
| Long words | `wrap_long_words_in_tables` | Wraps very long unbroken tokens in table cells with `\seqsplit{}` so they break instead of running past the column. |

If post-processing fails for a file, the conversion still succeeds — a warning is printed
and the raw Pandoc output is kept.

## Output and exit codes

The command prints per-file progress and a summary, then returns an exit code you can use
in scripts and CI:

| Exit code | Meaning |
|-----------|---------|
| `0` | Every matched file converted successfully. This includes the case where the pattern matched **no** files: a "No markdown files found" message is printed, but the exit code is still `0`. |
| `1` | The input directory or template was missing, Pandoc was unavailable, or at least one file failed to convert. |

## Python API

The same functionality is importable from `ddocs.markdown`:

```python
from pathlib import Path
from ddocs.markdown import convert_markdown_to_latex, convert_all_markdown_files

# Convert a single file
convert_markdown_to_latex(
    Path("docs/mkdocs/intro.md"),
    Path("docs/latex/intro.tex"),
    standalone=False,            # fragment
)

# Convert a whole directory; returns (successful, total)
ok, total = convert_all_markdown_files(
    Path("docs/mkdocs"),
    Path("docs/latex"),
    standalone=True,
    pattern="**/*.md",
)
print(f"{ok}/{total} converted")
```

| Function | Purpose |
|----------|---------|
| `convert_markdown_to_latex(input_file, output_file, template=None, standalone=False)` | Convert one Markdown file; returns `True`/`False`. |
| `convert_all_markdown_files(input_dir, output_dir, template=None, standalone=False, pattern="*.md")` | Convert a directory; returns `(successful, total)`. |

## Where this fits in a full pipeline

`markdown-to-latex` produces the `.tex`; the other commands provide the styling and the
engine to turn it into a PDF:

```bash
# 1. Convert Markdown to Deltares LaTeX fragments
ddocs markdown-to-latex -i docs/mkdocs -o docs/latex

# 2. Fetch the Deltares LaTeX styles/templates (see the RepoCloner guide)
ddocs get-tex-template --output-dir ./latex

# 3. Ensure a TeX engine is available (see the pdfLaTeX guide)
ddocs pdflatex download

# 4. Compile your master document, then tidy build artifacts
pdflatex docs/latex/manual.tex
ddocs clean --directory docs/latex --recursive
```

See [RepoCloner & authentication](repo-cloner-authentication.md) and
[Installing pdfLaTeX](installing-pdflatex.md) for steps 2–3.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Pandoc is not installed…` | The bundled binary could not be located on `PATH`. | Run `ddocs check-pandoc`; if it still fails, install Pandoc from <https://pandoc.org/installing.html>. |
| `Input directory not found` / `not a directory` | `--input` points at a missing path or a file. | Pass an existing directory to `-i`. |
| `Template file not found` | `--template` path is wrong. | Check the path, or omit `--template` to use the bundled Deltares template. |
| `No markdown files found` | The pattern matched nothing (often the non-recursive default). | Verify the files exist; use `--pattern "**/*.md"` to recurse into subdirectories. |
| A fragment won't compile on its own | Fragments are meant to be `\input` into a master document. | Re-run with `--standalone` for a self-contained document. |
| LaTeX errors on a custom template | The template is missing variables Pandoc/the post-processing expects. | Start from a copy of the bundled `deltares_template.tex` / `deltares_fragment_template.tex`. |
