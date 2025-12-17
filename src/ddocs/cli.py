"""Command-line interface for ddocs."""

import sys
import argparse
from pathlib import Path
from ddocs import __version__
from ddocs.markdown import mark_down_to_latex_cli


def create_parser():
    parser = argparse.ArgumentParser(
        prog='ddocs',
        description='Deltares HMS documentation utility tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all markdown files in user_docs
  ddocs markdown_to_latex --input docs/mkdocs --output docs/latex

  # Generate standalone LaTeX documents
  ddocs markdown_to_latex --input docs/mkdocs --output docs/latex --standalone

  # Get LaTeX templates
  ddocs get-tex-template --output-dir ./templates
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
        help='Available operations: markdown_to_latex, get-tex-template'
    )

    # sub-command: markdown_to_latex
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

    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == 'markdown-to-latex':
        # Handle markdown_to_latex command
        mark_down_to_latex_cli(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    sys.exit(main())

