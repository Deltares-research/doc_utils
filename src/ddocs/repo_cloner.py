import tempfile
import shutil
from pathlib import Path
from typing import Optional
from git import Repo


class RepoCloner:
    """Class to clone a git repository into a temporary directory and manage file operations."""

    def __init__(self, repo_url: str):
        """
        Initialize the RepoCloner with a repository URL.

        Args:
            repo_url: The URL of the git repository to clone
        """
        self.repo_url = repo_url
        self.temp_dir: Optional[Path] = None
        self.repo_path: Optional[Path] = None
        self.repo: Optional[Repo] = None

    def clone(self) -> Path:
        """
        Clone the repository into a temporary directory.

        Returns:
            Path to the cloned repository

        Raises:
            git.GitCommandError: If git clone fails
        """
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.mkdtemp())

        repo_name = self.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        self.repo_path = self.temp_dir / repo_name

        self.repo = Repo.clone_from(self.repo_url, str(self.repo_path))

        return self.repo_path

    def move_file(self, source_rel_path: str | Path, destination: str | Path) -> Path:
        """
        Move a file from the cloned repository to a new location.

        Args:
            source_rel_path: Relative path to the file within the cloned repository
            destination: Destination path (can be absolute or relative)

        Returns:
            Path to the moved file

        Raises:
            FileNotFoundError: If source file doesn't exist
            RuntimeError: If repository hasn't been cloned yet
        """
        if self.repo_path is None:
            raise RuntimeError("Repository not cloned yet. Call clone() first.")

        source = self.repo_path / source_rel_path
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        destination = Path(destination)

        # Create parent directories if they don't exist
        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(source), str(destination))
        return destination

    def copy_file(self, source_rel_path: str | Path, destination: str | Path) -> Path:
        """
        Copy a file from the cloned repository to a new location.

        Args:
            source_rel_path: Relative path to the file within the cloned repository
            destination: Destination path (can be absolute or relative)

        Returns:
            Path to the copied file

        Raises:
            FileNotFoundError: If source file doesn't exist
            RuntimeError: If repository hasn't been cloned yet
        """
        if self.repo_path is None:
            raise RuntimeError("Repository not cloned yet. Call clone() first.")

        source = self.repo_path / source_rel_path
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        destination = Path(destination)

        # Create parent directories if they don't exist
        destination.parent.mkdir(parents=True, exist_ok=True)

        if source.is_dir():
            shutil.copytree(str(source), str(destination), dirs_exist_ok=True)
        else:
            shutil.copy2(str(source), str(destination))

        return destination

    def list_files(self, relative_path: str = "", pattern: str = "*") -> list[Path]:
        """
        List files in the cloned repository.

        Args:
            relative_path: Relative path within the repository to list files from
            pattern: Glob pattern to filter files (default: "*")

        Returns:
            List of Path objects matching the pattern

        Raises:
            RuntimeError: If repository hasn't been cloned yet
        """
        if self.repo_path is None:
            raise RuntimeError("Repository not cloned yet. Call clone() first.")

        search_path = self.repo_path / relative_path
        if not search_path.exists():
            return []

        return list(search_path.glob(pattern))

    def cleanup(self):
        """Remove the temporary directory and all its contents."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            self.repo_path = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temporary directory."""
        self.cleanup()
        return False
