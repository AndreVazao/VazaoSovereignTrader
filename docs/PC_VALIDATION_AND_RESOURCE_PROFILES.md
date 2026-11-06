# PC validation and resource profiles

## Runtime and development dependencies

The Windows runtime installer uses `requirements-pc.txt`. It intentionally does
not install pytest or other test-only tooling.

For development or local test execution, install
`requirements-dev.txt` into the PC_ENGINE virtual environment:

```powershell
.\PC_ENGINE\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Lightweight installation verification

Run:

```powershell
.\scripts\verify_pc_install.ps1
```

This checks first-party Python syntax, runtime imports, Playwright, and PAPER
safety. It excludes `.venv`, installed packages, and generated cache folders
from compilation. It does not run the full test suite by default.

To run one focused test module:

```powershell
.\scripts\verify_pc_install.ps1 -RunTests -TestPath tests\test_desktop_paper_surface.py
```

Run broader test groups separately and avoid endurance or full-suite runs while
the live market-data collector is active on low-memory PCs.

## PC Compact

Intended for machines with constrained memory (including systems with about
3 GB RAM). Keep the workload limited to public market-data collection, data
quality checks, observational radar, PAPER bookkeeping, persistence, and
health telemetry. Run focused tests when the collector is stopped. Do not run
endurance benchmarks concurrently with the runtime.

## PC Performance

For machines with more CPU and memory headroom. Enables additional strategy
workers, parallel analysis, simulations, and backtesting subject to explicit
resource limits. These workloads remain PAPER/research-only until separately
validated. Hardware detection must not silently enable REAL execution or
increase risk limits.

## Safety invariants

Both profiles must keep REAL execution disabled and automatic promotion to
REAL disabled. Market-data collection uses public/read-only endpoints and
does not require exchange private keys. Profile selection changes resource
allocation only; it does not change trading permissions.
