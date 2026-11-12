#!/usr/bin/env python3
"""One-off, non-destructive conversion of project geometry and venue snapshots."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
from state import InstallationState


def split_geometry(doc):
    if (not isinstance(doc, dict) or not isinstance(doc.get("seats"), dict)
            or any(not isinstance(seat, dict) for seat in doc["seats"].values())):
        raise ValueError("Invalid Seats")
    with tempfile.TemporaryDirectory() as temporary:
        validator = InstallationState(temporary)
        validator.data["seats"] = doc["seats"]
        room = validator.clean_room(doc.get("room", validator.DEFAULT_ROOM))
        if room is None:
            raise ValueError("Invalid room")
        validator.data["room"] = room
        site = validator.clean_site({"room": room,
            "listener": doc.get("listener", validator.default_listener()),
            "positions": {key: seat.get("positions", []) for key, seat in doc["seats"].items()}})
    project = copy.deepcopy(doc)
    for key in ("name", "room", "listener"):
        project.pop(key, None)
    project["current_site"] = "default"
    for seat in project["seats"].values():
        seat.pop("positions", None)
    return project, site


def venue_sites(directory, seat_ids):
    sites, skipped = {}, []
    for source in sorted(Path(directory).glob("*.json")):
        try:
            doc = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(doc, dict) or not isinstance(doc.get("seats"), dict) or set(doc["seats"]) != set(seat_ids):
                raise ValueError("Seat ids do not match")
            for key, seat in doc["seats"].items():
                if not isinstance(seat, dict) or str(seat.get("id")) != key:
                    raise ValueError("Seat ids do not match")
            name = source.stem
            if not InstallationState.valid_site_name(name):
                raise ValueError("Site")
            if name == "default" or name in sites:
                raise ValueError("Site name collision")
            _, geometry = split_geometry(doc)
            sites[name] = geometry
        except (OSError, ValueError, TypeError, AttributeError) as error:
            skipped.append((source, str(error)))
    return sites, skipped


def migrate_sites(project_path, venues=None):
    path = Path(project_path)
    if not InstallationState.valid_site_name(path.parent.name):
        raise ValueError("Project")
    original = path.read_bytes()
    doc = json.loads(original)
    sites_dir = path.parent / "sites"
    backup = path.with_name("project.json.pre-sites")
    if "current_site" in doc or sites_dir.exists() or sites_dir.is_symlink() or backup.exists() or backup.is_symlink():
        raise FileExistsError("Site storage or migration backup already exists")
    project, default = split_geometry(doc)
    sites, skipped = venue_sites(venues or path.parents[2] / "installations", project["seats"])
    sites["default"] = default
    # Validate the complete new layout before any destination is touched.
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        staged_project = staging / "projects" / "default" / "project.json"
        staged_project.parent.mkdir(parents=True)
        (staging / "current-project").write_text("default\n")
        staged_project.write_text(json.dumps(project))
        (staged_project.parent / "sites").mkdir()
        for name, site in sites.items():
            (staged_project.parent / "sites" / (name + ".json")).write_text(json.dumps(site))
        state = InstallationState(staging)
        if state._load_invalid:
            raise ValueError("Invalid project")
        project = state.durable()
    created = []
    try:
        with backup.open("xb") as target:
            target.write(original)
        sites_dir.mkdir()
        for name, site in sites.items():
            target = sites_dir / (name + ".json")
            with target.open("x", encoding="utf-8") as output:
                json.dump(site, output, indent=2, sort_keys=True)
                output.write("\n")
            created.append(target)
        InstallationState._write_json(str(path), project)
    except Exception:
        if backup.exists():
            path.write_bytes(original)
        for target in created:
            target.unlink()
        if sites_dir.exists() and not any(sites_dir.iterdir()):
            sites_dir.rmdir()
        raise
    return created, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Existing project.json from project-storage migration")
    parser.add_argument("--venues", type=Path, help="Legacy installations directory")
    args = parser.parse_args()
    try:
        created, skipped = migrate_sites(args.project, args.venues)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"Migration refused: {error}\n")
    for path in created:
        print(f"Created {path}")
    for path, reason in skipped:
        print(f"Left {path}: {reason}")
    print(f"Preserved original in {args.project}.pre-sites; all venue sources left untouched")


if __name__ == "__main__":
    main()
