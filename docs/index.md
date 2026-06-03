# Deltares doc_utils

`ddocs` is a Python utility package for converting Markdown documentation to
LaTeX, designed for Deltares documentation workflows. It wraps Pandoc with
Deltares-specific LaTeX post-processing and ships a `ddocs` command-line
interface.

## Commands

| Command | Description |
| --- | --- |
| `ddocs markdown-to-latex` | Convert Markdown files to LaTeX fragments or standalone documents. |
| `ddocs get-tex-template` | Clone the Deltares LaTeX repository and copy template files. |
| `ddocs clean` | Remove LaTeX build artifacts (`.aux`, `.log`, `.bbl`, …). |
| `ddocs check-pandoc` | Verify Pandoc is installed; download it if missing. |

## Quick start

```bash
# Convert Markdown to LaTeX fragments
ddocs markdown-to-latex --input docs/mkdocs --output docs/latex

# Generate standalone LaTeX documents
ddocs markdown-to-latex -i docs/mkdocs -o docs/latex --standalone

# Retrieve the Deltares LaTeX templates
ddocs get-tex-template --output-dir ./templates

# Clean LaTeX build files (use -r to recurse)
ddocs clean --directory ./docs/latex --recursive
```

See the [API Reference](reference/index.md) for module-level documentation.
