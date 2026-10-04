#!/usr/bin/env python3
"""Convert an installation once into split project and host registry storage.

`--show FILE` also copies a show file (e.g. `dashboard/shows/test.json`) into
the project's one `show.json`; given alone, it copies it into the existing
current (or `--project`) project. An installation's `current_show` comes
along from its `shows/` folder when no `--show` is given.

The source is preserved. Existing destination files are never overwritten.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
from state import InstallationState
import show_model


def _project_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value or ""):
        raise ValueError("Project folder name must start with a letter or digit")
    return value


def migrate_show(show_file, data_dir, project=None):
    """Copy one show file, byte for byte, to the project's `show.json`."""
    show_file, root = Path(show_file), Path(data_dir)
    if project is None:
        project = (root / "current-project").read_text(encoding="utf-8").strip()
    directory = root / "projects" / _project_name(project)
    if not (directory / "project.json").is_file():
        raise FileNotFoundError(f"No project at {directory}")
    destination = directory / "show.json"
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"{destination} already exists")
    body = show_file.read_bytes()
    # Strict where the dashboard is tolerant: it would load a broken file as
    # an empty show and the next edit would replace it.
    if show_model.clean_show(json.loads(body.decode("utf-8"))) is None:
        raise ValueError(f"{show_file} is not a valid show")
    with destination.open("xb") as target:
        target.write(body)
    return destination


def migrate(source, data_dir, project=None, show_file=None):
    source, root = Path(source), Path(data_dir)
    doc = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("Source must be an installation object")
    project = project or re.sub(r"[^A-Za-z0-9._-]+", "-",
                                str(doc.get("name", "default"))).strip("-._") or "default"
    _project_name(project)
    current_show = doc.get("current_show")
    if show_file is None and isinstance(current_show, str) and current_show.strip():
        # The dashboard loaded a missing current show as an empty one.
        show_file = source.parent / "shows" / (current_show.strip() + ".json")
        if not show_file.is_file():
            show_file = None
    directory = root / "projects" / project
    destinations = (directory / "project.json", root / "devices.json",
                    root / "current-project")
    if directory.exists() or directory.is_symlink() or any(
            path.exists() or path.is_symlink() for path in destinations):
        raise FileExistsError("Destination project, registry or current-project already exists")
    # Use the current validators to reject partial/invalid input, and project
    # only current fields. This is a one-off tool, never a dashboard loader.
    with tempfile.TemporaryDirectory(prefix="bopos-project-migration-") as temporary:
        staging = Path(temporary)
        path = staging / "projects" / project / "project.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(doc), encoding="utf-8")
        (staging / "devices.json").write_text(
            json.dumps(doc.get("device_registry", {})), encoding="utf-8")
        (staging / "current-project").write_text(project + "\n", encoding="utf-8")
        state = InstallationState(staging)
        if state._load_invalid:
            raise ValueError("Source failed project or device registry validation")
        project_doc, registry = state.durable(), state.device_registry
    directory.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for path, body in zip(destinations, (
                json.dumps(project_doc, indent=2, sort_keys=True) + "\n",
                json.dumps(registry, indent=2, sort_keys=True) + "\n", project + "\n")):
            with path.open("x", encoding="utf-8") as target:
                created.append(path)
                target.write(body)
    except Exception:
        for path in reversed(created):
            path.unlink()
        directory.rmdir()
        raise
    if show_file is not None:
        try:
            destinations += (migrate_show(show_file, root, project),)
        except Exception:
            for path in reversed(created):
                path.unlink()
            directory.rmdir()
            raise
    return destinations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?",
                        help="Existing installation.json")
    parser.add_argument("--show", type=Path,
                        help="Show file to copy into the project's show.json")
    parser.add_argument("--data-dir", type=Path, default=REPO / "dashboard")
    parser.add_argument("--project", help="Destination project folder name")
    args = parser.parse_args()
    if args.source is None and args.show is None:
        parser.error("give an installation.json, --show FILE, or both")
    try:
        if args.source is None:
            paths = (migrate_show(args.show, args.data_dir, args.project),)
        else:
            paths = migrate(args.source, args.data_dir, args.project, args.show)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Migration refused: {error}\n")
    for path in paths:
        print(f"Created {path}")
    for source in (args.source, args.show):
        if source is not None:
            print(f"Preserved source {source}")


if __name__ == "__main__":
    main()
