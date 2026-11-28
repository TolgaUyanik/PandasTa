# -*- coding: utf-8 -*-
"""NOTICE lists every package module that states an MPL-2.0 origin.

MPL-2.0 is file-level copyleft: a Python file translated from MPL-2.0 Pine stays MPL-2.0, and the
repository must say which files those are. Until 2026-11-28 NOTICE listed only the one tracked
Pine file, while 54 package modules named an MPL-2.0 TradingView source in their docstrings.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MPL = re.compile(r"MPL-2\.0|Mozilla Public License")


def test_every_mpl_module_is_in_notice():
    notice = (ROOT / "NOTICE").read_text(encoding="utf8")
    listed = set(re.findall(r"^\s+(pandas_ta/\S+\.py)\s*$", notice, re.M))
    stated = {p.relative_to(ROOT).as_posix() for p in (ROOT / "pandas_ta").rglob("*.py")
              if MPL.search(p.read_text(encoding="utf8"))}
    assert stated - listed == set(), f"MPL-2.0 modules missing from NOTICE: {sorted(stated - listed)}"
    assert listed - stated == set(), f"NOTICE lists modules with no MPL-2.0 statement: {sorted(listed - stated)}"
