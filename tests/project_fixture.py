"""Build the split project layout for isolated dashboard test fixtures."""
import json
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
    if path.exists() or path.is_symlink():
        (root / "current-project").write_text("default\n")
    return str(root)
