"""The distribution HTTP surface follows the canonical file visibility rules."""
import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from fastapi import FastAPI
ROOT = Path(__file__).resolve().parents[1]
for source in (ROOT, ROOT / "python", ROOT / "dashboard"):
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
import server

class DistributionDenyTests(unittest.TestCase):
    @staticmethod
    async def request(app, path):
        sent = []
        received = False

        async def receive():
            nonlocal received
            if not received:
                received = True
                return {"type": "http.request", "body": b"", "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        await app({
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [],
            "client": ("test", 1),
            "server": ("test", 80),
        }, receive, send)
        return next(message["status"] for message in sent
                    if message["type"] == "http.response.start")

    def test_visible_nested_content_is_served_and_control_files_are_denied(self):
        with tempfile.TemporaryDirectory(prefix="bopos-static-") as temporary:
            root = Path(temporary)
            nested = root / "alpha" / "content"
            nested.mkdir(parents=True)
            (nested / "data.json").write_text("{}")
            (nested / ".secret").write_text("private")
            (nested / "data.json.part").write_text("incomplete")
            outside = root / "outside.json"
            outside.write_text("outside")
            (nested / "linked.json").symlink_to(outside)
            app = FastAPI()
            app.mount("/patches", server.DistributionStaticFiles(directory=temporary))
            self.assertEqual(asyncio.run(self.request(app, "/patches/alpha/content/data.json")), 200)
            for path in (".secret", "data.json.part", "linked.json"):
                with self.subTest(path=path):
                    self.assertEqual(asyncio.run(self.request(app, "/patches/alpha/content/" + path)), 404)
