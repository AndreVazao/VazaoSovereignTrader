# State Outcome notes

The first implementation is intentionally conservative. It evaluates future MarketState prices by symbol/action/regime/horizon and subtracts a configurable round-trip cost. It is not a live execution signal and is not sufficient alone for REAL approval.

Future optimization: replace linear future-state scans with per-symbol timestamp indexes/bisect and retain individual observations for richer combination-level analysis.
