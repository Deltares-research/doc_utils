from unittest.mock import patch

import pytest
from git import GitCommandError

from ddocs.repo_cloner import RepoCloner

HTTPS = "https://github.com/Deltares/LatexInstallation"
SSH = "git@github.com:Deltares/LatexInstallation.git"


@pytest.fixture(autouse=True)
def _clear_auth_env(monkeypatch):
    """Clear all auth env vars so tests are isolated from the real environment.

    Test scenario:
        Every credential env var is removed before each test; individual tests
        opt back in via monkeypatch.setenv where they need it.
    """
    for var in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_USERNAME", "GIT_PASSWORD",
                "SVN_USERNAME", "SVN_PASSWORD"):
        monkeypatch.delenv(var, raising=False)


class TestInit:
    """Tests for RepoCloner.__init__ credential resolution and defaults."""

    @pytest.mark.unit
    def test_explicit_args_take_precedence_over_env(self, monkeypatch):
        """Test explicit constructor args win over environment variables.

        Test scenario:
            Both args and env are set; the args must be stored on the instance.
        """
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        monkeypatch.setenv("GIT_USERNAME", "env_user")
        monkeypatch.setenv("GIT_PASSWORD", "env_pw")
        cloner = RepoCloner(HTTPS, token="arg_token", username="arg_user", password="arg_pw")
        assert cloner.token == "arg_token", f"token should be the arg, got {cloner.token}"
        assert cloner.username == "arg_user", f"username should be the arg, got {cloner.username}"
        assert cloner.password == "arg_pw", f"password should be the arg, got {cloner.password}"

    @pytest.mark.unit
    def test_token_falls_back_to_github_token_env(self, monkeypatch):
        """Test token defaults to GITHUB_TOKEN when no arg is given.

        Test scenario:
            GITHUB_TOKEN is set, GH_TOKEN is not; token resolves to GITHUB_TOKEN.
        """
        monkeypatch.setenv("GITHUB_TOKEN", "gh_env")
        assert RepoCloner(HTTPS).token == "gh_env", "token should read GITHUB_TOKEN"

    @pytest.mark.unit
    def test_token_falls_back_to_gh_token_when_github_token_absent(self, monkeypatch):
        """Test token uses GH_TOKEN when GITHUB_TOKEN is unset.

        Test scenario:
            Only GH_TOKEN is set; token resolves to it.
        """
        monkeypatch.setenv("GH_TOKEN", "ghtok")
        assert RepoCloner(HTTPS).token == "ghtok", "token should read GH_TOKEN fallback"

    @pytest.mark.unit
    def test_username_password_fall_back_to_git_env(self, monkeypatch):
        """Test username/password default to GIT_USERNAME/GIT_PASSWORD.

        Test scenario:
            GIT_* vars are set; the instance stores them.
        """
        monkeypatch.setenv("GIT_USERNAME", "gituser")
        monkeypatch.setenv("GIT_PASSWORD", "gitpw")
        cloner = RepoCloner(HTTPS)
        assert cloner.username == "gituser", "username should read GIT_USERNAME"
        assert cloner.password == "gitpw", "password should read GIT_PASSWORD"

    @pytest.mark.unit
    def test_git_env_takes_precedence_over_legacy_svn_env(self, monkeypatch):
        """Test GIT_* env vars win over the legacy SVN_* ones.

        Test scenario:
            Both GIT_* and SVN_* are set; GIT_* values are used.
        """
        monkeypatch.setenv("GIT_USERNAME", "gituser")
        monkeypatch.setenv("GIT_PASSWORD", "gitpw")
        monkeypatch.setenv("SVN_USERNAME", "svnuser")
        monkeypatch.setenv("SVN_PASSWORD", "svnpw")
        cloner = RepoCloner(HTTPS)
        assert cloner.username == "gituser", "GIT_USERNAME should take precedence"
        assert cloner.password == "gitpw", "GIT_PASSWORD should take precedence"

    @pytest.mark.unit
    def test_defaults_are_none_and_prefer_ssh_true(self):
        """Test a bare construction has no credentials and prefers SSH.

        Test scenario:
            No args and no env -> token/username/password are None, prefer_ssh True.
        """
        cloner = RepoCloner(HTTPS)
        assert cloner.token is None, f"token should default None, got {cloner.token}"
        assert cloner.username is None, f"username should default None, got {cloner.username}"
        assert cloner.password is None, f"password should default None, got {cloner.password}"
        assert cloner.prefer_ssh is True, "prefer_ssh should default to True"


class TestResolveCloneUrl:
    """Unit tests for RepoCloner._resolve_clone_url credential -> URL resolution."""

    @pytest.mark.unit
    def test_token_is_injected_into_https_url(self):
        """Test a token is injected as x-access-token in the HTTPS URL."""
        cloner = RepoCloner(HTTPS, token="ghp_secret")
        assert cloner._resolve_clone_url() == (
            "https://x-access-token:ghp_secret@github.com/Deltares/LatexInstallation"
        ), "token must be embedded as x-access-token"

    @pytest.mark.unit
    def test_token_precedence_over_username_password(self):
        """Test token wins when both token and basic-auth creds are present."""
        cloner = RepoCloner(HTTPS, token="ghp_secret", username="alice", password="pw")
        assert "x-access-token:ghp_secret" in cloner._resolve_clone_url(), "token should take precedence"

    @pytest.mark.unit
    def test_username_password_used_when_no_token(self):
        """Test username+password are injected when no token is available."""
        cloner = RepoCloner(HTTPS, username="alice", password="pw", prefer_ssh=False)
        assert cloner._resolve_clone_url() == (
            "https://alice:pw@github.com/Deltares/LatexInstallation"
        ), "basic-auth creds must be embedded"

    @pytest.mark.unit
    def test_prefers_ssh_when_no_credentials(self):
        """Test resolution falls back to an SSH URL when no creds and prefer_ssh."""
        cloner = RepoCloner(HTTPS, prefer_ssh=True)
        assert cloner._resolve_clone_url() == SSH, "should convert to SSH URL"

    @pytest.mark.unit
    def test_username_without_password_falls_through_to_ssh(self):
        """Test a username with no password does not trigger basic auth.

        Test scenario:
            Only username is set; basic-auth branch requires both, so it falls
            through to SSH.
        """
        cloner = RepoCloner(HTTPS, username="alice", prefer_ssh=True)
        assert cloner._resolve_clone_url() == SSH, "incomplete basic auth should fall through to SSH"

    @pytest.mark.unit
    def test_anonymous_https_when_ssh_not_preferred_and_no_credentials(self):
        """Test the URL is returned unchanged for an anonymous clone."""
        cloner = RepoCloner(HTTPS, prefer_ssh=False)
        assert cloner._resolve_clone_url() == HTTPS, "anonymous clone should keep the HTTPS URL"

    @pytest.mark.unit
    def test_existing_ssh_url_passed_through_untouched(self):
        """Test an SSH input URL is used as-is even when a token is present."""
        cloner = RepoCloner(SSH, token="ghp_secret")
        assert cloner._resolve_clone_url() == SSH, "existing SSH URL must not be rewritten"

    @pytest.mark.unit
    def test_ssh_scheme_url_passed_through(self):
        """Test an ssh:// scheme URL is passed through untouched."""
        url = "ssh://git@github.com/Deltares/LatexInstallation.git"
        cloner = RepoCloner(url, token="ghp_secret")
        assert cloner._resolve_clone_url() == url, "ssh:// URL must not be rewritten"

    @pytest.mark.unit
    def test_trailing_slash_is_stripped_before_token_injection(self):
        """Test a trailing slash on the URL is removed before injecting a token."""
        cloner = RepoCloner(HTTPS + "/", token="ghp_secret")
        assert cloner._resolve_clone_url() == (
            "https://x-access-token:ghp_secret@github.com/Deltares/LatexInstallation"
        ), "trailing slash should be stripped"

    @pytest.mark.unit
    def test_token_read_from_env(self, monkeypatch):
        """Test the token env var flows through into the resolved URL."""
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        cloner = RepoCloner(HTTPS)
        assert "env_token" in cloner._resolve_clone_url(), "env token should appear in URL"

    @pytest.mark.unit
    def test_legacy_svn_env_still_accepted(self, monkeypatch):
        """Test the legacy SVN_* env vars still drive basic auth as a fallback."""
        monkeypatch.setenv("SVN_USERNAME", "alice")
        monkeypatch.setenv("SVN_PASSWORD", "legacy")
        cloner = RepoCloner(HTTPS, prefer_ssh=False)
        assert cloner._resolve_clone_url() == (
            "https://alice:legacy@github.com/Deltares/LatexInstallation"
        ), "legacy SVN_* creds should still work"


class TestToSshUrl:
    """Tests for the RepoCloner._to_ssh_url static helper."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "url, expected",
        [
            (HTTPS, SSH),
            (HTTPS + ".git", SSH),
            (HTTPS + "/", SSH),
            ("http://github.com/Deltares/LatexInstallation", SSH),
            (SSH, SSH),
            ("ssh://git@github.com/x/y.git", "ssh://git@github.com/x/y.git"),
        ],
    )
    def test_conversion_matrix(self, url, expected):
        """Test HTTPS/HTTP URLs convert to SSH and SSH URLs pass through.

        Args:
            url: Input URL in various forms.
            expected: Expected SSH-form (or unchanged) URL.

        Test scenario:
            Covers .git presence/absence, trailing slash, http scheme, and
            already-SSH inputs.
        """
        assert RepoCloner._to_ssh_url(url) == expected, f"{url} -> expected {expected}"


class TestScrubSecrets:
    """Tests for the RepoCloner._scrub_secrets helper."""

    @pytest.mark.unit
    def test_masks_token_and_password(self):
        """Test both token and password are replaced with ***."""
        cloner = RepoCloner(HTTPS, token="ghp_secret", password="pw")
        scrubbed = cloner._scrub_secrets("fatal: ghp_secret and pw rejected")
        assert "ghp_secret" not in scrubbed, "token must be masked"
        assert "pw" not in scrubbed, "password must be masked"
        assert "***" in scrubbed, "mask marker should be present"

    @pytest.mark.unit
    def test_masks_token_only_when_no_password(self):
        """Test only the token is masked when no password is set."""
        cloner = RepoCloner(HTTPS, token="ghp_secret")
        scrubbed = cloner._scrub_secrets("url https://x-access-token:ghp_secret@github.com")
        assert "ghp_secret" not in scrubbed, "token must be masked"
        assert "***" in scrubbed, "mask marker should be present"

    @pytest.mark.unit
    def test_returns_text_unchanged_when_no_secrets(self):
        """Test text is returned unchanged when there are no secrets to scrub."""
        cloner = RepoCloner(HTTPS)
        message = "fatal: repository not found"
        assert cloner._scrub_secrets(message) == message, "text without secrets is unchanged"


class TestCloneErrorScrubbing:
    """clone() must not leak credentials when the underlying git command fails."""

    @pytest.mark.unit
    def test_clone_failure_scrubs_token_from_error(self, tmp_path):
        """Test a failed clone raises a scrubbed RuntimeError, not the raw token.

        Test scenario:
            Repo.clone_from raises a GitCommandError whose text contains the token;
            clone() must re-raise a RuntimeError with the token masked.
        """
        cloner = RepoCloner(HTTPS, token="ghp_secret")
        cloner.temp_dir = tmp_path
        boom = GitCommandError("git clone https://x-access-token:ghp_secret@github.com/x", 128)
        with patch("ddocs.repo_cloner.Repo.clone_from", side_effect=boom):
            with pytest.raises(RuntimeError) as excinfo:
                cloner.clone()
        assert "ghp_secret" not in str(excinfo.value), "token must not appear in the error"
        assert "***" in str(excinfo.value), "masked marker should appear in the error"

    @pytest.mark.unit
    def test_clone_uses_resolved_url(self, tmp_path):
        """Test clone() passes the credential-resolved URL to Repo.clone_from.

        Test scenario:
            With a token set, the URL handed to Repo.clone_from carries the token.
        """
        cloner = RepoCloner(HTTPS, token="ghp_secret")
        cloner.temp_dir = tmp_path
        with patch("ddocs.repo_cloner.Repo.clone_from") as mock_clone:
            cloner.clone()
        called_url = mock_clone.call_args.args[0]
        assert called_url == (
            "https://x-access-token:ghp_secret@github.com/Deltares/LatexInstallation"
        ), f"clone should use the resolved URL, got {called_url}"


class TestCloneSuccessPath:
    """Tests for RepoCloner.clone() success-path behaviour."""

    @pytest.mark.unit
    def test_clone_auto_creates_temp_dir_when_missing(self, tmp_path, monkeypatch):
        """Test clone() creates a temp dir via mkdtemp when none is set.

        Test scenario:
            With temp_dir unset, mkdtemp supplies the directory and repo_path is
            ``<temp_dir>/<repo-name>``.
        """
        cloner = RepoCloner("https://github.com/owner/myrepo", prefer_ssh=False)
        monkeypatch.setattr("ddocs.repo_cloner.tempfile.mkdtemp", lambda: str(tmp_path))
        with patch("ddocs.repo_cloner.Repo.clone_from"):
            result = cloner.clone()
        assert cloner.temp_dir == tmp_path, f"temp_dir should be set, got {cloner.temp_dir}"
        assert result == tmp_path / "myrepo", f"repo_path should be <temp>/myrepo, got {result}"

    @pytest.mark.unit
    def test_clone_reuses_existing_temp_dir(self, tmp_path, monkeypatch):
        """Test clone() keeps a temp dir that is already set.

        Test scenario:
            temp_dir is pre-set; mkdtemp must not be called.
        """
        cloner = RepoCloner("https://github.com/owner/myrepo", prefer_ssh=False)
        cloner.temp_dir = tmp_path

        def _boom():
            raise AssertionError("mkdtemp should not be called when temp_dir is set")

        monkeypatch.setattr("ddocs.repo_cloner.tempfile.mkdtemp", _boom)
        with patch("ddocs.repo_cloner.Repo.clone_from"):
            cloner.clone()
        assert cloner.temp_dir == tmp_path, "existing temp_dir must be reused"

    @pytest.mark.unit
    def test_clone_strips_git_suffix_from_repo_name(self, tmp_path):
        """Test clone() derives the repo dir name without the .git suffix.

        Test scenario:
            A ``*.git`` URL yields a repo_path whose name drops ``.git``.
        """
        cloner = RepoCloner("https://github.com/owner/myrepo.git", prefer_ssh=False)
        cloner.temp_dir = tmp_path
        with patch("ddocs.repo_cloner.Repo.clone_from"):
            result = cloner.clone()
        assert result == tmp_path / "myrepo", f"repo name should drop .git, got {result.name}"

    @pytest.mark.unit
    def test_clone_returns_repo_path_and_sets_repo(self, tmp_path):
        """Test clone() stores the Repo object and returns the repo path.

        Test scenario:
            On success, ``self.repo`` is the clone_from result and the returned
            path equals ``self.repo_path``.
        """
        cloner = RepoCloner("https://github.com/owner/myrepo", prefer_ssh=False)
        cloner.temp_dir = tmp_path
        with patch("ddocs.repo_cloner.Repo.clone_from", return_value="REPO") as mock_clone:
            result = cloner.clone()
        assert cloner.repo == "REPO", f"repo should be the clone_from result, got {cloner.repo}"
        assert result == cloner.repo_path, "clone() should return self.repo_path"
        mock_clone.assert_called_once()
