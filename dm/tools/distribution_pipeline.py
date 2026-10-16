#!/usr/bin/env python3
"""Local distribution preparation; creates unsigned archives, never uploads."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

SOURCE = Path(__file__).resolve().parents[2]


def environment(project, ios18=False):
    project = Path(project).resolve()
    baseline = project / '暗黑2打包工程/full-1.0.4/Payload/SwIOS.app/sw'
    local_env = project / '源码打包流程/local.env'
    if not local_env.is_file():
        raise ValueError('Existing signing local.env is required')
    env = os.environ.copy()
    env.update(DM_LOCAL_ENV=str(local_env), DM_LANG='zh', DM_GEN_ONLY='1',
               DM_DISTRIBUTION_PROFILE='1', DM_IOS_M3='1' if ios18 else '0')
    for key, filename in [('DM_ASSET_BASE', 'asset_base.txt'),
                          ('DM_ASTC_PACK_BASE', 'astc_pack_base.txt')]:
        value = (baseline / filename).read_text().strip()
        if urlsplit(value).scheme != 'https' or urlsplit(value).hostname != 'download.a-mini.com':
            raise ValueError('Expected existing HTTPS R2 download gateway')
        env[key] = value
    root = Path(env.get('DM_ROOT', str(Path.home() / 'dm-work')))
    env['DM_ROOT'] = str(root)
    env['PATH'] = str(root / 'build/cache/dm/venv/bin') + os.pathsep + env['PATH']
    return env


def execute(project, action, ios18=False, number=None):
    env = environment(project, ios18)
    # Signing is loaded by the existing shell helper, not re-written or copied into Git.
    checked = subprocess.run(['bash', str(SOURCE / 'setup.sh'), 'check'], env=env)
    if checked.returncode or action == 'check':
        return checked.returncode
    if not number or not re.fullmatch(r'\d+\.\d+\.\d+', number):
        raise ValueError('Use a three-component build number')
    legacy = Path(env.get('DM_ASTC_PACK', '/nonexistent'))
    if not all((legacy / f).is_file() for f in ('pack.json', 'pack_index.tsv')):
        raise ValueError('Matching DM_ASTC_PACK with pack.json and pack_index.tsv required')
    output = Path(project) / '源码打包流程' / ('ios18' if ios18 else 'ios26')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / ('D2R-' + number + '.xcarchive')
    if archive.exists():
        raise ValueError('Archive already exists; choose a new build number')
    for command in [
        ['bash', str(SOURCE / 'setup.sh')],
        ['bash', str(SOURCE / 'dm/ios/run.sh'), 'build'],
        ['xcodebuild', '-project', str(SOURCE / 'dm/ios/DmIOS.xcodeproj'), '-scheme', 'DmIOS',
         '-configuration', 'Release', '-destination', 'generic/platform=iOS',
         '-archivePath', str(archive), 'CODE_SIGNING_ALLOWED=NO',
         'DM_BUILD_NUMBER=' + number, 'MARKETING_VERSION=1.0.0', 'archive'],
    ]:
        subprocess.run(command, env=env, check=True)
    print('Unsigned archive created; not exported, installed or uploaded.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'build'])
    parser.add_argument('--project-root', type=Path, default=SOURCE.parent)
    parser.add_argument('--ios18', action='store_true')
    parser.add_argument('--build-number')
    args = parser.parse_args()
    try:
        sys.exit(execute(args.project_root, args.action, args.ios18, args.build_number))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        # Never print environment values or signed resource URLs.
        print('Stopped:', str(exc) if isinstance(exc, ValueError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
