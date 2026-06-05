# Deltares HMS Documentation utility package

## Running the tests

```bash
pytest
```

The suite includes **live** tests (marked `integration` / `e2e`) that clone the private
`Deltares/LatexInstallation` repository and build a PDF. They require network access and
credentials with read access to that repo — a token in `GITHUB_TOKEN` / `GH_TOKEN` (or
`LATEX_REPO_TOKEN` in a local `.env`, which `tests/conftest.py` bridges), or an SSH key.

To run only the fast, hermetic tests (no network, no credentials), deselect them:

```bash
pytest -m "not e2e and not integration"
```

Never commit your `.env` / token — `.env` is git-ignored.
