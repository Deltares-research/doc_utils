import os
import sys
from pathlib import Path


def is_macos():
    return os.name == "posix" and sys.platform == "darwin"


def is_linux():
    return os.name == "posix" and sys.platform.startswith("linux")


def assert_files_are_equal(result_path: Path, reference_path: Path):
    """Assert that two files are equal."""
    with open(result_path, 'r') as result_file, open(
            reference_path, 'r'
    ) as reference_file:
        assert result_file.read() == reference_file.read()