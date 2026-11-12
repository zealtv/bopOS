"""Isolate subprocesses from Git's hook-local repository and index settings."""
import os


def environment():
    # -C/cwd do not override GIT_DIR or GIT_INDEX_FILE. Remove every inherited
    # Git variable, including configuration overrides and worktree/common paths.
    return {key: value for key, value in os.environ.items()
            if not key.startswith('GIT_')}
