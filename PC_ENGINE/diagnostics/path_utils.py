from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_config_path(value: str | Path, *, base_dir: Path | None = None) -> Path:
    """Resolve configured filesystem paths consistently from the repository root."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (base_dir or REPO_ROOT) / path
