from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any


def _available_ram_bytes() -> int | None:
    """Read a RAM estimate without installing dependencies or changing the host."""
    try:
        if hasattr(os, "sysconf"):
            pages = int(os.sysconf("SC_PHYS_PAGES"))
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            if pages > 0 and page_size > 0:
                return pages * page_size
    except (OSError, ValueError, TypeError, AttributeError):
        pass

    if platform.system() == "Windows":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except (AttributeError, OSError, TypeError):
            pass
    return None


def _read_config(config_dir: Path) -> tuple[dict[str, Any] | None, str, str | None]:
    local = config_dir / "config.local.json"
    example = config_dir / "config.example.json"
    path = local if local.is_file() else example
    if not path.is_file():
        return None, "missing", "No config.local.json or config.example.json found"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        # Report only the exception type; never echo file contents or secrets.
        return None, path.name, f"Config unreadable ({type(exc).__name__})"
    if not isinstance(payload, dict):
        return None, path.name, "Config root must be a JSON object"
    return payload, path.name, None


def _probe_webgl() -> dict[str, Any]:
    """Probe a locally installed Playwright Chromium; never download browsers or visit a network URL."""
    if importlib.util.find_spec("playwright") is None:
        return {"status": "unavailable", "reason": "playwright_not_installed", "webgl1": False, "webgl2": False}

    browser = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                timeout=5000,
                args=["--disable-dev-shm-usage"],
            )
            page = browser.new_page()
            page.set_default_timeout(3000)
            result = page.evaluate("""() => {
                const probe = (name) => {
                    try {
                        const canvas = document.createElement('canvas');
                        const gl = canvas.getContext(name);
                        if (!gl) return {available: false, renderer: null};
                        const ext = gl.getExtension('WEBGL_debug_renderer_info');
                        const renderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null;
                        return {available: true, renderer};
                    } catch (_) {
                        return {available: false, renderer: null};
                    }
                };
                const one = probe('webgl');
                const two = probe('webgl2');
                return {webgl1: one.available, webgl2: two.available, renderer: two.renderer || one.renderer || null};
            }""")
            renderer = result.get("renderer")
            software_renderer = bool(
                isinstance(renderer, str)
                and any(token in renderer.lower() for token in ("swiftshader", "llvmpipe", "software rasterizer", "softpipe"))
            )
            return {
                "status": "probed",
                "webgl1": bool(result.get("webgl1")),
                "webgl2": bool(result.get("webgl2")),
                "renderer": renderer if isinstance(renderer, str) else None,
                "software_renderer_detected": software_renderer if renderer else None,
            }
    except Exception as exc:
        # Avoid returning exception messages, paths, or other potentially sensitive host details.
        return {
            "status": "unknown",
            "reason": type(exc).__name__,
            "webgl1": False,
            "webgl2": False,
        }
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


def _visual_recommendations(
    ram_bytes: int | None, cpu_count: int | None, renderer: dict[str, Any]
) -> dict[str, Any]:
    """Recommend modes conservatively; recommendations never control trading permissions."""
    modes = {"chat": True, "pixel": True, "enhanced": False, "3d": False}
    reasons: list[str] = []
    if ram_bytes is None or ram_bytes < 4 * 1024**3 or cpu_count is None or cpu_count < 2:
        reasons.append("enhanced_requires_at_least_4GiB_RAM_and_2_logical_CPUs")
    elif renderer.get("status") == "probed" and renderer.get("webgl2"):
        modes["enhanced"] = True
    else:
        reasons.append("enhanced_requires_successful_local_WebGL2_probe")

    if (
        ram_bytes is not None
        and ram_bytes >= 8 * 1024**3
        and cpu_count is not None
        and cpu_count >= 4
        and renderer.get("status") == "probed"
        and renderer.get("webgl2")
        and renderer.get("software_renderer_detected") is False
    ):
        modes["3d"] = True
    else:
        reasons.append("3d_requires_8GiB_RAM_4_CPUs_and_detected_nonsoftware_WebGL2")

    return {
        "default": "auto",
        "available_baseline": ["chat", "pixel"],
        "recommended_modes": modes,
        "reasons": reasons,
        "note": "Recommendations only; optional components must not be installed unless selected and supported.",
    }


def collect_diagnostics(
    root: str | Path | None = None, *, probe_renderer: bool = False
) -> dict[str, Any]:
    """Collect local install readiness without creating dirs, starting services, or using network."""
    repo_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    engine_root = repo_root / "PC_ENGINE"
    config_dir = engine_root / "config"
    data_dir = engine_root / "data"
    config, config_source, config_error = _read_config(config_dir)

    configured_mode = str(config.get("mode", "PAPER")).upper() if config else "UNKNOWN"
    effective_mode = "PAPER" if configured_mode == "REAL" else configured_mode
    renderer = _probe_webgl() if probe_renderer else {
        "status": "not_requested", "webgl1": None, "webgl2": None,
        "software_renderer_detected": None,
    }
    ram_bytes = _available_ram_bytes()
    cpu_count = os.cpu_count()
    dependencies = {
        name: importlib.util.find_spec(name) is not None
        for name in ("flask", "ccxt", "playwright")
    }
    disk_path = data_dir if data_dir.exists() else repo_root
    try:
        disk = shutil.disk_usage(disk_path)
        free_disk_bytes: int | None = int(disk.free)
    except OSError:
        free_disk_bytes = None

    checks: dict[str, dict[str, Any]] = {
        "config": {
            "ok": config is not None and config_error is None,
            "source": config_source,
            "error": config_error,
        },
        "mode": {
            "ok": configured_mode == "PAPER",
            "configured": configured_mode,
            "effective": effective_mode,
            "paper_only": True,
        },
        "dependencies": {
            "ok": all(dependencies.values()),
            "available": dependencies,
        },
        "runtime_data_directory": {
            "ok": not data_dir.exists() or data_dir.is_dir(),
            "exists": data_dir.exists(),
            "initialized": data_dir.is_dir(),
            "writable_if_present": os.access(data_dir, os.W_OK) if data_dir.exists() else None,
        },
        "disk_space": {"ok": free_disk_bytes is not None, "free_bytes": free_disk_bytes},
    }
    critical = [name for name, check in checks.items() if check.get("ok") is False]
    if configured_mode == "REAL":
        status = "SAFE_STATE"
    elif critical:
        status = "DEGRADED"
    else:
        status = "READY"

    return {
        "schema_version": 1,
        "command": "vst doctor",
        "status": status,
        "read_only": True,
        "changes_made": False,
        "network_requests": 0,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_logical": cpu_count,
            "ram_total_bytes": ram_bytes,
        },
        "paths": {
            "repository_root": str(repo_root),
            "engine_root_exists": engine_root.is_dir(),
            "config_source": config_source,
            "data_directory_exists": data_dir.is_dir(),
        },
        "checks": checks,
        "renderer": renderer,
        "visual_profile": _visual_recommendations(ram_bytes, cpu_count, renderer),
        "critical_checks": critical,
        "safety": {
            "configured_mode": configured_mode,
            "effective_mode": effective_mode,
            "real_promotion_attempted": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only VST installation/runtime diagnostics; no services are started."
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--probe-renderer", action="store_true",
        help="probe a locally installed Playwright Chromium for WebGL support; never downloads a browser",
    )
    args = parser.parse_args(argv)
    report = collect_diagnostics(probe_renderer=args.probe_renderer)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"VST doctor: {report['status']}")
        print(f"Platform: {report['platform']['system']} / {report['platform']['machine']}")
        print(f"Mode: {report['safety']['configured_mode']} (effective {report['safety']['effective_mode']})")
        for name, check in report["checks"].items():
            print(f"- {'PASS' if check.get('ok') else 'CHECK'} {name}")
        print("Read-only: yes; network requests: 0; changes made: no")
    return {"READY": 0, "DEGRADED": 1, "SAFE_STATE": 2}.get(report["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
