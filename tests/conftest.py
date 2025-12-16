import pytest
from pathlib import Path


@pytest.fixture
def reference_dir():
    return Path("tests/data/reference")

@pytest.fixture
def reference_files(reference_dir):
    return reference_dir.rglob("*.tex")