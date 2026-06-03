# `ddocs.markdown.pandoc_utils`

Locate, verify, and install the Pandoc executable that the conversion pipeline
shells out to. Confirms that `pandoc` is callable, downloads a prebuilt binary
via `pypandoc` when it is missing, and prepends its directory to `PATH` for the
current process.

::: ddocs.markdown.pandoc_utils
    options:
      show_root_heading: true
      show_source: true
