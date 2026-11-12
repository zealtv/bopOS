"""Build the split project layout for isolated dashboard test fixtures."""
import json
import math
from pathlib import Path


def project_path(root):
    path = Path(root) / "projects" / "default" / "project.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def data_root(path):
    """Finalize a fixture document and return its host data root."""
    path = Path(path)
    root = path.parents[2]
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        doc = None
    if isinstance(doc, dict) and "device_registry" in doc:
        registry = doc["device_registry"]
        (root / "devices.json").write_text(json.dumps(registry))
    if isinstance(doc, dict) and "current_site" not in doc and isinstance(doc.get("seats"), dict):
        # Fixture authors use a compact document; write the actual split layout.
        room = doc.pop("room", {"width": 10, "depth": 8, "origin": [0, 0], "units": "m"})
        listener = doc.pop("listener", {"x": room.get("width", 10) / 2,
            "y": room.get("depth", 8) / 2, "heading": 0,
            "range": min(3, math.hypot(room.get("width", 10), room.get("depth", 8)))})
        positions = {key: seat.pop("positions", []) for key, seat in doc["seats"].items() if isinstance(seat, dict)}
        doc.pop("name", None)
        doc["current_site"] = "default"
        site = path.parent / "sites" / "default.json"
        site.parent.mkdir(exist_ok=True)
        site.write_text(json.dumps({"room": room, "listener": listener, "positions": positions}))
        path.write_text(json.dumps(doc))
    elif isinstance(doc, dict) and doc.get("current_site") == "default":
        site = path.parent / "sites" / "default.json"
        if not site.exists():
            site.parent.mkdir(exist_ok=True)
            site.write_text(json.dumps({"room": {"width": 10, "depth": 8, "origin": [0, 0], "units": "m"},
                "listener": {"x": 5, "y": 4, "heading": 0, "range": 3},
                "positions": {key: [] for key in doc.get("seats", {})} if isinstance(doc.get("seats"), dict) else {}}))
    if path.exists() or path.is_symlink():
        (root / "current-project").write_text("default\n")
    return str(root)
