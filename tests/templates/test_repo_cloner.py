from unittest.mock import patch

import pytest
from git import GitCommandError

from ddocs.templates.repo_cloner import RepoCloner, clone_repo_cli

HTTPS = "https://github.com/Deltares/LatexInstallation"
SSH = "git@github.com:Deltares/LatexInstallation.git"


@pytest.fixture(autouse=True)
def _clear_auth_env(request, monkeypatch):
    """Clear all auth env vars so unit tests are isolated from the real environment.

    Test scenario:
        Every credential env var is removed before each test; individual tests
        opt back in via monkeypatch.setenv where they need it. The live
        ``integration`` test is exempt -- it needs the real token to clone.
    """
    if request.node.get_closest_marker("integration"):
        return
    for var in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_USERNAME", "GIT_PASSWORD",
                "SVN_USERNAME", "SVN_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    # SVN_* are cleared above only to keep the environment clean; the code no
    # longer reads them (the legacy fallback was removed).


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
    def test_legacy_svn_env_is_ignored(self, monkeypatch):
        """Test the legacy SVN_* env vars are no longer read.

        Test scenario:
            Only SVN_* are set; username/password stay None (the fallback was removed).
        """
        monkeypatch.setenv("SVN_USERNAME", "svnuser")
        monkeypatch.setenv("SVN_PASSWORD", "svnpw")
        cloner = RepoCloner(HTTPS)
        assert cloner.username is None, "SVN_USERNAME must not be read"
        assert cloner.password is None, "SVN_PASSWORD must not be read"

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
    def test_legacy_svn_env_does_not_authenticate(self, monkeypatch):
        """Test SVN_* env vars no longer affect the resolved URL.

        Test scenario:
            With only SVN_* set and prefer_ssh False, resolution ignores them and
            falls through to the anonymous HTTPS URL.
        """
        monkeypatch.setenv("SVN_USERNAME", "alice")
        monkeypatch.setenv("SVN_PASSWORD", "legacy")
        cloner = RepoCloner(HTTPS, prefer_ssh=False)
        assert cloner._resolve_clone_url() == HTTPS, "SVN_* must not inject basic-auth creds"


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
        with patch("ddocs.templates.repo_cloner.Repo.clone_from", side_effect=boom):
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
        with patch("ddocs.templates.repo_cloner.Repo.clone_from") as mock_clone:
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
        monkeypatch.setattr("ddocs.templates.repo_cloner.tempfile.mkdtemp", lambda: str(tmp_path))
        with patch("ddocs.templates.repo_cloner.Repo.clone_from"):
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

        monkeypatch.setattr("ddocs.templates.repo_cloner.tempfile.mkdtemp", _boom)
        with patch("ddocs.templates.repo_cloner.Repo.clone_from"):
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
        with patch("ddocs.templates.repo_cloner.Repo.clone_from"):
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
        with patch("ddocs.templates.repo_cloner.Repo.clone_from", return_value="REPO") as mock_clone:
            result = cloner.clone()
        assert cloner.repo == "REPO", f"repo should be the clone_from result, got {cloner.repo}"
        assert result == cloner.repo_path, "clone() should return self.repo_path"
        mock_clone.assert_called_once()


class TestCloneRepoCli:
    """Tests for the clone_repo_cli entry point."""

    @pytest.mark.unit
    def test_cli_copies_templates_and_cleans_up(self, tmp_path):
        """Test clone_repo_cli clones, copies three template paths, and cleans up.

        Test scenario:
            RepoCloner is replaced by a fake recording context-manager use; the CLI
            must enter/exit the manager (cleanup), clone once, copy 3 paths, return 0.
        """
        from ddocs.templates.repo_cloner import clone_repo_cli

        created = {}

        class FakeCloner:
            def __init__(self, url, **kwargs):
                created["url"] = url
                created["kwargs"] = kwargs

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                created["cleaned"] = True
                return False

            def clone(self):
                created["cloned"] = True
                return tmp_path

            def copy_file(self, src, dest):
                created.setdefault("copied", []).append(src)
                return dest

        with patch("ddocs.templates.repo_cloner.RepoCloner", FakeCloner):
            rc = clone_repo_cli(tmp_path / "out")

        assert rc == 0, f"clone_repo_cli should return 0, got {rc}"
        assert created["cloned"] is True, "clone() should have been called"
        assert created["cleaned"] is True, "context manager __exit__ (cleanup) should run"
        assert len(created["copied"]) == 3, f"should copy 3 template paths, got {created.get('copied')}"
        assert created["url"] == "https://github.com/Deltares/LatexInstallation", "wrong repo URL"

    @pytest.mark.unit
    def test_cli_passes_auth_through_to_repocloner(self, tmp_path):
        """Test clone_repo_cli forwards auth arguments to RepoCloner.

        Test scenario:
            token/username/password/prefer_ssh given to clone_repo_cli appear in the
            RepoCloner constructor call.
        """
        from ddocs.templates.repo_cloner import clone_repo_cli

        seen = {}

        class FakeCloner:
            def __init__(self, url, **kwargs):
                seen.update(kwargs)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def clone(self):
                return tmp_path

            def copy_file(self, src, dest):
                return dest

        with patch("ddocs.templates.repo_cloner.RepoCloner", FakeCloner):
            clone_repo_cli(
                tmp_path / "out",
                token="ghp_demo",
                username="alice",
                password="pw",
                prefer_ssh=False,
            )

        assert seen == {
            "token": "ghp_demo",
            "username": "alice",
            "password": "pw",
            "prefer_ssh": False,
        }, f"auth args should be forwarded to RepoCloner, got {seen}"

    @pytest.mark.unit
    def test_cli_defaults_prefer_ssh_and_no_creds(self, tmp_path):
        """Test clone_repo_cli defaults to no credentials and prefer_ssh=True.

        Test scenario:
            Called with only an output dir, RepoCloner receives token/username/password
            as None and prefer_ssh True (so SSH is the fallback).
        """
        from ddocs.templates.repo_cloner import clone_repo_cli

        seen = {}

        class FakeCloner:
            def __init__(self, url, **kwargs):
                seen.update(kwargs)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def clone(self):
                return tmp_path

            def copy_file(self, src, dest):
                return dest

        with patch("ddocs.templates.repo_cloner.RepoCloner", FakeCloner):
            clone_repo_cli(tmp_path / "out")

        assert seen == {
            "token": None,
            "username": None,
            "password": None,
            "prefer_ssh": True,
        }, f"defaults should be no creds + prefer_ssh, got {seen}"


class TestContextManager:
    """Tests for RepoCloner.cleanup and the context-manager protocol."""

    @pytest.mark.unit
    def test_cleanup_removes_temp_dir_and_resets_state(self, tmp_path):
        """Test cleanup() deletes the temp dir and clears tracked paths.

        Test scenario:
            With a populated temp dir, cleanup removes it and resets
            temp_dir/repo_path to None.
        """
        cloner = RepoCloner(HTTPS)
        work = tmp_path / "work"
        work.mkdir()
        (work / "file.txt").write_text("data", encoding="utf-8")
        cloner.temp_dir = work
        cloner.repo_path = work / "repo"
        cloner.cleanup()
        assert not work.exists(), "temp dir should be removed"
        assert cloner.temp_dir is None, "temp_dir should reset to None"
        assert cloner.repo_path is None, "repo_path should reset to None"

    @pytest.mark.unit
    def test_cleanup_is_noop_when_no_temp_dir(self):
        """Test cleanup() does nothing when no temp dir was created.

        Test scenario:
            A fresh cloner with temp_dir None can call cleanup without error.
        """
        cloner = RepoCloner(HTTPS)
        cloner.cleanup()
        assert cloner.temp_dir is None, "temp_dir should remain None"

    @pytest.mark.unit
    def test_enter_returns_self(self):
        """Test __enter__ returns the cloner instance for use in a with-block."""
        cloner = RepoCloner(HTTPS)
        with cloner as ctx:
            assert ctx is cloner, "context manager should yield the same instance"

    @pytest.mark.unit
    def test_exit_cleans_up_temp_dir(self, tmp_path):
        """Test leaving the with-block removes the temp dir.

        Test scenario:
            A temp dir set before the block is gone after it.
        """
        cloner = RepoCloner(HTTPS)
        work = tmp_path / "work"
        work.mkdir()
        cloner.temp_dir = work
        with cloner:
            pass
        assert not work.exists(), "exit should clean up the temp dir"
        assert cloner.temp_dir is None, "temp_dir should reset to None after exit"

    @pytest.mark.unit
    def test_exit_does_not_suppress_exceptions(self, tmp_path):
        """Test __exit__ returns False so exceptions propagate out of the block."""
        cloner = RepoCloner(HTTPS)
        work = tmp_path / "work"
        work.mkdir()
        cloner.temp_dir = work
        with pytest.raises(ValueError, match="boom"):
            with cloner:
                raise ValueError("boom")
        assert not work.exists(), "cleanup should still run when the block raises"


@pytest.mark.integration
def test_clone_repo_live(tmp_path):
    """Smoke-test a real clone of the Deltares LatexInstallation templates.

    Test scenario:
        Runs when a token is available. Performs a live authenticated clone and
        copies the template files into a temp dir, expecting a zero exit code.
    """
    assert clone_repo_cli(tmp_path / "templates") == 0, "live clone_repo_cli should return 0"
