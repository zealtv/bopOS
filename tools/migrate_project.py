#!/usr/bin/env python3
"""Convert an installation once into split project and host registry storage.

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
from migrate_sites import split_geometry, venue_sites


def migrate(source, data_dir, project=None):
    source, root = Path(source), Path(data_dir)
    doc = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("Source must be an installation object")
    project = project or re.sub(r"[^A-Za-z0-9._-]+", "-",
                                str(doc.get("name", "default"))).strip("-._") or "default"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", project):
        raise ValueError("Project folder name must start with a letter or digit")
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
        project_body, default_site = split_geometry(doc)
        sites, skipped = venue_sites(source.parent / "installations", project_body["seats"])
        sites["default"] = default_site
        (path.parent / "sites").mkdir()
        for name, site in sites.items():
            (path.parent / "sites" / (name + ".json")).write_text(json.dumps(site))
        path.write_text(json.dumps(project_body), encoding="utf-8")
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
        (directory / "sites").mkdir()
        for name, site in sites.items():
            site_path = directory / "sites" / (name + ".json")
            with site_path.open("x", encoding="utf-8") as target:
                created.append(site_path)
                json.dump(site, target, indent=2, sort_keys=True)
                target.write("\n")
        for path, body in zip(destinations, (
                json.dumps(project_doc, indent=2, sort_keys=True) + "\n",
                json.dumps(registry, indent=2, sort_keys=True) + "\n", project + "\n")):
            with path.open("x", encoding="utf-8") as target:
                created.append(path)
                target.write(body)
    except Exception:
        for path in reversed(created):
            path.unlink()
        (directory / "sites").rmdir()
        directory.rmdir()
        raise
    for path, reason in skipped:
        print(f"Left {path}: {reason}")
    return destinations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Existing installation.json")
    parser.add_argument("--data-dir", type=Path, default=REPO / "dashboard")
    parser.add_argument("--project", help="Destination project folder name")
    args = parser.parse_args()
    try:
        paths = migrate(args.source, args.data_dir, args.project)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Migration refused: {error}\n")
    for path in paths:
        print(f"Created {path}")
    print(f"Preserved source {args.source}")


if __name__ == "__main__":
    main()
