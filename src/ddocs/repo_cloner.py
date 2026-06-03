import os
import re
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from git import Repo, GitCommandError


class RepoCloner:
    """Clone a git repository into a temporary directory and manage file operations.

    Authentication is resolved from the supplied arguments or the environment with a fixed
    precedence: token, then username+password, then SSH (when ``prefer_ssh`` is set), then an
    anonymous HTTPS clone. This lets the same code authenticate via a token in CI and via the
    developer's SSH key on a laptop.

    Examples:
        - Construct with a token and read back the stored credentials:
            ```python
            >>> from ddocs.repo_cloner import RepoCloner
            >>> cloner = RepoCloner("https://github.com/Deltares/LatexInstallation", token="ghp_demo")
            >>> cloner.token
            'ghp_demo'
            >>> cloner.repo_url
            'https://github.com/Deltares/LatexInstallation'

            ```
        - A token turns the public URL into an authenticated HTTPS clone URL:
            ```python
            >>> from ddocs.repo_cloner import RepoCloner
            >>> RepoCloner("https://github.com/Deltares/LatexInstallation", token="ghp_demo")._resolve_clone_url()
            'https://x-access-token:ghp_demo@github.com/Deltares/LatexInstallation'

            ```

    See Also:
        clone_repo_cli: Uses this class to fetch the Deltares LaTeX templates.
    """

    def __init__(
        self,
        repo_url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        prefer_ssh: bool = True,
    ):
        """Initialize the RepoCloner.

        Args:
            repo_url: The URL of the git repository to clone (HTTPS or SSH form).
            token: Personal access / app token for HTTPS auth. Defaults to the
                ``GITHUB_TOKEN`` or ``GH_TOKEN`` environment variable.
            username: Username for HTTPS basic auth. Defaults to ``GIT_USERNAME``
                or the legacy ``SVN_USERNAME`` environment variable.
            password: Password/token for HTTPS basic auth. Defaults to ``GIT_PASSWORD``
                or the legacy ``SVN_PASSWORD`` environment variable.
            prefer_ssh: When no token or username/password is available, clone via an
                SSH URL (using the machine's SSH key) instead of anonymously.

        Examples:
            - An explicit token is stored verbatim (it wins over any environment value):
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> cloner = RepoCloner("https://github.com/owner/repo", token="ghp_demo")
                >>> cloner.token
                'ghp_demo'
                >>> cloner.prefer_ssh
                True

                ```
            - Basic-auth credentials are stored for later HTTPS injection:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> cloner = RepoCloner("https://github.com/owner/repo", username="alice", password="pw")
                >>> (cloner.username, cloner.password)
                ('alice', 'pw')

                ```
        """
        self.repo_url = repo_url
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.username = username or os.getenv("GIT_USERNAME") or os.getenv("SVN_USERNAME")
        self.password = password or os.getenv("GIT_PASSWORD") or os.getenv("SVN_PASSWORD")
        self.prefer_ssh = prefer_ssh
        self.temp_dir: Optional[Path] = None
        self.repo_path: Optional[Path] = None
        self.repo: Optional[Repo] = None

    @staticmethod
    def _to_ssh_url(url: str) -> str:
        """Convert an HTTPS git URL to its ``git@host:owner/repo.git`` SSH form.

        URLs that are already SSH (``git@`` or ``ssh://``) are returned unchanged.

        Args:
            url: An HTTPS/HTTP or SSH git URL.

        Returns:
            The SSH-form URL, or ``url`` unchanged if it was already SSH.

        Examples:
            - An HTTPS URL is rewritten and given a ``.git`` suffix:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> RepoCloner._to_ssh_url("https://github.com/Deltares/LatexInstallation")
                'git@github.com:Deltares/LatexInstallation.git'

                ```
            - An already-SSH URL is returned untouched:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> RepoCloner._to_ssh_url("git@github.com:Deltares/LatexInstallation.git")
                'git@github.com:Deltares/LatexInstallation.git'

                ```
        """
        if url.startswith("git@") or url.startswith("ssh://"):
            ssh_url = url
        else:
            without_scheme = re.sub(r"^https?://", "", url.rstrip("/"))
            host, _, path = without_scheme.partition("/")
            if not path.endswith(".git"):
                path = f"{path}.git"
            ssh_url = f"git@{host}:{path}"
        return ssh_url

    def _resolve_clone_url(self) -> str:
        """Build the effective clone URL from the available credentials.

        Precedence: token, then username+password, then SSH (when ``prefer_ssh``),
        then an anonymous HTTPS clone. An input that is already an SSH URL is used as-is.

        Returns:
            The clone URL git should use, with any token/credentials embedded.

        Examples:
            - A token is embedded as an ``x-access-token`` HTTPS credential:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> RepoCloner("https://github.com/owner/repo", token="ghp_demo")._resolve_clone_url()
                'https://x-access-token:ghp_demo@github.com/owner/repo'

                ```
            - An SSH input URL is used as-is, even when a token is set:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> RepoCloner("git@github.com:owner/repo.git", token="ghp_demo")._resolve_clone_url()
                'git@github.com:owner/repo.git'

                ```
        """
        url = self.repo_url.rstrip("/")
        if url.startswith("git@") or url.startswith("ssh://"):
            clone_url = url
        elif self.token:
            clone_url = re.sub(r"^https://", f"https://x-access-token:{self.token}@", url, count=1)
        elif self.username and self.password:
            clone_url = re.sub(r"^https://", f"https://{self.username}:{self.password}@", url, count=1)
        elif self.prefer_ssh:
            clone_url = self._to_ssh_url(url)
        else:
            clone_url = url
        return clone_url

    def _scrub_secrets(self, text: str) -> str:
        """Replace any known secret (token/password) in ``text`` with ``***``.

        Args:
            text: Arbitrary text (e.g. a git error message) that may contain secrets.

        Returns:
            The text with every configured token/password occurrence masked.

        Examples:
            - A token embedded in an error message is masked:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> cloner = RepoCloner("https://github.com/owner/repo", token="ghp_demo")
                >>> cloner._scrub_secrets("fatal: auth failed for ghp_demo")
                'fatal: auth failed for ***'

                ```
            - Text without any secret is returned unchanged:
                ```python
                >>> from ddocs.repo_cloner import RepoCloner
                >>> cloner = RepoCloner("https://github.com/owner/repo", token="ghp_demo")
                >>> cloner._scrub_secrets("fatal: repository not found")
                'fatal: repository not found'

                ```
        """
        scrubbed = text
        for secret in (self.token, self.password):
            if secret:
                scrubbed = scrubbed.replace(secret, "***")
        return scrubbed

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

        # Build authenticated URL if credentials are provided
        clone_url = self.repo_url.rstrip('/')  # Remove trailing slash
        if self.username and self.password:
            # Insert credentials into HTTPS URL
            if clone_url.startswith('https://'):
                clone_url = clone_url.replace('https://', f'https://{self.username}:{self.password}@', 1)

        self.repo = Repo.clone_from(clone_url, str(self.repo_path))

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


def clone_repo_cli(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Cloning LatexInstallation repository...")
    cloner = RepoCloner("https://github.com/Deltares/LatexInstallation")
    cloner.clone()

    # Copy the template paths
    paths = [
        "MiKTeX/tex/latex/deltares",
        "MiKTeX/tex/latex/nomentbl/deltares",
        "MiKTeX/bibtex/bst/deltares"
    ]

    for path in paths:
        print(f"Copying {path}...")
        cloner.copy_file(path, output_dir)

    print(f"✓ Template files copied to {output_dir}")
    return 0
