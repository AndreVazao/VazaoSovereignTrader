# Desktop PAPER local bridge

The desktop surface is the Windows-first implementation of the transport-neutral execution surface contract.

## Scope

'DesktopPaperSurfaceAdapter' can:

- verify that a configured desktop executable exists;
- launch that executable through a local subprocess with 'shell=False';
- observe process liveness;
- optionally inspect visible Windows UI Automation window titles when 'pywinauto' is installed;
- persist deterministic PAPER feedback through 'ExecutionSurfaceFeedbackStore';
- record PAPER BUY/SELL/CANCEL intents without clicking order controls.

It deliberately cannot:

- click BUY/SELL/CANCEL controls;
- submit forms;
- call private exchange APIs;
- persist credentials, cookies, OTPs or session secrets;
- claim that a PAPER intent was filled by the exchange;
- authorize REAL execution.

## Configuration

A venue can construct the adapter with:

- 'venue_id'
- absolute/local 'executable_path'
- optional 'process_name'
- optional 'launch_args'
- optional 'working_dir'
- optional 'window_title_contains'
- optional bounded 'feedback_path'

The adapter is local-only. Relative application/data paths should be resolved by the existing repository path utilities before construction.

## Operational semantics

'probe()' returns:

- 'DOWN' when the executable is missing;
- 'DISCONNECTED' when the executable exists but the process is not running;
- 'OBSERVED' when the application process is running.

'CONNECT' starts only the configured desktop process. 'OBSERVE' reads operational state. BUY/SELL/CANCEL produce 'PAPER_INTENT_RECORDED' feedback and no trading-side effect.

The optional 'pywinauto' observation is read-only. If unavailable, process-level telemetry still works and the feedback states that UI title inspection was not configured/installed.

The adapter reuses the same feedback store and dashboard telemetry as browser surfaces. Operational health remains separate from economic evidence, OOS uncertainty, Risk Engine and REAL authorization.
