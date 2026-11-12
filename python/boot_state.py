"""Boot-local observations: crash restarts must preserve this boot's records."""
import os
import sys
import time


def boot_time():
    try:
        with open('/proc/uptime') as source:
            return time.time() - float(source.read().split()[0])
    except (OSError, ValueError, IndexError):
        # Non-Linux development hosts do not rotate on process restarts either.
        return 0


def predates_boot(path):
    try:
        return os.stat(path).st_mtime < boot_time()
    except FileNotFoundError:
        return False


def clear_previous_boot(path):
    if predates_boot(path):
        os.unlink(path)


if __name__ == '__main__':
    clear_previous_boot(sys.argv[1])
