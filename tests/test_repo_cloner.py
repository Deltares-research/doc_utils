import pytest
from ddocs.repo_cloner import RepoCloner

HTTPS = "https://github.com/Deltares/LatexInstallation"


class TestResolveCloneUrl:
    """Unit tests for RepoCloner credential -> clone-URL resolution."""

    @pytest.mark.unit
    def test_token_is_injected_into_https_url(self):
        cloner = RepoCloner(HTTPS, token="ghp_secret")
        assert cloner._resolve_clone_url() == (
            "https://x-access-token:ghp_secret@github.com/Deltares/LatexInstallation"
        )

    @pytest.mark.unit
    def test_username_password_used_when_no_token(self):
        cloner = RepoCloner(HTTPS, username="alice", password="pw", prefer_ssh=False)
        assert cloner._resolve_clone_url() == (
            "https://alice:pw@github.com/Deltares/LatexInstallation"
        )

    @pytest.mark.unit
    def test_prefers_ssh_when_no_credentials(self):
        cloner = RepoCloner(HTTPS, prefer_ssh=True)
        assert cloner._resolve_clone_url() == "git@github.com:Deltares/LatexInstallation.git"

    @pytest.mark.unit
    def test_anonymous_https_when_ssh_not_preferred_and_no_credentials(self):
        cloner = RepoCloner(HTTPS, prefer_ssh=False)
        assert cloner._resolve_clone_url() == HTTPS

    @pytest.mark.unit
    def test_existing_ssh_url_passed_through_untouched(self):
        ssh = "git@github.com:Deltares/LatexInstallation.git"
        cloner = RepoCloner(ssh, token="ghp_secret")
        assert cloner._resolve_clone_url() == ssh

    @pytest.mark.unit
    def test_token_read_from_env(self, monkeypatch):
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        cloner = RepoCloner(HTTPS)
        assert "env_token" in cloner._resolve_clone_url()

    @pytest.mark.unit
    def test_legacy_svn_env_still_accepted(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        monkeypatch.delenv("GIT_USERNAME", raising=False)
        monkeypatch.delenv("GIT_PASSWORD", raising=False)
        monkeypatch.setenv("SVN_USERNAME", "alice")
        monkeypatch.setenv("SVN_PASSWORD", "legacy")
        cloner = RepoCloner(HTTPS, prefer_ssh=False)
        assert cloner._resolve_clone_url() == "https://alice:legacy@github.com/Deltares/LatexInstallation"

    @pytest.mark.unit
    def test_scrub_secrets_masks_token_and_password(self):
        cloner = RepoCloner(HTTPS, token="ghp_secret", password="pw")
        scrubbed = cloner._scrub_secrets("fatal: ghp_secret and pw rejected")
        assert "ghp_secret" not in scrubbed
        assert "pw" not in scrubbed
        assert "***" in scrubbed
