"""Offline reporter launcher only; not a model controller or trust anchor."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def report():
    shell = shutil.which('pwsh')
    if shell is None:
        print(json.dumps({'decision': 'NO_GO', 'reporter': 'NOT_TESTED'}))
        return 1
    # Only OS/runtime metadata reaches this child. Never pass credentials or
    # arbitrary evidence flags. Opt out BEFORE startup, even if parent opted in.
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP',
                              'HOME', 'USERPROFILE', 'LANG', 'LC_ALL'}}
    env['POWERSHELL_TELEMETRY_OPTOUT'] = '1'
    env['POWERSHELL_UPDATECHECK'] = 'Off'
    # Use disposable startup caches; never publish these runtime paths.
    with tempfile.TemporaryDirectory(prefix='garden-report-') as cache:
        env.update(XDG_CACHE_HOME=cache, XDG_CONFIG_HOME=cache, XDG_DATA_HOME=cache)
        try:
            result = subprocess.run([shell, '-NoProfile', '-NonInteractive', '-File',
                                     str(Path(__file__).with_name('acceptance.ps1'))],
                                    env=env, stdin=subprocess.DEVNULL, timeout=20, check=False)
        except (OSError, subprocess.TimeoutExpired):
            print(json.dumps({'decision': 'NO_GO', 'reporter': 'NOT_TESTED'}))
            return 1
    # A child returning 0 is not acceptance either. No path can authorize GO.
    return result.returncode if result.returncode != 0 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true', required=True)
    parser.parse_args()
    return report()


if __name__ == '__main__':
    raise SystemExit(main())
