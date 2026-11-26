# Minimal Python Runtime Closure — design and acceptance tests

**Status:** design contract plus validated implementation increments. The packaged Linux CPython runtime and a trusted-parent Bubblewrap launcher are implemented and CI-tested; production supervisor/registry integration, authenticated inventory and TOCTOU closure remain unimplemented.
**Scope:** Linux Bubblewrap worker runtime for PR #578. Windows remains separately constrained by Job Objects and is not filesystem/network-isolated.

## Objective

Run the existing one-shot connector worker under Bubblewrap using a package-owned, explicit runtime closure. The worker must not inherit host /usr, /lib, /bin, host Python paths, host site-packages, VST state, credentials, user home, or host scratch paths.

## Runtime package contract

The packager must produce a versioned, immutable runtime directory from pinned build inputs. It must include only:
- The exact Python interpreter executable.
- The interpreter's required standard-library files and extension modules.
- The ELF interpreter/loader and exact shared libraries required by the interpreter and included extension modules.
- A deliberately selected CA trust bundle only if/when network policy is introduced; current worker network remains disabled.
- The VST worker bootstrap module and an explicit, reviewed set of first-party worker modules/dependencies.

The package must not contain pip, compilers, shells, package managers, debuggers, host configuration, user site-packages, .pth files, sitecustomize.py, usercustomize.py, or arbitrary executable utilities unless individually justified and tested. Disable bytecode writes and user site initialization. Do not use ldd on untrusted executables or dynamically discover dependencies at worker launch.

## Manifest generation and integrity

- Generate the manifest at trusted packaging time from the package staging directory and a reviewed dependency inventory.
- Record package format version, Python ABI/version, architecture, source paths, in-sandbox destinations, file type, size and SHA-256 for every regular file.
- Reject symlinks, hard links, special files, duplicate destinations, path traversal, writable-by-group/world entries and unreviewed executable files.
- Reject every source path that overlaps host-owned sensitive/system roots, including nested descendants and ancestor mounts; package sources must come from a protected, package-owned runtime location rather than user home, VST state, host configuration, temporary or broad system trees.
- Sign or otherwise authenticate the manifest as part of the installer/package trust chain. Hashes alone do not establish authenticity if an attacker can replace both package and manifest.
- Install under a protected, versioned directory that the runtime user cannot modify. Do not update files in place while workers may be starting.
- Revalidate the package identity and file metadata immediately before launch. Prefer opening sources by file descriptor and using fd-based bind mounts where supported; if the implementation cannot close the validation-to-mount race, deny launch rather than claiming TOCTOU protection.

## Bubblewrap launch contract

The launcher, not the Python worker, owns sandbox construction. It must:
1. Validate the authenticated package manifest and exact worker entry point.
2. Construct argv without a shell and use only the manifest-backed builder. Never fall back to legacy broad runtime_roots.
3. Create fresh private user/PID/IPC/UTS/network namespaces and bounded private /tmp and /work.
4. Mount only manifest entries read-only, preserving required ELF loader destination aliases explicitly.
5. Set a minimal deterministic environment: isolated HOME/TMPDIR, PYTHONHOME pointing inside the package, PYTHONNOUSERSITE=1, PYTHONDONTWRITEBYTECODE=1, PYTHONSAFEPATH=1, and a minimal PATH containing no host directories.
6. Disable network entirely until a separately reviewed provider-specific egress broker exists.
7. Start the worker bootstrap as the declared interpreter's module/script; do not spawn a second unsandboxed Python process.
8. Keep bounded IPC endpoints outside the worker's filesystem namespace and preserve the existing sanitized JSON envelope contract.
9. Treat Bubblewrap absence, namespace denial, mount failure, manifest mismatch, startup timeout and worker crash as hard denial; no direct-process fallback.
10. Kill the complete sandbox process tree and close all IPC/file descriptors on success, error, timeout, cancellation and parent crash.

## Required real-runtime test

The Linux enforcement workflow must build the runtime package from pinned inputs and execute that exact packaged interpreter under Bubblewrap. The test must:
- Import the worker bootstrap and every declared standard-library/extension dependency.
- Assert interpreter version, ABI, architecture, sys.prefix, sys.base_prefix, sys.path, HOME and TMPDIR are package/sandbox-local.
- Run a bounded worker request and validate the existing JSON IPC response.
- Prove that host /usr/bin/id, host /etc/passwd, host Python, undeclared host marker files, VST data, Learning Vault and host temporary paths are inaccessible.
- Prove network, loopback and local service access fail.
- Prove no host PATH, PYTHONPATH, PYTHONHOME, proxy, credential-shaped environment or user-site configuration is inherited.
- Prove scratch size caps and read-only runtime mounts.
- Exercise missing loader/library, tampered manifest, modified package file, symlink/hardlink replacement, path traversal, crash, timeout, child process and cleanup failures.
- Never silently skip the actual Bubblewrap execution in its dedicated CI job.

## Integration sequence

1. Build and test the packaged runtime in isolation from the worker lifecycle.
2. Add a Linux launcher that starts the existing worker entry point directly inside Bubblewrap and retains the existing bounded IPC protocol.
3. Add parent-side supervision, startup handshake, cancellation and process-tree cleanup tests.
4. Integrate behind an explicit Linux-only policy switch in IsolatedConnectorAdapter; unsupported platforms must deny rather than use the direct multiprocessing path for untrusted adapters.
5. Keep ConnectorRegistry disconnected until the packaged-runtime, lifecycle and adversarial gates pass.
6. Only after filesystem isolation is proven, design provider-specific HTTPS egress using OS-level enforcement and tests for DNS rebinding, redirects, private IPs, proxies and peer-address validation.
7. Implement Windows AppContainer/restricted-token filesystem isolation and WFP/Firewall egress controls independently. Job Objects are resource/process controls, not a sandbox.

## Non-goals and safety

- No API credentials, private exchange scopes, account linking, orders, transfers, withdrawals or LIVE mode.
- No third-party connector execution during this work.
- No assumption that Linux CI proves the user's physical Windows PC.
- No claim that a static assembly probe is equivalent to a packaged Python runtime.
- No merge while any required exact-HEAD workflow or security gate is incomplete.

## Packaged-runtime implementation increment — 2026-11-22

A first reproducible Linux packaging path now exists in `scripts/build_connector_python_runtime.py`. It requires root and a protected `/opt` parent, copies the selected trusted CPython interpreter's standard library and selected worker bootstrap modules into a versioned-layout staging tree, inventories ELF dependencies of the interpreter, libpython and extension modules, copies the loader/shared libraries into the package, and patches the copied interpreter to use the package-local loader and library path. The executable is deliberately stored outside the mounted runtime directory so the manifest does not hide it behind a directory mount.

The dedicated Linux workflow now installs Bubblewrap, patchelf and binutils, builds this package, and runs `tests/test_connector_python_runtime.py` inside the real sandbox. The test imports the actual `IsolatedConnectorAdapter` module plus selected standard-library and extension modules, exercises a size-bounded local IPC exchange, checks the runtime prefix and sanitized environment, and verifies host files and loopback networking are unavailable.

This is an implementation/test increment, not yet a production runtime release:
- The generated JSON inventory is unsigned. It is CI evidence, not an authenticity mechanism.
- Package immutability currently relies on root ownership and read-only modes; a production installer must establish and verify this trust boundary.
- The packager's ELF dependency discovery uses `ldd` only on the trusted CI-selected CPython interpreter and its bundled extension modules. It must never be reused on arbitrary connector binaries.
- The current IPC probe uses a bounded local socket pair; it does not yet prove that the existing multiprocessing worker lifecycle is supervised inside Bubblewrap.
- The real runtime test must pass on the exact current PR HEAD before this increment is considered validated.
- No connector adapter is launched through this runtime yet. The registry remains disconnected from untrusted connector execution.

## Supervised multiprocessing probe — 2026-11-22

The packaged-runtime integration now includes a second-stage probe launched by the packaged interpreter itself. It invokes the existing `IsolatedConnectorAdapter` inside Bubblewrap, so the existing `multiprocessing.get_context("spawn")` path is exercised rather than only simulating a socket exchange.

The probe verifies:
- worker process starts from the packaged CPython executable;
- bootstrap handshake and resource-limit acknowledgement complete;
- bounded request/response crosses the existing multiprocessing pipes;
- a deliberately slow adapter hits the parent-side timeout;
- the parent's process-group cleanup reaps the worker and leaves no active child.

This is stronger CI evidence for the existing worker lifecycle, but it does not mean the supervisor launches that worker under Bubblewrap in production. The test explicitly enters Bubblewrap first and then starts the worker from inside that namespace. The missing production integration remains: the trusted parent must construct the strict manifest-backed Bubblewrap argv and launch the worker executable through it before any adapter code can run. No fallback to the legacy unsandboxed multiprocessing path is allowed when strict mode is required.


## Trusted-parent Bubblewrap launcher increment — 2026-11-26

A first parent-side launcher is now implemented in `PC_ENGINE/core/linux_connector_launcher.py` and covered by `tests/test_linux_connector_launcher.py`.

- The parent builds the command only through the strict `runtime_manifest` path. It does not accept legacy `runtime_roots` and does not fall back to multiprocessing or unsandboxed execution.
- The worker bootstrap runs directly under the declared packaged interpreter inside Bubblewrap; the parent sends one bounded JSON request over stdin and accepts one bounded JSON response over stdout.
- Bubblewrap starts in a dedicated parent process group. The parent enforces an operation deadline, bounds captured stdout, discards stderr, and kills the complete process group on timeout or abnormal cleanup.
- The strict builder continues to create private bounded `/tmp` and `/work`, clear the environment, mount only manifest entries read-only and deny all network access.

**Exact-HEAD CI evidence:** the dedicated Linux enforcement workflow passed on PR #603 code HEAD `9d7caf0000cc9b3acd6c79da777927ec0519ce11` ([run 45826907713](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45826907713)): **86 passed**, including the actual trusted-parent launch of the packaged CPython bootstrap inside Bubblewrap and a timeout/cleanup test. The Python suite and PAPER lifecycle checks are tracked separately on their own exact HEADs.

**Scope limit:** the launcher is not connected to `ConnectorRegistry` or the production worker supervisor. The runtime manifest is revalidated structurally but is not cryptographically authenticated, and the filesystem validation-to-mount race is not yet closed. The package must remain root-owned and immutable; no third-party connector may be enabled. Provider-specific network egress and Windows filesystem/network isolation remain separate blockers.


**Exact-HEAD cross-workflow evidence:** the same code-bearing HEAD `9d7caf0000cc9b3acd6c79da777927ec0519ce11` passed Python (**1,726 passed, 5 skipped, 101 subtests**) in [run 45826907675](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45826907675), PAPER lifecycle (**82 passed**) in [run 45826907551](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45826907551), and Windows EXE/installer in [run 45826907651](https://github.com/AndreVazao/VazaoSovereignTrader/actions/runs/45826907651). Snyk did not publish a check on this HEAD; this PR changes no dependency manifests.

**Repository snapshot before this documentation refresh:** main remains `cd2b39e7bd454f8178aa9fb29e87acd29fd9fd1a`; PR #603 is the single active implementation PR. Its validated code-bearing commit is `9d7caf0000cc9b3acd6c79da777927ec0519ce11`. The following commit updates documentation only.
