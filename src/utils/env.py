"""
Minimal .env file loader — no external dependencies.

Loads ``KEY=VALUE`` pairs from a ``.env`` file at the project root.
Uses simple line-by-line parsing (no regex) for maximum compatibility.

Supports:
  - Comments (``# ...``)
  - Quoted values (``KEY="value"`` or ``KEY='value'``)
  - Inline comments for unquoted values (``KEY=value # comment``)
  - Empty lines
  - Whitespace trimming

Usage::

    from src.utils.env import load_env

    load_env()                          # loads .env from project root
    db_host = os.getenv("DB_HOST", "127.0.0.1")
"""

import os
from pathlib import Path


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (where .env should live)."""
    return Path(__file__).resolve().parent.parent.parent


def load_env(env_path: str = ".env") -> bool:
    """Load variables from a .env file into ``os.environ``.

    Args:
        env_path: Path to .env file (relative to project root, or absolute).

    Returns:
        True if the file was found and loaded, False otherwise.
    """
    project_root = _find_project_root()
    full_path = Path(env_path)
    if not full_path.is_absolute():
        full_path = project_root / env_path

    if not full_path.exists():
        return False

    content = full_path.read_text(encoding="utf-8")
    count = 0

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and full-line comments
        if not line or line.startswith("#"):
            continue

        # Must contain '='
        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        # Handle quoted values
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        else:
            # Strip inline comment from unquoted values
            # Find ' #' that's not inside quotes (already handled above)
            comment_pos = _find_unquoted_hash(value)
            if comment_pos >= 0:
                value = value[:comment_pos].strip()

        os.environ[key] = value
        count += 1

    return count > 0


def _find_unquoted_hash(text: str) -> int:
    """Find the first '#' that is not inside single or double quotes."""
    in_single = False
    in_double = False
    for i, ch in enumerate(text):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return i
    return -1
