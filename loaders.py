"""Credential check for account-gated sources.

Every external source is a typed function in its own module (flaring, forest,
matching, returns, ratings) that takes text/paths and returns plain data, so
tests feed it fixtures and synthetic data. Gated sources read credentials from
environment variables (a local, gitignored `.env`) and raise `MissingCredentials`.
"""

import os


class MissingCredentials(RuntimeError):
    """An account-gated source was used without its credentials set."""


def require_env(*names: str) -> tuple[str, ...]:
    """Values of the named env vars, or MissingCredentials listing the unset ones."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise MissingCredentials(
            "set %s (see 'Data you need to obtain' in README.md)"
            % ", ".join(missing))
    return tuple(os.environ[n] for n in names)
