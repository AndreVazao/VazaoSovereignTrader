# Minimal Python Runtime Closure — design and acceptance tests

**Status:** design contract only. No packaged Python runtime or production launcher is implemented by this document.
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