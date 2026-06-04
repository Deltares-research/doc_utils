"""Command-line interface for ddocs."""

import sys
import argparse
from pathlib import Path
from ddocs import __version__
from ddocs.markdown import mark_down_to_latex_cli, check_pandoc_cli
from ddocs.latex import clean_latex_cli, check_pdflatex_cli
from ddocs.templates import clone_repo_cli


def create_parser() -> argparse.ArgumentParser:
    """Build the ``ddocs`` argument parser with all subcommands.

    Registers the ``markdown-to-latex``, ``get-tex-template``, ``clean`` and
    ``check-pandoc`` subcommands. ``get-tex-template`` accepts ``--output-dir`` plus
    the authentication options ``--token``, ``--username``, ``--password`` and
    ``--no-ssh``.

    Returns:
        The configured ``argparse.ArgumentParser``.

    Examples:
        - Parse a ``get-tex-template`` invocation and read the auth options:
            ```python
            >>> from ddocs.cli import create_parser
            >>> args = create_parser().parse_args(
            ...     ["get-tex-template", "-o", "out", "--token", "tok"]
            ... )
            >>> args.command
            'get-tex-template'
            >>> args.token
            'tok'
            >>> (args.username, args.password, args.no_ssh)
            (None, None, False)

            ```
        - ``--no-ssh`` flips the SSH-fallback flag:
            ```python
            >>> from ddocs.cli import create_parser
            >>> args = create_parser().parse_args(["get-tex-template", "-o", "out", "--no-ssh"])
            >>> args.no_ssh
            True

            ```

    See Also:
        main: Parses arguments with this parser and dispatches to the handlers.
    """
    parser = argparse.ArgumentParser(
        prog='ddocs',
        description='Deltares HMS documentation utility tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all markdown files in user_docs
  ddocs markdown-to-latex --input docs/mkdocs --output docs/latex

  # Generate standalone LaTeX documents
  ddocs markdown-to-latex --input docs/mkdocs --output docs/latex --standalone

  # Get LaTeX templates (SSH key used when no credentials are given)
  ddocs get-tex-template --output-dir ./templates

  # ... authenticating with a token, or a username/password
  ddocs get-tex-template -o ./templates --token <token>
  ddocs get-tex-template -o ./templates --username <user> --password <token>

  # Clean LaTeX build files
  ddocs clean --directory ./docs/latex

  # Check that Pandoc is installed (download it if missing)
  ddocs check-pandoc

  # Check that pdflatex is installed (install TinyTeX if missing)
  ddocs check-pdflatex
        """
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(
        title='operation type',
        description='Select the operation to perform',
        dest='command',
        required=True,
        help='Available operations: markdown-to-latex, get-tex-template, clean, check-pandoc, check-pdflatex'
    )

    # sub-command: markdown-to-latex
    markdown_to_latex = subparsers.add_parser(
        "markdown-to-latex",
        help='Convert Markdown to LaTeX',
    )

    markdown_to_latex.add_argument(
        '--input',
        "-i",
        type=Path,
        required=True,
        help='Input directory with Markdown files'
    )
    markdown_to_latex.add_argument(
        '--output',
        "-o",
        type=Path,
        required=True,
        help='Output directory for LaTeX files'
    )
    markdown_to_latex.add_argument(
        '--template',
        type=Path,
        help='Custom Pandoc LaTeX template'
    )
    markdown_to_latex.add_argument(
        '--standalone',
        action='store_true',
        help='Generate standalone LaTeX documents (vs. fragments for inclusion)'
    )
    markdown_to_latex.add_argument(
        '--pattern',
        type=str,
        default='*.md',
        help='Glob pattern for matching files (default: *.md)'
    )

    # sub-command: get-tex-template
    get_tex_template = subparsers.add_parser(
        'get-tex-template',
        help='Clone Deltares LatexInstallation repo and copy template files',
    )
    get_tex_template.add_argument(
        '--output-dir',
        "-o",
        type=Path,
        required=True,
        help='Output directory for the template files'
    )
    get_tex_template.add_argument(
        '--token',
        help='Token for HTTPS auth (defaults to the GITHUB_TOKEN / GH_TOKEN env var)'
    )
    get_tex_template.add_argument(
        '--username',
        help='Username for HTTPS basic auth (defaults to the GIT_USERNAME env var)'
    )
    get_tex_template.add_argument(
        '--password',
        help='Password/token for HTTPS basic auth (defaults to the GIT_PASSWORD env var)'
    )
    get_tex_template.add_argument(
        '--no-ssh',
        action='store_true',
        help='Disable the SSH-key fallback; clone anonymously when no credentials are given'
    )

    # sub-command: clean
    clean = subparsers.add_parser(
        'clean',
        help='Clean LaTeX build files (aux, log, bbl, etc.)',
    )
    clean.add_argument(
        '--directory',
        "-d",
        type=Path,
        required=True,
        help='Directory to clean LaTeX build files from'
    )
    clean.add_argument(
        '--recursive',
        "-r",
        action='store_true',
        help='Clean recursively in subdirectories'
    )

    # sub-command: check-pandoc
    subparsers.add_parser(
        'check-pandoc',
        help='Check that Pandoc is installed; download it if missing',
    )

    # sub-command: check-pdflatex
    check_pdflatex = subparsers.add_parser(
        'check-pdflatex',
        help='Check that pdflatex is installed; install TinyTeX if missing',
    )
    check_pdflatex.add_argument(
        '--packages',
        help='Comma/space-separated tlmgr packages to install (overrides the default collections)'
    )
    check_pdflatex.add_argument(
        '--no-packages',
        action='store_true',
        help='Only ensure pdflatex; do not install any extra TeX packages'
    )

    return parser


def main() -> int:
    """Parse the command line and dispatch to the selected subcommand handler.

    Builds the parser via :func:`create_parser`, parses ``sys.argv``, and calls the
    matching handler. For ``get-tex-template`` the authentication options
    (``--token`` / ``--username`` / ``--password`` / ``--no-ssh``) are forwarded to
    :func:`ddocs.templates.repo_cloner.clone_repo_cli`. The handler's exit code is returned so a
    caller can pass it to :func:`sys.exit`.

    Returns:
        The subcommand handler's exit code (``0`` on success, non-zero on failure).

    Examples:
        - Run a command and use the result as a process exit status:
            ```python
            >>> import sys
            >>> from ddocs.cli import main
            >>> sys.exit(main())  # doctest: +SKIP

            ```
        - Authenticate ``get-tex-template`` with a token (sets ``sys.argv`` first):
            ```python
            >>> import sys
            >>> from ddocs.cli import main
            >>> sys.argv = ["ddocs", "get-tex-template", "-o", "out", "--token", "tok"]
            >>> code = main()  # doctest: +SKIP
            >>> code  # doctest: +SKIP
            0

            ```

    See Also:
        create_parser: Builds the parser this function uses.
        ddocs.templates.repo_cloner.clone_repo_cli: Handles ``get-tex-template``.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Dispatch to the selected command and propagate its exit code
    if args.command == 'get-tex-template':
        exit_code = clone_repo_cli(
            args.output_dir,
            token=args.token,
            username=args.username,
            password=args.password,
            prefer_ssh=not args.no_ssh,
        )
    elif args.command == 'markdown-to-latex':
        exit_code = mark_down_to_latex_cli(args)
    elif args.command == 'clean':
        exit_code = clean_latex_cli(args)
    elif args.command == 'check-pandoc':
        exit_code = check_pandoc_cli(args)
    elif args.command == 'check-pdflatex':
        exit_code = check_pdflatex_cli(args)
    else:
        parser.print_help()
        exit_code = 1

    return exit_code


if __name__ == '__main__':
    sys.exit(main())

