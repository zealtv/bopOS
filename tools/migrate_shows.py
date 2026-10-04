#!/usr/bin/env python3
"""One-off, non-destructive conversion of a project's one show to multiple shows.

The project's `show.json` is copied, byte for byte, to `shows/<its name>.json`
(`shows/Show.json` when its name can't be a file name) and becomes the
project's `current_show`. `show.json` is left where it is and the original
`project.json` is kept as `project.json.pre-shows`.
"""
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
from state import DEFAULT_SHOW, InstallationState
import show_model


def show_name(body):
    """The show's file name, from a strictly valid show document."""
    # Strict where the dashboard is tolerant: it would load a broken file as
    # an empty show and the next edit would replace it.
    doc = show_model.clean_show(json.loads(body.decode("utf-8")))
    if doc is None:
        raise ValueError("Not a valid show")
    name = doc["name"].strip()
    return name if InstallationState.valid_site_name(name) else DEFAULT_SHOW


def install_show(directory, body, backup=True):
    """Write `body` as one of the project's shows and make it current."""
    directory = Path(directory)
    project_path = directory / "project.json"
    original = project_path.read_bytes()
    doc = json.loads(original)
    if not isinstance(doc, dict):
        raise ValueError("Invalid project")
    name = show_name(body)
    destination = directory / "shows" / (name + ".json")
    saved = project_path.with_name("project.json.pre-shows")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"{destination} already exists")
    if backup and (saved.exists() or saved.is_symlink()):
        raise FileExistsError(f"{saved} already exists")
    created_dir = not destination.parent.exists()
    created = []
    try:
        if backup:
            with saved.open("xb") as target:
                created.append(saved)
                target.write(original)
        destination.parent.mkdir(exist_ok=True)
        with destination.open("xb") as target:
            created.append(destination)
            target.write(body)
        doc["current_show"] = name
        InstallationState._write_json(str(project_path), doc)
    except Exception:
        project_path.write_bytes(original)
        for path in reversed(created):
            path.unlink()
        if created_dir and destination.parent.exists():
            destination.parent.rmdir()
        raise
    return destination


def migrate_shows(project_path):
    path = Path(project_path)
    if not InstallationState.valid_site_name(path.parent.name):
        raise ValueError("Project")
    # A stale `current_show` from an installation conversion may be present;
    # the shows/ folder is what says a project has been converted.
    if (path.parent / "shows").exists() or (path.parent / "shows").is_symlink():
        raise FileExistsError("The project already has shows")
    # Without a show.json the dashboard already opens an empty current show.
    return install_show(path.parent, (path.parent / "show.json").read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="The project's project.json")
    args = parser.parse_args()
    try:
        created = migrate_shows(args.project)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Migration refused: {error}\n")
    print(f"Created {created}")
    print(f"Preserved original in {args.project}.pre-shows; show.json left untouched")


if __name__ == "__main__":
    main()
