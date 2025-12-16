"""Convert Markdown documentation to LaTeX format.

This script converts Markdown files from the mkdocs user_docs folder to LaTeX files
that can be included in PDF documentation. It uses Pandoc for the conversion.
"""

from pathlib import Path
import subprocess
import argparse
import sys
from ddocs import __path__
data_dir = Path(__path__[0]) / 'data'


def check_pandoc_installed() -> bool:
    """Check if Pandoc is installed and available.

    Returns:
        True if Pandoc is available, False otherwise
    """
    try:
        result = subprocess.run(
            ['pandoc', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Found Pandoc: {result.stdout.split()[1]}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def replace_utf8_tree_chars(content: str) -> str:
    """Replace UTF-8 box-drawing characters and symbols with LaTeX equivalents.

    Args:
        content: LaTeX content string

    Returns:
        Content with UTF-8 characters replaced
    """
    # Map UTF-8 box-drawing characters to ASCII equivalents
    replacements = {
        '├': '|',
        '│': '|',
        '└': '`',
        '─': '-',
        '┌': '+',
        '┐': '+',
        '┘': '+',
        '┴': '+',
        '┬': '+',
        '┤': '+',
        '├──': '|--',
        '└──': '`--',
        '│   ': '|   ',
        # Common Unicode symbols to LaTeX commands
        '✓': r'\checkmark',
        '✗': r'\texttimes',
        '⚠': r'\textbf{!}',  # Warning sign
        '⚠️': r'\textbf{!}',  # Warning sign with emoji modifier
        '→': r'$\rightarrow$',
        '←': r'$\leftarrow$',
        '↔': r'$\leftrightarrow$',
        '…': r'\ldots',
        '—': '---',  # em-dash
        '–': '--',   # en-dash
        '"': "``",   # left double quote
        '"': "''",   # right double quote
        ''': "`",    # left single quote
        ''': "'",    # right single quote
        '\ufe0f': '',  # Remove emoji variation selector
    }

    for utf8_char, ascii_char in replacements.items():
        content = content.replace(utf8_char, ascii_char)

    return content


def fix_table_column_widths(content: str) -> str:
    """Fix LaTeX table column widths for better formatting.

    Looks for tables and analyzes content to adjust column widths
    to prevent overlap.

    Args:
        content: LaTeX content string

    Returns:
        Content with adjusted table column widths
    """
    import re

    # Find all longtable environments
    longtable_pattern = r'(\\begin\{longtable\}.*?\\end\{longtable\})'

    def fix_single_table(table_text):
        """Fix a single table by analyzing its content."""

        # Find the column specification line
        col_pattern = r'>\{\\raggedright\\arraybackslash\}p\{\(\\linewidth - (\d+)\\tabcolsep\) \* \\real\{(0\.\d+)\}\}'

        matches = list(re.finditer(col_pattern, table_text))
        if not matches:
            return table_text

        tabcolsep = matches[0].group(1)
        num_cols = len(matches)

        # Check if this table has "Short" and "Long" headers (CLI argument tables)
        if 'Short' in table_text and 'Long' in table_text:
            # CLI argument table
            if num_cols == 5:
                # Check for very long options like --calculate-surge
                if '--calculate-surge' in table_text:
                    # Need extra space for long options
                    new_widths = ['0.16', '0.07', '0.22', '0.10', '0.35']
                else:
                    new_widths = ['0.19', '0.08', '0.18', '0.12', '0.33']
            elif num_cols == 4:
                new_widths = ['0.25', '0.09', '0.22', '0.44']
            else:
                return table_text

        # Check for tables with very long column names
        elif 'Keringstoestand' in table_text or '[open/gesloten]' in table_text:
            # Input file format table with long Dutch column names
            if num_cols == 4:
                # Column, Description, Unit, Required
                # Column has long names like "Keringstoestand[open/gesloten]"
                # Required has "Only with --calculate-surge"
                new_widths = ['0.28', '0.30', '0.12', '0.30']
            else:
                return table_text

        # Check for tables with column headers but not the special cases above
        elif 'Column' in table_text and 'Description' in table_text:
            # Generic column/description table
            if num_cols == 4:
                new_widths = ['0.25', '0.35', '0.15', '0.25']
            else:
                return table_text
        else:
            # Don't modify tables we don't recognize
            return table_text

        # Replace each column width
        result = table_text
        for i, match in enumerate(matches):
            if i < len(new_widths):
                old_spec = match.group(0)
                new_spec = f'>{{\\raggedright\\arraybackslash}}p{{(\\linewidth - {tabcolsep}\\tabcolsep) * \\real{{{new_widths[i]}}}}}'
                result = result.replace(old_spec, new_spec, 1)

        return result

    # Process all longtables
    result = re.sub(longtable_pattern, lambda m: fix_single_table(m.group(0)), content, flags=re.DOTALL)

    return result


def wrap_long_words_in_tables(content: str) -> str:
    """Wrap very long words in table cells with seqsplit for automatic breaking.

    This prevents long words from overflowing table columns by allowing them
    to break at any character position.

    Args:
        content: LaTeX content string

    Returns:
        Content with long words wrapped in seqsplit
    """
    import re

    # Find all longtable environments
    longtable_pattern = r'(\\begin\{longtable\}.*?\\end\{longtable\})'

    def wrap_long_words_in_table(table_text):
        """Wrap long words in a single table."""

        # Pattern to find table cell content (between & and \\ or &)
        # This is a simplified approach - wrap text in curly braces that looks problematic

        # Find long words (>15 characters without spaces) that aren't already in commands
        # Exclude content already in \lstinline, \passthrough, math mode, etc.
        def wrap_word(match):
            word = match.group(0)
            # Don't wrap if already in a command or if it's a LaTeX command itself
            return f'\\seqsplit{{{word}}}'

        # Pattern: words with brackets like "Keringstoestand[open/gesloten]"
        # or long words without spaces (>20 chars)
        result = table_text

        # Wrap long column names with brackets (like "Keringstoestand[open/gesloten]")
        # Match pattern: word followed by [text] where total length > 20
        bracket_pattern = r'([A-Za-z]{10,})\{?\[([^\]]+)\]\}?'

        def wrap_bracket_text(match):
            # Check if already wrapped or in a command
            before_match = result[max(0, match.start()-20):match.start()]
            if '\\seqsplit' in before_match or '\\passthrough' in before_match:
                return match.group(0)

            word = match.group(1)
            bracket_content = match.group(2)
            # Return wrapped version
            return f'\\seqsplit{{{word}[{bracket_content}]}}'

        result = re.sub(bracket_pattern, wrap_bracket_text, result)

        return result

    # Process all longtables
    result = re.sub(longtable_pattern, lambda m: wrap_long_words_in_table(m.group(0)), content, flags=re.DOTALL)

    return result



def convert_markdown_to_latex(
    input_file: Path,
    output_file: Path,
    template: Path | None = None,
    standalone: bool = False
) -> bool:
    """Convert a Markdown file to LaTeX using Pandoc.

    Args:
        input_file: Path to input Markdown file
        output_file: Path to output LaTeX file
        template: Optional custom Pandoc template
        standalone: If True, generate a complete LaTeX document.
                   If False, generate a fragment that can be included.

    Returns:
        True if conversion succeeded, False otherwise
    """
    cmd = [
        'pandoc',
        str(input_file),
        '-o', str(output_file),
        '--from', 'markdown',
        '--to', 'latex',
    ]

    # Add options
    if standalone:
        cmd.append('--standalone')

    if template:
        cmd.extend(['--template', str(template)])

    # Add some useful options for better LaTeX output
    cmd.extend([
        '--listings',  # Use listings package for code blocks
        '--number-sections',  # Number sections
    ])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Post-process the generated LaTeX file to replace UTF-8 characters
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace UTF-8 box-drawing characters with ASCII
            content = replace_utf8_tree_chars(content)

            # Fix table column widths for better formatting
            content = fix_table_column_widths(content)

            # Wrap long words in tables to enable automatic breaking
            content = wrap_long_words_in_tables(content)

            # If not standalone mode, add necessary commands at the beginning
            if not standalone:
                preamble = (
                    "% Pandoc compatibility commands\n"
                    "\\providecommand{\\tightlist}{%\n"
                    "  \\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}%\n"
                    "}\n"
                    "\\providecommand{\\passthrough}[1]{#1}\n\n"
                )
                content = preamble + content

            # Write back the modified content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"  Warning: Could not post-process {output_file.name}: {e}")

        print(f"OK Converted: {input_file.name} -> {output_file.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR converting {input_file.name}:")
        print(f"  {e.stderr}")
        return False


def convert_all_markdown_files(
    input_dir: Path,
    output_dir: Path,
    template: Path | None = None,
    standalone: bool = False,
    pattern: str = "*.md"
) -> tuple[int, int]:
    """Convert all Markdown files in a directory to LaTeX.

    Args:
        input_dir: Directory containing Markdown files
        output_dir: Directory for output LaTeX files
        template: Optional custom Pandoc template
        standalone: If True, generate complete LaTeX documents
        pattern: Glob pattern for matching files (default: "*.md")

    Returns:
        Tuple of (successful_conversions, total_files)
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all markdown files
    md_files = list(input_dir.glob(pattern))

    if not md_files:
        print(f"No markdown files found in {input_dir}")
        return 0, 0

    print(f"Found {len(md_files)} markdown file(s) to convert")
    print()

    # Convert each file
    success_count = 0
    for md_file in md_files:
        # Generate output filename
        tex_file = output_dir / f"{md_file.stem}.tex"

        if convert_markdown_to_latex(md_file, tex_file, template, standalone):
            success_count += 1

    return success_count, len(md_files)


def create_parser():
    parser = argparse.ArgumentParser(
        description='Convert Markdown documentation to LaTeX format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all markdown files in user_docs
  python scripts/markdown_to_latex.py
  
  # Convert with custom input/output directories
  python scripts/markdown_to_latex.py --input docs/mkdocs/guides --output docs/latex/guides
  
  # Generate standalone LaTeX documents
  python scripts/markdown_to_latex.py --standalone
  
  # Use a custom template
  python scripts/markdown_to_latex.py --template my_template.tex
        """
    )
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('docs/mkdocs/user_docs'),
        help='Input directory with Markdown files (default: docs/mkdocs/user_docs)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('docs/latex/user_docs'),
        help='Output directory for LaTeX files (default: docs/latex/user_docs)'
    )
    parser.add_argument(
        '--template',
        type=Path,
        help='Custom Pandoc LaTeX template'
    )
    parser.add_argument(
        '--standalone',
        action='store_true',
        help='Generate standalone LaTeX documents (vs. fragments for inclusion)'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        default='*.md',
        help='Glob pattern for matching files (default: *.md)'
    )
    return parser


def converter():
    """Main entry point for the script."""
    parser = create_parser()
    args = parser.parse_args()

    # Check if Pandoc is installed
    if not check_pandoc_installed():
        print("Error: Pandoc is not installed or not in PATH")
        print("Please install Pandoc: https://pandoc.org/installing.html")
        print()
        print("On Ubuntu/Debian: sudo apt-get install pandoc")
        print("On macOS: brew install pandoc")
        print("On Windows: choco install pandoc (or download from website)")
        return 1

    # Check if input directory exists
    if not args.input.exists():
        print(f"Error: Input directory not found: {args.input}")
        return 1

    if not args.input.is_dir():
        print(f"Error: Input path is not a directory: {args.input}")
        return 1

    # Check template if provided
    if args.template and not args.template.exists():
        print(f"Error: Template file not found: {args.template}")
        return 1

    print(f"Converting Markdown to LaTeX")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    if args.template:
        print(f"Template: {args.template}")
    print()

    # Convert files
    success_count, total_count = convert_all_markdown_files(
        args.input,
        args.output,
        args.template,
        args.standalone,
        args.pattern
    )

    print()
    print(f"Conversion complete: {success_count}/{total_count} files converted successfully")

    if success_count < total_count:
        print(f"Warning: {total_count - success_count} file(s) failed to convert")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(converter())

