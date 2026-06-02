"""Command-line interface for ddocs."""

import sys
import argparse
from pathlib import Path
from ddocs import __version__
from ddocs.markdown import mark_down_to_latex_cli, clean_latex_cli
from ddocs.repo_cloner import clone_repo_cli
from ddocs.pandoc_utils import check_pandoc_cli


def create_parser():
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

  # Get LaTeX templates
  ddocs get-tex-template --output-dir ./templates

  # Clean LaTeX build files
  ddocs clean --directory ./docs/latex

  # Check that Pandoc is installed (download it if missing)
  ddocs check-pandoc
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
        help='Available operations: markdown-to-latex, get-tex-template, clean, check-pandoc'
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

    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Dispatch to the selected command and propagate its exit code
    if args.command == 'get-tex-template':
        exit_code = clone_repo_cli(args.output_dir)
    elif args.command == 'markdown-to-latex':
        exit_code = mark_down_to_latex_cli(args)
    elif args.command == 'clean':
        exit_code = clean_latex_cli(args)
    elif args.command == 'check-pandoc':
        exit_code = check_pandoc_cli(args)
    else:
        parser.print_help()
        exit_code = 1

    return exit_code


if __name__ == '__main__':
    sys.exit(main())

