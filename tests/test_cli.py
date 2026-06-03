"""Unit tests for the ddocs CLI parser and dispatch, focused on get-tex-template."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from ddocs.cli import create_parser, main


class TestGetTexTemplateParser:
    """Tests for parsing the get-tex-template subcommand arguments."""

    @pytest.mark.unit
    def test_parses_all_auth_options(self):
        """Test the parser captures output-dir and every auth flag.

        Test scenario:
            All flags supplied -> namespace carries output_dir, token, username,
            password and no_ssh.
        """
        args = create_parser().parse_args([
            "get-tex-template", "-o", "out",
            "--token", "tok", "--username", "alice", "--password", "pw", "--no-ssh",
        ])
        assert args.command == "get-tex-template", f"unexpected command: {args.command}"
        assert args.output_dir == Path("out"), f"unexpected output_dir: {args.output_dir}"
        assert args.token == "tok", f"unexpected token: {args.token}"
        assert args.username == "alice", f"unexpected username: {args.username}"
        assert args.password == "pw", f"unexpected password: {args.password}"
        assert args.no_ssh is True, "no_ssh should be True when --no-ssh is given"

    @pytest.mark.unit
    def test_auth_options_default_to_none_and_no_ssh_false(self):
        """Test auth flags default to None and --no-ssh defaults to False.

        Test scenario:
            Only the required output-dir is given.
        """
        args = create_parser().parse_args(["get-tex-template", "-o", "out"])
        assert args.token is None, f"token should default None, got {args.token}"
        assert args.username is None, f"username should default None, got {args.username}"
        assert args.password is None, f"password should default None, got {args.password}"
        assert args.no_ssh is False, "no_ssh should default to False"

    @pytest.mark.unit
    def test_missing_output_dir_is_an_error(self):
        """Test omitting the required --output-dir aborts with SystemExit.

        Test scenario:
            argparse rejects the missing required option (exit code 2).
        """
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["get-tex-template"])
        assert exc_info.value.code == 2, f"argparse should exit 2, got {exc_info.value.code}"


class TestMainDispatch:
    """Tests for main() dispatching get-tex-template to clone_repo_cli."""

    @pytest.mark.unit
    def test_forwards_auth_args_and_returns_exit_code(self, monkeypatch):
        """Test main() forwards every auth arg to clone_repo_cli and returns its code.

        Test scenario:
            With all flags set, clone_repo_cli receives the output dir plus token,
            username, password and prefer_ssh=False (because --no-ssh).
        """
        monkeypatch.setattr(sys, "argv", [
            "ddocs", "get-tex-template", "-o", "out",
            "--token", "tok", "--username", "alice", "--password", "pw", "--no-ssh",
        ])
        with patch("ddocs.cli.clone_repo_cli", return_value=0) as mock_cli:
            code = main()
        assert code == 0, f"main should return clone_repo_cli's code, got {code}"
        mock_cli.assert_called_once_with(
            Path("out"), token="tok", username="alice", password="pw", prefer_ssh=False,
        )

    @pytest.mark.unit
    def test_defaults_prefer_ssh_true_and_no_creds(self, monkeypatch):
        """Test main() defaults to prefer_ssh=True and no credentials.

        Test scenario:
            Only output-dir given -> clone_repo_cli called with None creds and
            prefer_ssh True.
        """
        monkeypatch.setattr(sys, "argv", ["ddocs", "get-tex-template", "-o", "out"])
        with patch("ddocs.cli.clone_repo_cli", return_value=0) as mock_cli:
            main()
        mock_cli.assert_called_once_with(
            Path("out"), token=None, username=None, password=None, prefer_ssh=True,
        )

    @pytest.mark.unit
    def test_propagates_nonzero_exit_code(self, monkeypatch):
        """Test main() returns a non-zero code from clone_repo_cli unchanged.

        Test scenario:
            clone_repo_cli returns 1 -> main returns 1.
        """
        monkeypatch.setattr(sys, "argv", ["ddocs", "get-tex-template", "-o", "out"])
        with patch("ddocs.cli.clone_repo_cli", return_value=1):
            assert main() == 1, "main should propagate a non-zero exit code"
