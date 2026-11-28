# -*- coding: utf-8 -*-
"""The public tree carries no absolute local paths (2026-11-28 clean-up).

Receipts and review files used to quote the owner's run folders and workspace paths
(`/home/<user>/...`, `C:/Users/<user>/...`, `D:\\<workspace>\\...`). They say nothing useful to a
reader of the public repo and expose the owner's machine layout; `{runs}` and `<workspace>` are
the placeholders now. The vendored Pine corpus under docs/pine is excluded (not ours).
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_PATH = re.compile(r"/home/[a-z][a-z0-9_-]*/|\b[A-Za-z]:[\\/]+(?:Users|home)[\\/]")


def test_no_absolute_local_paths_in_tracked_text():
    files = subprocess.run(["git", "ls-files", "*.md", "*.py", "*.csv", "*.json", "*.txt", "*.yml"],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    for rel in files:
        if rel.startswith("docs/pine/") or rel == "tests/test_public_hygiene.py":
            continue
        text = (ROOT / rel).read_text(encoding="utf8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if LOCAL_PATH.search(line):
                hits.append(f"{rel}:{n}")
    assert hits == [], f"absolute local paths: {hits[:20]}"
