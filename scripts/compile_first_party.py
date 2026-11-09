from __future__ import annotations

import py_compile
import sys
from pathlib import Path


EXCLUDED_DIRECTORY_NAMES = frozenset(
    {".venv", "venv", "__pycache__", ".git", "node_modules"}
)


def collect_first_party_python_files(root: str | Path) -> list[Path]:
    """Return project Python files while excluding environments and caches."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise NotADirectoryError(str(base))
    return sorted(
        path
        for path in base.rglob("*.py")
        if not any(part in EXCLUDED_DIRECTORY_NAMES for part in path.relative_to(base).parts)
    )


def compile_first_party(root: str | Path) -> int:
    files = collect_first_party_python_files(root)
    for path in files:
        py_compile.compile(str(path), doraise=True)
    print(f"Compiled {len(files)} first-party Python files.")
    return len(files)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python compile_first_party.py <source-root>", file=sys.stderr)
        return 2
    try:
        compile_first_party(args[0])
    except (OSError, py_compile.PyCompileError) as exc:
        print(f"First-party Python compile check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
