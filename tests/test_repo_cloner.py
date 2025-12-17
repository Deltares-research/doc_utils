from ddocs.repo_cloner import clone_repo_cli
from pathlib import Path

def test_clone_repo():
    dest_dir = Path("tests/data/tex_data")
    clone_repo_cli(dest_dir)
