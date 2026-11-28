# -*- coding: utf-8 -*-
"""NOTICE accounts for every package module derived from a TradingView script.

MPL-2.0 is file-level copyleft: a Python file translated from MPL-2.0 Pine stays MPL-2.0, and the
repository must say which files those are. Until 2026-11-28 NOTICE listed only the one tracked
Pine file. Two checks:

1. every package file stating an MPL-2.0 origin is in NOTICE's MPL list, and nothing else is;
2. every package file citing a TradingView script (`tradingview.com/script/<id>` or
   `pine/<id>-...`) either states its licence (so check 1 covers it), is one of the upstream
   pandas-ta modules that cite a TradingView page as a reference, or is listed in NOTICE as
   "not verified". A new port that cites a script and states no licence fails here: the review
   that found `bpress` missing (its source header says MPL-2.0, its docstring did not) is why.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MPL = re.compile(r"MPL-2\.0|Mozilla Public License")
TV = re.compile(r"tradingview\.com/script/[A-Za-z0-9]{8}|\b[A-Za-z0-9]{8}-[A-Za-z0-9][A-Za-z0-9-]*\.pine\b")
# Modules naming a TradingView script by author/title only (no script id): kept by hand.
NAMED_ONLY: set = set()  # empty on purpose since halftrend was removed and wavetrend got its URL
# Upstream pandas-ta modules (present in pandas-ta 0.4.71b0 or pandas-ta-openbb 0.4.25 under the
# same name) whose docstrings link a TradingView page as a reference, not as a ported source.
UPSTREAM_REFERENCES = {
    "pandas_ta/candles/cdl_inside.py", "pandas_ta/momentum/cmo.py", "pandas_ta/momentum/qqe.py",
    "pandas_ta/momentum/smi.py", "pandas_ta/momentum/squeeze_pro.py", "pandas_ta/overlap/hilo.py",
    "pandas_ta/overlap/kama.py", "pandas_ta/overlap/sinwma.py", "pandas_ta/overlap/ssf.py",
    "pandas_ta/overlap/vidya.py", "pandas_ta/volatility/thermo.py",
}


def _notice_section(title):
    notice = (ROOT / "NOTICE").read_text(encoding="utf8")
    m = re.search(rf"^{re.escape(title)}\n-+\n(.*?)(?=^\S[^\n]*\n-+\n|\Z)", notice, re.M | re.S)
    assert m, f"NOTICE has no section {title!r}"
    return set(re.findall(r"^\s+(pandas_ta/\S+\.py)\s*$", m.group(1), re.M))


def _package():
    return {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf8")
            for p in (ROOT / "pandas_ta").rglob("*.py")}


def test_every_mpl_module_is_in_notice():
    listed = _notice_section("Package modules ported from MPL-2.0 TradingView sources")
    stated = {f for f, s in _package().items() if MPL.search(s)}
    assert stated - listed == set(), f"MPL-2.0 modules missing from NOTICE: {sorted(stated - listed)}"
    assert listed - stated == set(), f"NOTICE lists modules with no MPL-2.0 statement: {sorted(listed - stated)}"


def test_every_tradingview_citation_has_a_licence_statement():
    unverified = _notice_section("Package modules citing a TradingView script whose licence is not verified")
    silent = {f for f, s in _package().items() if TV.search(s) and not MPL.search(s)}
    unaccounted = silent - UPSTREAM_REFERENCES - unverified
    assert unaccounted == set(), (
        f"modules cite a TradingView script but state no licence: {sorted(unaccounted)}; "
        "state the source's licence in the docstring, or list the file in NOTICE as not verified")
    assert NAMED_ONLY <= unverified, f"author/title-only TradingView sources must be listed as not verified: {sorted(NAMED_ONLY - unverified)}"
    stale = (UPSTREAM_REFERENCES | (unverified - NAMED_ONLY)) - silent
    assert stale == set(), f"listed as silent but now state a licence or cite nothing: {sorted(stale)}"
