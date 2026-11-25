from __future__ import annotations

from pathlib import Path


def _recover_incomplete_tail(target: Path) -> int:
    """Discard only an unterminated trailing JSONL record.

    A process or machine interruption can leave the final append without its
    newline. Keeping that fragment would cause the next append to concatenate
    two records and make both unreadable. Complete newline-terminated records
    are preserved. The backwards scan uses fixed-size chunks.
    """
    if not target.exists():
        return 0

    with target.open("r+b") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        if size == 0:
            return 0

        handle.seek(-1, 2)
        if handle.read(1) == b"\n":
            return 0

        position = size
        chunk_size = 64 * 1024
        while position > 0:
            start = max(0, position - chunk_size)
            handle.seek(start)
            chunk = handle.read(position - start)
            newline = chunk.rfind(b"\n")
            if newline >= 0:
                recovered_size = start + newline + 1
                handle.truncate(recovered_size)
                return size - recovered_size
            position = start

        handle.truncate(0)
        return size


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
    Before appending, an unterminated trailing fragment from an interrupted
    prior write is truncated to the last complete newline-delimited record.
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
    if target.exists():
        _recover_incomplete_tail(target)
    if target.exists() and target.stat().st_size + len(encoded) > max_bytes:
        if previous.exists():
            previous.unlink()
        target.replace(previous)

    # Binary append keeps the byte cap exact across platforms/newline modes.
    with target.open("ab") as handle:
        handle.write(encoded)
    return True
