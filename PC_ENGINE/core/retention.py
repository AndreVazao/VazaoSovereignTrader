from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable


def retain_jsonl(
    path: str | Path,
    *,
    max_rows: int = 50_000,
    max_age_ms: int | None = None,
    timestamp_fields: tuple[str, ...] = ("timestamp_ms", "observed_ts_ms", "created_at_ms"),
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> int:
    """Compact a JSONL store, keeping only useful recent evidence.

    Invalid rows are discarded. Retention is bounded by both row count and
    optional age. The rewrite is atomic so a crash cannot leave a half-file.
    """
    target = Path(path)
    if not target.exists():
        return 0
    max_rows = max(1, int(max_rows))
    cutoff = int(time.time() * 1000) - int(max_age_ms) if max_age_ms is not None else None
    kept: list[dict[str, Any]] = []
    try:
        with target.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        continue
                    if validator is not None and not validator(row):
                        continue
                    if cutoff is not None:
                        ts = next((int(row.get(field, 0) or 0) for field in timestamp_fields if row.get(field)), 0)
                        if ts > 0 and ts < cutoff:
                            continue
                    kept.append(row)
                except (json.JSONDecodeError, TypeError, ValueError, OverflowError):
                    continue
    except OSError:
        return 0

    kept = kept[-max_rows:]
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            for row in kept:
                handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        tmp.replace(target)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
    return len(kept)
