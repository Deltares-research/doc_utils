# RepoCloner & Authentication

This guide explains the `ddocs.repo_cloner` module: what it does, how it authenticates against the
**private** Deltares LaTeX template repository, and exactly which token to create (and with which
permissions) so the `ddocs get-tex-template` command works both in CI and on a developer laptop.

For the auto-generated API reference, see [`ddocs.repo_cloner`](../reference/repo_cloner.md).

## What the module does

`repo_cloner.py` clones a git repository into a temporary directory and copies files out of it. It
backs the `ddocs get-tex-template` command, which fetches the Deltares LaTeX templates from the
private repository `https://github.com/Deltares/LatexInstallation`:

```bash
ddocs get-tex-template --output-dir ./templates
```

Under the hood this:

1. Creates `RepoCloner("https://github.com/Deltares/LatexInstallation")`.
2. Clones the repo into a temporary directory (authenticating as described below).
3. Copies three template sub-trees into `--output-dir`:
   - `MiKTeX/tex/latex/deltares`
   - `MiKTeX/tex/latex/nomentbl/deltares`
   - `MiKTeX/bibtex/bst/deltares`
4. Removes the temporary clone (the `RepoCloner` is used as a context manager).

Because `LatexInstallation` is **private**, the clone needs credentials — anonymous HTTPS will fail.

## The `RepoCloner` class

```python
RepoCloner(
    repo_url: str,
    token: str | None = None,
    username: str | None = None,
    password: str | None = None,
    prefer_ssh: bool = True,
)
```

Key methods:

| Method | Purpose |
| --- | --- |
| `clone()` | Clone the repo into a temp dir; returns the clone path. Raises a **scrubbed** `RuntimeError` on failure. |
| `copy_file(src, dest)` | Copy a file/dir out of the clone (creates parent dirs). |
| `move_file(src, dest)` | Move a file out of the clone. |
| `list_files(rel="", pattern="*")` | Glob files inside the clone. |
| `cleanup()` | Delete the temp dir. Runs automatically on context-manager exit. |

It supports the context-manager protocol, so the temp clone is always removed:

```python
from ddocs.repo_cloner import RepoCloner

with RepoCloner("https://github.com/Deltares/LatexInstallation") as cloner:
    cloner.clone()
    cloner.copy_file("MiKTeX/tex/latex/deltares", "./templates")
# temp dir cleaned up here
```

## How authentication is resolved

`RepoCloner` builds the effective clone URL from the first credential it finds, in this fixed order:

| Priority | Method | Trigger | Resulting clone URL |
| --- | --- | --- | --- |
| 1 | **Token** | `token=` arg, or `GITHUB_TOKEN` / `GH_TOKEN` env | `https://x-access-token:<token>@github.com/owner/repo` |
| 2 | **Basic auth** | `username=` + `password=` args, or `GIT_USERNAME` + `GIT_PASSWORD` env | `https://<user>:<password>@github.com/owner/repo` |
| 3 | **SSH** | `prefer_ssh=True` (default) **and** no token/basic-auth available | `git@github.com:owner/repo.git` (uses your SSH key) |
| 4 | **Anonymous** | `prefer_ssh=False` and no credentials | the HTTPS URL unchanged (public repos only) |

A URL that is already in SSH form (`git@…` or `ssh://…`) is always used as-is, regardless of any token.

> **Why this order works everywhere:** a laptop usually has **no** token in its environment, so it
> falls through to **SSH** and reuses the developer's existing key. CI sets a **token** secret, so it
> takes the token branch. The same code authenticates correctly in both places with no flags.

## Passing credentials to the CLI

The `ddocs get-tex-template` command exposes the same authentication directly as flags:

| Flag | Method | Falls back to |
| --- | --- | --- |
| `--token <token>` | Token (HTTPS) | `GITHUB_TOKEN` / `GH_TOKEN` env when omitted |
| `--username <user>` | Basic auth username | `GIT_USERNAME` env when omitted |
| `--password <token>` | Basic auth password/token | `GIT_PASSWORD` env when omitted |
| `--no-ssh` | Disables the SSH fallback (clone anonymously when no credentials are given) | — |

A flag overrides the corresponding environment variable. When neither a flag nor an env var supplies
credentials, the command falls back to your **SSH key** (unless `--no-ssh` is passed). The resolution
order is the same as above: token → username/password → SSH → anonymous.

```bash
# Token
ddocs get-tex-template --output-dir ./templates --token <token>

# Username + password (the password must be a token)
ddocs get-tex-template -o ./templates --username <user> --password <token>

# Nothing provided -> uses your SSH key
ddocs get-tex-template -o ./templates

# Force an anonymous clone (no SSH fallback; only works for public repos)
ddocs get-tex-template -o ./templates --no-ssh
```

> ⚠️ **Avoid passing secrets on the command line in real use.** Values given via `--token` / `--password`
> can leak into your shell history and the process list. Prefer the environment variables
> (`GITHUB_TOKEN`, `GIT_PASSWORD`) or a `.env` file, or use your SSH key. The flags are convenient for
> one-off local runs.

## Which method should I use?

| Environment | Recommended method | Why |
| --- | --- | --- |
| **Developer laptop** | **SSH key** | Most devs already have an SSH key registered with GitHub — nothing to configure, no secrets to manage. |
| **CI / GitHub Actions** | **Token** (PAT / deploy key / App token) | CI runners have no SSH key; a token stored as a secret is the standard, simplest path. |

`username` + `password` basic auth is supported but **not recommended**: GitHub disabled account
passwords for git over HTTPS in 2021, so the "password" must actually be a token anyway — in which
case prefer the `token` method.

## Creating a token (CI)

Create the token under an account/identity that has **read access** to
`Deltares/LatexInstallation`, then store it as a CI secret.

### Option A — Fine-grained personal access token (recommended)

GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.

| Setting                               | Value                                                     |
|---------------------------------------|-----------------------------------------------------------|
| **Resource owner**                    | `Deltares` (the org that owns the repo)                   |
| **Repository access**                 | *Only select repositories* → `Deltares/LatexInstallation` |
| **Repository permissions → Contents** | **Read-only**                                             |
| **Repository permissions → Metadata** | **Read-only** (selected automatically)                    |
| **Expiration**                        | Set a sensible expiry (e.g. 90 days) and rotate           |

> Fine-grained tokens targeting an organisation repo may require **organisation approval** before they
> work. An org owner approves the token request under the org's PAT settings.

That is the **least-privilege** set: read-only `Contents` is all that is needed to clone and copy files.
Do **not** grant write, admin, workflow, or any other scopes.

### Option B — Classic personal access token

GitHub → **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token**.

Check exactly **one** top-level scope:

| Scope | Why |
| --- | --- |
| ✅ **`repo`** — *Full control of private repositories* | Required to clone a **private** repo. This single checkbox is all you need. |

Checking `repo` automatically includes its sub-scopes (you do not tick them individually):

- `repo:status`
- `repo_deployment`
- `public_repo`
- `repo:invite`
- `security_events`

Do **not** select anything else — no `workflow`, `admin:org`, `write:packages`, `gist`, `user`, etc.

**Why you can't go narrower:** classic tokens are coarse and have **no read-only scope** for
private-repo contents. The only finer option, `public_repo`, covers **public** repos only and will not
clone a private one — so `repo` is the minimum that works for `LatexInstallation`.

> ⚠️ The `repo` scope grants read **and write** to **all** of your private repositories, not just
> `LatexInstallation`. For least privilege, prefer the fine-grained token in **Option A**, which can be
> limited to a single repo with `Contents: Read-only`.

| Token type | Minimum to clone the private repo | Read-only? | Scoped to one repo? |
| --- | --- | --- | --- |
| **Classic** | `repo` | ❌ (includes write) | ❌ (all your private repos) |
| **Fine-grained** | `Contents: Read-only` | ✅ | ✅ |

### Option C — Deploy key or GitHub App (CI without a personal token)

- **Deploy key:** add an SSH public key as a read-only *Deploy key* on `LatexInstallation`, and load the
  matching private key into the CI runner's `ssh-agent`. The clone then uses the SSH URL.
- **GitHub App installation token:** install an App with `Contents: Read-only` on the repo and mint a
  short-lived installation token in the workflow. Good for org-wide automation.

> ⚠️ **The built-in Actions `GITHUB_TOKEN` is not enough.** It is scoped to the repository running the
> workflow, so it generally **cannot** clone a *different* private repo such as `LatexInstallation`. Use
> a fine-grained PAT (Option A), a deploy key, or an App token (Option C) stored as a secret.

## Configuring the token

The code reads the token from `GITHUB_TOKEN` (or `GH_TOKEN`). Expose your secret under that name.

### GitHub Actions

Store the token as a repository/organisation secret (e.g. `LATEX_REPO_TOKEN`) and map it to the env var:

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.LATEX_REPO_TOKEN }}

steps:
  - run: ddocs get-tex-template --output-dir ./templates
```

### Local shell (token)

=== "PowerShell"

    ```powershell
    $env:GITHUB_TOKEN = "ghp_your_token_here"
    ddocs get-tex-template --output-dir ./templates
    ```

=== "bash"

    ```bash
    export GITHUB_TOKEN="ghp_your_token_here"
    ddocs get-tex-template --output-dir ./templates
    ```

## Using an SSH key (laptop)

If you do **not** set a token, `RepoCloner` (with `prefer_ssh=True`, the default) converts the HTTPS URL
to its SSH form and clones with your SSH key — no extra configuration in `ddocs` is needed. You only need
a working SSH key on GitHub:

1. Generate a key (if you don't have one):
   ```bash
   ssh-keygen -t ed25519 -C "you@example.com"
   ```
2. Add the **public** key to GitHub → **Settings → SSH and GPG keys → New SSH key**.
3. Confirm access:
   ```bash
   ssh -T git@github.com
   ```

As long as your account can read `Deltares/LatexInstallation`, the clone will succeed.

## Environment variable reference

| Variable | Used for | Notes |
| --- | --- | --- |
| `GITHUB_TOKEN` | Token auth (priority 1) | Preferred. Injected as `x-access-token:<token>`. |
| `GH_TOKEN` | Token auth (priority 1) | Fallback if `GITHUB_TOKEN` is unset. |
| `GIT_USERNAME` | Basic auth username (priority 2) | Only used with `GIT_PASSWORD`. |
| `GIT_PASSWORD` | Basic auth password/token (priority 2) | GitHub requires this to be a token, not an account password. |

> The legacy `SVN_USERNAME` / `SVN_PASSWORD` variables are **no longer read** — that fallback was removed.

## Security notes

- **Errors are scrubbed.** If a clone fails, `RepoCloner` raises a `RuntimeError` whose message has any
  token/password replaced with `***`, so credentials never leak into logs or CI output.
- **Never commit a token.** Keep it in a CI secret or a local environment variable, not in code or config.
- **Least privilege & rotation.** Grant only `Contents: Read-only`, set an expiry, and rotate tokens.
- **Token-in-URL caveat.** Token-based HTTPS embeds the credential in the remote URL for the temporary
  clone; the temp directory is deleted on context-manager exit, but avoid printing resolved URLs.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Authentication failed for 'https://github.com/...'` | No usable token and the URL stayed HTTPS (e.g. `prefer_ssh=False` in CI) | Set `GITHUB_TOKEN` to a token with read access, or use SSH. |
| Clone works locally but fails in CI | CI is using the built-in `GITHUB_TOKEN`, which can't reach `LatexInstallation` | Use a fine-grained PAT / deploy key / App token (see Option C). |
| `Permission denied (publickey)` on a laptop | No SSH key registered with GitHub | Add your SSH key (see *Using an SSH key*). |
| Fine-grained token has no effect | Token not approved by the org, or `Contents` permission missing | Get org approval and grant `Contents: Read-only`. |
