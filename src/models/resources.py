"""Best-effort system resource detection: RAM, disk, GPU VRAM, Ollama reachability.

Used by src/models/registry.py (RAM-fit validation) and scripts/validate_system.py
(startup validation) to implement issues #5 and #11.
"""

import logging
import shutil
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:  # pragma: no cover - exercised only when psutil is absent
    psutil = None
    _HAS_PSUTIL = False


def _read_proc_meminfo() -> dict:
    """Parse /proc/meminfo into a dict of {key: 'value kB'} (Linux only)."""
    meminfo = {}
    with open("/proc/meminfo", "r") as f:
        for line in f:
            parts = line.split(":")
            if len(parts) == 2:
                meminfo[parts[0].strip()] = parts[1].strip()
    return meminfo


def get_available_ram_gb() -> float:
    """Return currently available (not just free) RAM in GB.

    Prefers psutil when installed (cross-platform, accounts for reclaimable
    cache). Falls back to /proc/meminfo's MemAvailable on Linux. Returns 0.0
    (logging a warning) when neither is available, e.g. on macOS without
    psutil - callers should treat 0.0 as "unknown" rather than "no RAM".
    """
    if _HAS_PSUTIL:
        return psutil.virtual_memory().available / (1024 ** 3)

    try:
        meminfo = _read_proc_meminfo()
        available_kb = meminfo.get("MemAvailable") or meminfo.get("MemFree") or meminfo.get("MemTotal")
        if not available_kb:
            raise ValueError("no memory fields found")
        value_kb = float(available_kb.split()[0])
        return value_kb / (1024 ** 2)
    except (FileNotFoundError, ValueError, IndexError):
        logger.warning(
            "Unable to determine available RAM (psutil not installed and "
            "/proc/meminfo unavailable on this platform); reporting 0.0GB (unknown)."
        )
        return 0.0


def get_total_ram_gb() -> float:
    """Return total physical RAM in GB, or 0.0 if it cannot be determined."""
    if _HAS_PSUTIL:
        return psutil.virtual_memory().total / (1024 ** 3)

    try:
        meminfo = _read_proc_meminfo()
        total_kb = meminfo.get("MemTotal")
        if not total_kb:
            raise ValueError("MemTotal not found")
        return float(total_kb.split()[0]) / (1024 ** 2)
    except (FileNotFoundError, ValueError, IndexError):
        logger.warning("Unable to determine total RAM on this platform; reporting 0.0GB (unknown).")
        return 0.0


def get_disk_space_gb(path: str = ".") -> float:
    """Return free disk space in GB at the given path."""
    usage = shutil.disk_usage(path)
    return usage.free / (1024 ** 3)


def get_gpu_vram_gb() -> Optional[tuple]:
    """Best-effort GPU VRAM detection via `nvidia-smi`.

    Returns (vram_gb, gpu_name) for the first detected GPU, or None if no
    NVIDIA GPU / driver is present. This is inherently best-effort: sandboxed
    or CPU-only environments will always return None, which callers should
    report as "N/A" rather than treat as an error.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        first_line = result.stdout.strip().splitlines()[0]
        mem_mb_str, name = first_line.split(",", 1)
        return float(mem_mb_str.strip()) / 1024, name.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
        return None


def check_ollama_reachable(base_url: str, timeout: float = 3.0) -> bool:
    """Return True if the Ollama server at base_url responds to /api/tags."""
    try:
        import httpx

        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False
