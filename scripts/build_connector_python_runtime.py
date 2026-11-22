#!/usr/bin/env python3
"""Build a root-owned, minimal CPython closure for the Linux connector sandbox.

This packager consumes only the trusted Python interpreter selected by CI or the
administrator. It never executes connector code and never discovers dependencies
at worker launch. The output is an immutable staging tree plus a separate
interpreter file so the manifest can mount the tree without covering the
executable path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

EXCLUDED_DIRS = {
    "__pycache__", "site-packages", "ensurepip", "test", "tests",
    "idlelib", "tkinter", "turtledemo",
}
EXCLUDED_FILES = {
    "sitecustomize.py", "usercustomize.py", "EXTERNALLY-MANAGED",
}
DEPENDENCY = re.compile(r"(?:=>\s+)?(/[^\s]+)\s+\(0x[0-9a-fA-F]+\)")
INTERPRETER = re.compile(r"Requesting program interpreter:\s*(/[^\]]+)")


def fail(code: str) -> "NoReturn":
    raise SystemExit(code)


def run(argv: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, check=False, env=env)
    if result.returncode:
        fail(f"runtime_packager_command_failed:{Path(argv[0]).name}:{result.stderr[-1200:]}")
    return result.stdout


def safe_destination(path: Path) -> Path:
    if not path.is_absolute() or path.parent != Path("/opt"):
        fail("runtime_destination_must_be_direct_child_of_opt")
    if path.exists() or path.is_symlink():
        fail("runtime_destination_already_exists")
    parent = Path("/opt")
    metadata = parent.stat()
    if metadata.st_uid != 0 or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        fail("runtime_destination_parent_not_protected")
    return path


def copy_regular(source: Path, target: Path, mode: int = 0o444) -> None:
    resolved = source.resolve(strict=True)
    if not resolved.is_file():
        fail(f"runtime_dependency_not_regular:{source.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(resolved.read_bytes()).digest():
            fail(f"runtime_dependency_name_collision:{target.name}")
        return
    shutil.copyfile(resolved, target)
    target.chmod(mode)


def copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        fail("python_stdlib_directory_missing")
    shutil.copytree(
        source,
        target,
        symlinks=False,
        ignore=shutil.ignore_patterns(*EXCLUDED_DIRS, "*.pyc", "*.pyo", "*.pth", *EXCLUDED_FILES),
    )
    for current, dirs, files in os.walk(target):
        for name in dirs:
            (Path(current) / name).chmod(0o555)
        for name in files:
            item = Path(current) / name
            if item.is_symlink() or not item.is_file():
                fail("runtime_package_contains_non_regular_file")
            item.chmod(0o555 if os.access(item, os.X_OK) else 0o444)


def ldd_dependencies(binary: Path, env: dict[str, str]) -> set[Path]:
    output = run(["ldd", str(binary)], env=env)
    if "not found" in output or "statically linked" in output:
        if "statically linked" in output:
            return set()
        fail(f"runtime_dependency_unresolved:{binary.name}")
    found = {Path(match).resolve(strict=True) for match in DEPENDENCY.findall(output)}
    if not found:
        fail(f"runtime_dependency_inventory_empty:{binary.name}")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("/opt/vst-connector-runtime"))
    parser.add_argument("--executable", type=Path, default=Path("/opt/vst-connector-python/python"))
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()

    if os.name != "posix" or not sys.platform.startswith("linux"):
        fail("linux_runtime_packager_required")
    if os.geteuid() != 0:
        fail("runtime_packager_requires_root")
    destination = safe_destination(args.destination)
    executable_target = args.executable
    if executable_target.parent != Path("/opt/vst-connector-python"):
        fail("runtime_executable_destination_invalid")
    executable_target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if executable_target.exists() or executable_target.is_symlink():
        fail("runtime_executable_destination_already_exists")

    python = args.python.resolve(strict=True)
    if not python.is_file() or not os.access(python, os.X_OK):
        fail("trusted_python_interpreter_required")
    version = sysconfig.get_python_version()
    stdlib_source = Path(sysconfig.get_path("stdlib")).resolve(strict=True)
    libdir = Path(sysconfig.get_config_var("LIBDIR") or "").resolve(strict=True)
    ld_library = sysconfig.get_config_var("LDLIBRARY")
    if not ld_library:
        fail("python_shared_library_name_missing")
    libpython_source = libdir / ld_library
    if not libpython_source.exists():
        fail("python_shared_library_missing")

    patchelf = shutil.which("patchelf")
    if not patchelf:
        fail("patchelf_required")

    stage = Path(tempfile.mkdtemp(prefix=".vst-runtime-stage-", dir="/opt"))
    try:
        runtime_lib = stage / "lib"
        stdlib_target = runtime_lib / f"python{version}"
        runtime_lib.mkdir(mode=0o755)
        copy_tree(stdlib_source, stdlib_target)
        copy_regular(libpython_source, runtime_lib / libpython_source.name)

        app = stage / "app" / "PC_ENGINE"
        (app / "core").mkdir(parents=True)
        repository = Path(__file__).resolve().parents[1]
        for relative in (
            "PC_ENGINE/__init__.py",
            "PC_ENGINE/core/__init__.py",
            "PC_ENGINE/core/isolated_connector_worker.py",
            "PC_ENGINE/core/connector_worker_limits.py",
        ):
            source = repository / relative
            if not source.is_file():
                fail(f"worker_bootstrap_source_missing:{relative}")
            target = stage / "app" / relative
            copy_regular(source, target)

        dependencies: set[Path] = set()
        ldd_env = {**os.environ, "LD_LIBRARY_PATH": str(libdir)}
        dependencies.update(ldd_dependencies(python, ldd_env))
        dependencies.update(ldd_dependencies(libpython_source, ldd_env))
        extension_root = stdlib_target / "lib-dynload"
        if not extension_root.is_dir():
            fail("python_extension_directory_missing")
        extensions = sorted(item for item in extension_root.rglob("*") if item.is_file() and ".so" in item.name)
        if not extensions:
            fail("python_extension_inventory_empty")
        for extension in extensions:
            dependencies.update(ldd_dependencies(extension, ldd_env))

        loader = None
        for dependency in sorted(dependencies):
            if dependency.name.startswith("ld-linux") or dependency.name.startswith("ld-musl"):
                loader = dependency
            copy_regular(dependency, runtime_lib / dependency.name)
        if loader is None:
            # The ELF interpreter is not always listed by ldd; inspect the
            # trusted interpreter's program headers and include it explicitly.
            headers = run(["readelf", "-l", str(python)])
            match = INTERPRETER.search(headers)
            if not match:
                fail("python_elf_loader_missing")
            loader = Path(match.group(1)).resolve(strict=True)
            copy_regular(loader, runtime_lib / loader.name)

        executable_target.parent.chmod(0o755)
        shutil.copyfile(python, executable_target)
        executable_target.chmod(0o555)
        loader_target = runtime_lib / loader.name
        if not loader_target.exists():
            copy_regular(loader, loader_target)
        run([patchelf, "--set-interpreter", str(loader_target), "--set-rpath", str(runtime_lib), str(executable_target)])

        for current, dirs, files in os.walk(stage):
            for name in dirs:
                (Path(current) / name).chmod(0o555)
            for name in files:
                item = Path(current) / name
                if item.is_symlink() or not item.is_file():
                    fail("runtime_package_contains_unsafe_entry")
                if item.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    fail("runtime_package_entry_writable_by_group_or_world")
                item.chmod(0o555 if os.access(item, os.X_OK) else 0o444)
        stage.chmod(0o555)

        inventory = []
        for item in sorted(stage.rglob("*")):
            if item.is_file():
                inventory.append({
                    "path": str(item.relative_to(stage)),
                    "size": item.stat().st_size,
                    "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
                })
        metadata = {
            "format": 1,
            "python_version": sys.version,
            "python_abi": sysconfig.get_config_var("SOABI"),
            "architecture": platform.machine(),
            "executable": str(executable_target),
            "python_home": str(destination),
            "library_path": str(destination / "lib"),
            "files": inventory,
        }
        # Metadata is generated outside the immutable runtime root. Its digest
        # is evidence for CI only; production authentication/signing is a
        # separate gate and must not be inferred from this unsigned document.
        metadata_path = Path("/opt/vst-connector-runtime-manifest.json")
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        metadata_path.chmod(0o444)
        os.rename(stage, destination)
        print(json.dumps({
            "runtime_root": str(destination),
            "executable": str(executable_target),
            "python_home": str(destination),
            "library_path": str(destination / "lib"),
            "python_version": version,
            "files": len(inventory),
        }, sort_keys=True))
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        if executable_target.exists():
            executable_target.unlink()
        raise


if __name__ == "__main__":
    main()
