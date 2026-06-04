from pathlib import Path
import shutil
from tests.utils import assert_files_are_equal
from ddocs.markdown import convert_all_markdown_files


def test_markdown(reference_files: list[Path]):
    input_files = Path("tests/data/md_files")
    output_dir = Path("tests/data/output")
    standalone = False
    result = convert_all_markdown_files(input_files, output_dir, standalone=standalone)
    assert result == (2, 2)
    assert output_dir.exists()
    output_files = list(output_dir.rglob("*.tex"))
    assert  len(output_files) == 2

    for ref_file in reference_files:
        file = output_dir / ref_file.name
        assert_files_are_equal(file, ref_file)

    shutil.rmtree(output_dir, ignore_errors=True)
