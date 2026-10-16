#!/usr/bin/env python3
"""Generate the existing paid distribution profile without adding capabilities."""
import pathlib
import re
import subprocess
import sys
import tempfile


def generate(source, destination):
    with tempfile.TemporaryDirectory() as tmp:
        stripped = pathlib.Path(tmp) / 'project.yml'
        subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('project_free.py')),
                        str(source), str(stripped)], check=True)
        spec = stripped.read_text()
    spec, count = re.subn(r'^ *com.apple.security.application-groups:.*\n', '', spec, flags=re.M)
    if count != 1:
        raise ValueError('Expected exactly one App Group entitlement')
    old = 'CFBundleDisplayName: D2R Mobile\n'
    if spec.count(old) != 1:
        raise ValueError('Expected one iOS display name')
    spec = spec.replace(old, 'CFBundleDisplayName: D2R 暗黑之旅\n')
    pathlib.Path(destination).write_text(spec)


if __name__ == '__main__':
    generate(*sys.argv[1:3])
