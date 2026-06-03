#!/usr/bin/env python3
"""Small helper to bump the semver `version` field inside `config.yaml`.

Usage:
  python bump_version.py [major|minor|patch]
  python bump_version.py --set 2.0.0

This script edits `config.yaml` in-place and prints the new version.
"""
import re
import sys
from pathlib import Path

CONFIG = Path(__file__).parents[1] / 'config.yaml'

def read_version(text: str) -> str | None:
    # match lines like: version: "1.4.2"  or version: 1.4.2
    m = re.search(r'^\s*version\s*:\s*["\']?(\d+\.\d+\.\d+)["\']?\s*$', text, flags=re.M)
    return m.group(1) if m else None

def replace_version(text: str, new_version: str) -> str:
    return re.sub(r'(^\s*version\s*:\s*["\']?)(\d+\.\d+\.\d+)(["\']?\s*$)', r"\1" + new_version + r"\3", text, flags=re.M)

def bump(v: str, part: str) -> str:
    parts = [int(x) for x in v.split('.')]
    if part == 'major':
        parts[0] += 1; parts[1] = 0; parts[2] = 0
    elif part == 'minor':
        parts[1] += 1; parts[2] = 0
    else:
        parts[2] += 1
    return '.'.join(str(x) for x in parts)

def main(argv):
    if not CONFIG.exists():
        print('config.yaml not found at', CONFIG)
        return 2
    txt = CONFIG.read_text(encoding='utf-8')
    cur = read_version(txt)
    if cur is None:
        print('Could not find version in config.yaml')
        return 3

    if len(argv) >= 2 and argv[1] == '--set':
        if len(argv) < 3:
            print('Usage: --set VERSION')
            return 4
        new = argv[2]
    else:
        part = 'patch'
        if len(argv) >= 2 and argv[1] in ('major','minor','patch'):
            part = argv[1]
        new = bump(cur, part)

    new_txt = replace_version(txt, new)
    if new_txt == txt:
        print('No change made')
        return 5
    CONFIG.write_text(new_txt, encoding='utf-8')
    print(f'Bumped version: {cur} -> {new}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
#!/usr/bin/env python3
"""
Semplice script per incrementare la versione semantica in `config.yaml`.

Usage:
  python bump_version.py [major|minor|patch]

Default: patch

Lo script modifica in-place `config.yaml` nel parent directory dello script.
Fai un backup manuale se necessario.
"""
import sys
import re
from pathlib import Path


def bump_version_str(v: str, part: str) -> str:
    parts = v.strip().split('.')
    # ensure at least 3 parts
    while len(parts) < 3:
        parts.append('0')
    major, minor, patch = map(int, parts[:3])
    if part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif part == 'minor':
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def main():
    part = 'patch'
    if len(sys.argv) > 1:
        if sys.argv[1] in ('major', 'minor', 'patch'):
            part = sys.argv[1]
        else:
            print('Argomento non valido, usare major|minor|patch')
            sys.exit(2)

    cfg = Path(__file__).resolve().parents[1] / 'config.yaml'
    if not cfg.exists():
        print('config.yaml non trovato in', cfg)
        sys.exit(1)

    txt = cfg.read_text(encoding='utf-8')
    m = re.search(r'^version:\s*"?(\d+(?:\.\d+){0,2})"?\s*$', txt, flags=re.M)
    if not m:
        print('version non trovata in config.yaml')
        sys.exit(1)

    old = m.group(1)
    new = bump_version_str(old, part)
    new_txt = txt[:m.start(1)] + new + txt[m.end(1):]
    # write backup
    bak = cfg.with_suffix('.yaml.bak')
    bak.write_text(txt, encoding='utf-8')
    cfg.write_text(new_txt, encoding='utf-8')
    print(f'Updated version: {old} -> {new} (backup: {bak.name})')


if __name__ == '__main__':
    main()
