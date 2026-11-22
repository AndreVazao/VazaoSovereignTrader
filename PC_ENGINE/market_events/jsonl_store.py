from __future__ import annotations

from pathlib import Path


def append_bounded_jsonl(
    output: str | Path,
    backup: str | Path,
    encoded_line: str,
    max_bytes: int,
) -> bool:
    """Append one JSONL line while bounding active + backup file sizes.

    The caller owns synchronization around this function. A record larger than
    the cap is rejected without changing either file. Existing symlinks are
    rejected so rotation cannot be redirected outside the configured data dir.
    """
    target = Path(output)
    previous = Path(backup)
    if not isinstance(encoded_line, str) or not encoded_line.endswith("\n"):
        raise ValueError("jsonl_record_must_end_with_newline")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes_must_be_positive_integer")
    if target == previous:
        raise ValueError("output_and_backup_must_differ")
    if target.is_symlink() or previous.is_symlink():
        raise OSError("jsonl_path_must_not_be_symlink")

    encoded = encoded_line.encode("utf-8")
    if len(encoded) > max_bytes:
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size + len(encoded) > max_bytes:
        if previous.exists():
            previous.unlink()
        target.replace(previous)

    # Binary append keeps the byte cap exact across platforms/newline modes.
    with target.open("ab") as handle:
        handle.write(encoded)
    return True
