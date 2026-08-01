#!/usr/bin/env python3
"""Check relative markdown links and images across the doc surface."""
import os
import re
import sys

REPO = "/home/user/bopOS"
DOCS = ["README.md", "docs/ARCHITECTURE.md", "docs/PORTS.md",
        "docs/GETTING-STARTED.md", "docs/INSTALL.md", "docs/COMPOSING.md",
        "docs/OSC-CONTRACT.md", "docs/HARDWARE.md", "docs/PERF.md",
        "docs/VERIFICATION.md", "dashboard/README.md", "patches/README.md",
        "assets/README.md", "python/io/README.md"]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
bad = 0
for doc in DOCS:
    path = os.path.join(REPO, doc)
    base = os.path.dirname(path)
    with open(path, encoding="utf-8") as source:
        text = source.read()
    for target in LINK.findall(text):
        if target.startswith(("http:", "https:", "mailto:", "#")):
            continue
        rel = target.split("#")[0]
        if not rel:
            continue
        resolved = os.path.normpath(os.path.join(base, rel))
        if not os.path.exists(resolved):
            print(f"BROKEN  {doc}: {target}")
            bad += 1
print("checked", len(DOCS), "documents;", bad, "broken links")
sys.exit(1 if bad else 0)
