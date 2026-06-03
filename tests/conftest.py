import os
import pytest
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Load the project's .env (token, RUN_NETWORK_TESTS, ...) into the environment
# before tests collect, so credential lookups and skip markers see it. Existing
# environment variables take precedence (override=False).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# RepoCloner reads GITHUB_TOKEN/GH_TOKEN; allow the CI-style secret name
# LATEX_REPO_TOKEN (used in .env / CI) to satisfy it without duplicating the value.
if os.getenv("LATEX_REPO_TOKEN") and not (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")):
    os.environ["GITHUB_TOKEN"] = os.environ["LATEX_REPO_TOKEN"]


@pytest.fixture
def reference_dir():
    return Path("tests/data/reference")

@pytest.fixture
def reference_files(reference_dir):
    return reference_dir.rglob("*.tex")

@pytest.fixture
def temp_latex_workspace():
    """Create a temporary workspace with LaTeX files for testing clean functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        
        # Create typical LaTeX project structure
        (workspace / "main.tex").write_text(r"""
\documentclass{article}
\begin{document}
\title{Test Document}
\maketitle
\section{Introduction}
This is a test document.
\end{document}
""")
        
        # Create chapter files
        chapters_dir = workspace / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "chapter1.tex").write_text(r"\section{Chapter 1}")
        (chapters_dir / "chapter2.tex").write_text(r"\section{Chapter 2}")
        
        # Create images directory
        images_dir = workspace / "images"
        images_dir.mkdir()
        (images_dir / "figure1.png").touch()  # Dummy image file
        
        yield workspace

@pytest.fixture
def temp_latex_build_files():
    """Create temporary directory with LaTeX build files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        build_dir = Path(temp_dir)
        
        # Create comprehensive set of LaTeX build files
        build_files = {
            # Main document build files
            'main.aux': 'LaTeX auxiliary file',
            'main.log': 'LaTeX log file',
            'main.toc': 'Table of contents',
            'main.lof': 'List of figures', 
            'main.lot': 'List of tables',
            'main.out': 'Hyperref outline',
            'main.bbl': 'Bibliography file',
            'main.blg': 'Bibliography log',
            
            # Index files
            'main.idx': 'Index file',
            'main.ilg': 'Index log',
            'main.ind': 'Index output',
            
            # LaTeXMk files
            'main.fdb_latexmk': 'LaTeXMk database',
            'main.fls': 'File list',
            
            # SyncTeX
            'main.synctex.gz': 'SyncTeX file',
            
            # Beamer presentation files
            'presentation.nav': 'Beamer navigation',
            'presentation.snm': 'Beamer slide notes', 
            'presentation.vrb': 'Beamer verbatim',
            
            # Other common extensions
            'document.xdy': 'xindy index style',
        }
        
        # Create the files
        for filename, description in build_files.items():
            file_path = build_dir / filename
            file_path.write_text(f"% {description}\n% This is a dummy {filename} file for testing")
        
        # Also create some source files that should NOT be removed
        source_files = [
            'main.tex', 'document.tex', 'styles.sty', 'config.cls',
            'data.csv', 'image.png', 'README.md'
        ]
        for filename in source_files:
            (build_dir / filename).touch()
        
        yield build_dir