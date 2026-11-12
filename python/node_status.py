"""Human-readable status, without importing or starting the node daemon."""
from pathlib import Path
import subprocess

import engine_service
import manifest
import version_identity


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        patch = (root / 'patches/active_patch.txt').read_text().strip()
    except OSError:
        patch = '(unavailable)'
    candidate, _error = manifest.load(str(root / 'patches' / patch))
    name = Path(candidate['engine']).name if candidate else 'pd'
    print('Engine alive:', engine_service.alive(name))
    print('Active patch:', patch)
    print('Framework version:', version_identity.display_version(root))
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', '--short', 'HEAD'],
                              capture_output=True, text=True)
    print('Framework revision:', revision.stdout.strip() or '(unavailable)')
    for name in ('bopos', 'io'):
        print('\nLast ' + name + ' log lines:')
        try:
            # Read the tail without loading a potentially large capped log.
            with (root / ('run/' + name + '.log')).open('rb') as source:
                source.seek(0, 2)
                source.seek(max(0, source.tell() - 8192))
                print('\n'.join(source.read().decode(errors='replace').splitlines()[-10:]))
        except OSError:
            print('(unavailable)')


if __name__ == '__main__':
    main()
