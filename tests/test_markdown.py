from pathlib import Path
from ddocs.markdown import convert_all_markdown_files

def test_markdown():
    input_files = Path("tests/data/md_files")
    output_files = Path("tests/data/output")
    template = Path("src/ddocs/data/deltares_fragment_template.tex")
    standalone = False
    result = convert_all_markdown_files(input_files, output_files, template, standalone)

