# -*- coding: utf-8 -*-
"""`docs/ImplementingAnIndicator.md` lists the touch points and categories the package really has (#331 GEN-3).

The doc is the in-repo porting recipe. Two of its facts drift when the code moves: the files the
generator writes (`docs/new_indicator.py`'s MANIFEST) and the categories (`pandas_ta.Category`).
Both are compared here with the package, so neither can be stale, and the doc must not retype a
count (#331).
"""
import importlib.util
import re
from pathlib import Path

import pandas_ta as ta

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "docs" / "ImplementingAnIndicator.md").read_text(encoding="utf8")


def _generator():
    spec = importlib.util.spec_from_file_location("new_indicator", ROOT / "docs" / "new_indicator.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _section(title):
    m = re.search(rf"^## {title}\n(.*?)(?=^## |\Z)", DOC, re.M | re.S)
    assert m, f"no '## {title}' section"
    return m.group(1)


def test_the_touch_points_match_the_generators_manifest():
    manifest = {p.format(category="<category>", name="<name>") for _, p in _generator().MANIFEST}
    listed = set(re.findall(r"^- `([^`]+)`", _section("Touch points"), re.M))
    assert listed == manifest, f"doc only: {listed - manifest}; generator only: {manifest - listed}"


def test_the_categories_match_the_package():
    line = re.search(r"^Categories: (.+?)\.$", _section("Touch points"), re.M | re.S)
    assert line, "no 'Categories:' line"
    listed = re.findall(r"`([a-z_]+)`", line.group(1))
    assert listed == list(ta.Category), f"doc {listed} vs package {list(ta.Category)}"


def test_the_doc_retypes_no_count():
    retyped = re.findall(r"\b\d+ (?:indicators|categories|touch points)\b", DOC)
    assert retyped == [], f"retyped counts: {retyped}"


def test_every_sibling_repo_path_in_claude_md_is_labelled_owner_only():
    """GEN-4: a public clone has no `../Backtesting` or `../AlternativeRepos`. Each paragraph of
    CLAUDE.md that names one must say "owner-only", so a reader knows the path will not resolve."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf8")
    sibling = re.compile(r"\.\./(?:Backtesting|AlternativeRepos)|[a-zA-Z]:/\w+/Backtesting")
    unlabelled = [p.strip()[:80] for p in re.split(r"\n\s*\n", text)
                  if sibling.search(p) and "owner-only" not in p]
    assert unlabelled == [], f"sibling-repo paths without 'owner-only': {unlabelled}"
