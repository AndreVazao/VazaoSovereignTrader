from __future__ import annotations

import json

from PC_ENGINE.core.paper_confluence_tracker import PaperConfluenceTracker


def main() -> None:
    tracker = PaperConfluenceTracker()
    print(json.dumps(tracker.summary(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
