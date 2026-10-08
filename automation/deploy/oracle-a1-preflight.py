#!/usr/bin/env python3
"""Read-only Oracle Ampere A1 host checks; never claims to verify OCI billing.

Inputs: local OS/CPU/RAM/root filesystem. Output: pass/fail before installing Docker.
The tenancy home region, shape, Always Free label, and billing must be verified in OCI.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import sys

GIB = 1024 ** 3


def check_platform(arch: str, os_release: dict[str, str], cpus: int, ram_bytes: int, disk_bytes: int) -> list[str]:
    failures = []
    if arch not in ("aarch64", "arm64"):
        failures.append("expected Linux ARM64/aarch64 (OCI Ampere A1), not " + arch)
    if (os_release.get("ID"), os_release.get("VERSION_ID")) != ("ubuntu", "24.04"):
        failures.append("expected Ubuntu Server 24.04 LTS")
    if cpus < 2:
        failures.append("expected 2 OCPUs (detected fewer than 2 CPUs)")
    if ram_bytes < 10 * GIB:
        failures.append("expected 12 GB allocation (detected less than 10 GiB usable RAM)")
    if disk_bytes < 75 * GIB:
        failures.append("expected a boot volume sized about 100 GB (less than 75 GiB root disk)")
    return failures


def read_os_release(path: Path = Path('/etc/os-release')) -> dict[str, str]:
    info = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if '=' not in line or line.startswith('#'):
            continue
        key, value = line.split('=', 1)
        info[key] = value.strip().strip('"')
    return info


def read_mem_bytes(path: Path = Path('/proc/meminfo')) -> int:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith('MemTotal:'):
            return int(line.split()[1]) * 1024
    raise ValueError('MemTotal not found')


def main() -> int:
    if sys.platform != 'linux':
        print('BLOCKED: preflight must run on the target Linux VM')
        return 1
    try:
        failures = check_platform(platform.machine().lower(), read_os_release(),
                                  os.cpu_count() or 0, read_mem_bytes(),
                                  shutil.disk_usage('/').total)
    except (OSError, ValueError) as exc:
        print('BLOCKED: cannot inspect host:', type(exc).__name__)
        return 1
    if failures:
        print('BLOCKED: host does not match the approved Oracle A1 profile:')
        for failure in failures:
            print(' -', failure)
        return 1
    print('PASS: basic Ubuntu 24.04 / ARM64 / 2 CPU / RAM / disk preflight.')
    print('IMPORTANT: only OCI Console can confirm the Always Free label, home region,')
    print('VM.Standard.A1.Flex shape, 2 OCPU / 12 GB / 100 GB and zero paid add-ons.')
    print('No cloud resources were created. START_ENABLED remains false.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
