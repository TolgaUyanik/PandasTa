# -*- coding: utf-8 -*-
"""Generate `docs/indicators/<name>.md` — one INDREF reference page per shipped
indicator — plus `docs/indicators/README.md`, the index.

    python docs/gen_indicator_pages.py                 # emit pages from the fact cache
    python docs/gen_indicator_pages.py --refresh-facts # re-measure the slow facts first
    python docs/gen_indicator_pages.py --check         # emit nowhere; fail if a page would change

WHAT "SHIPPED" MEANS HERE, stated once and applied everywhere
--------------------------------------------------------------
`TODO.md`'s INDREF-1 line said "all 201". That number was stale before this ran
(two batches landed after it was written) and it was also ambiguous, because
this package has three different indicator surfaces -- `docs/IndicatorDictionary.md`
§"How many indicators is that, exactly" prints all three from a live probe.

The definition used by THIS generator:

    shipped = every name registered in `pandas_ta.Category`
              + every indicator callable on the package that is NOT registered
              - `ma`

`ma` is excluded because it is a moving-average DISPATCHER -- it returns some
other indicator's output and emits no column of its own.  That is not a
judgement invented here: `gen_indicator_dictionary.py` already carries
`SKIP = {"ma"}`, and the dictionary lists `ta.ma` under *Not indicators*.
Everything else callable gets a page even when `Category` does not know about
it, because "shipped" should mean "a consumer can call it", and the pages for
those names say in the header that a `df.ta.strategy()` sweep will skip them.

The three counts and the page count are printed on every run and written into
the index, so nobody has to retype them.

WHAT IS MACHINE-FILLED AND WHAT IS OWED
---------------------------------------
Machine-filled from a real measurement: the header table's declared rows, §2
(columns / ML form / warm-up / probe range, joined against the parent repo's
`IndicatorMLRegister.md`), §3's module length and first-appearance date, §5's
leak flag (a positive statement about `LEAK_RULES`, not a stub), §10's mining
greps, and §12's Gate F pass count from a full-suite `--junitxml` run.

Owed by a human, and therefore carrying the LITERAL stub token: §1 (what it
measures), §3's provenance identification, §4 (formula as computed here), §6,
§7, §8, §9, §11, and the *effective defaults* header row.  The effective
defaults are NOT machine-filled on purpose: on this fork's ports every validated
parameter is declared `None` and resolved by a `_validated_int` /
`_validated_float` fallback in the function body, so `inspect.signature` says
`None` and substituting the real value into a row labelled "declared signature"
would contradict the dictionary row next to it.  See `_TEMPLATE.md`.

IDEMPOTENCE
-----------
Every slow or clock-dependent input -- the pytest run, the multi-GB
`backtest_results/` scan, the run date -- is frozen in `docs/indicators/_facts.json`
and re-read on later runs.  A plain run is therefore byte-stable: re-running
produces no diff until you pass `--refresh-facts`.  `_facts.json` starts with an
underscore, which is exactly what `tests/test_indref_pages.py::_pages` skips.

THE PROVENANCE COUNTS ARE COMPUTED, NOT TYPED
---------------------------------------------
§13's `n=` counts are produced by importing `tests/test_indref_pages.py` and
running ITS grouping function over the rendered page.  That is deliberate and it
is worth being honest about what it does and does not buy: it means the guard
cannot catch a fabrication introduced BY THIS GENERATOR (the count would move
with it), and it means the guard is doing its real job -- catching a number a
human adds, edits, or deletes on a page AFTERWARDS, which is the failure mode
`_TEMPLATE.md` was written for.  The alternative, hand-typing 233 metrics
blocks, is the hand-bookkeeping the parent repo's knowledge-base v1 died of.
"""
import argparse
import datetime
import importlib.util
import inspect
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PAGES = HERE / "indicators"
FACTS = PAGES / "_facts.json"
PARENT = ROOT.parent / "Backtesting"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import gen_indicator_dictionary as gid  # noqa: E402  (runs the live probe on import)
import pandas_ta as ta  # noqa: E402

#: Hand-written pages this generator must never overwrite.  `tvstop.md` is
#: INDREF-0's worked example and is the reference for how much evidence a
#: section is expected to carry; regenerating it would replace measured content
#: with stubs.
PROTECTED = {"tvstop"}

STUB = "STUB: not measured — fill from %s"

REGISTER = PARENT / "docs" / "knowledgebase" / "IndicatorMLRegister.md"
STRATEGY_MASTER = PARENT / "datastore" / "source" / "StrategyMaster.csv"
BACKTEST_RESULTS = PARENT / "backtest_results"
IE = PARENT / "backtesting_engine" / "indicator_engine.py"
SI = PARENT / "backtesting_engine" / "speedy_indicators.py"
ANALYSIS = PARENT / "scripts" / "analysis"
INDREF2 = PARENT / "docs" / "indicators" / "_indref2_facts.json"

# Campaign documents: batch harnesses that measured many indicators at once.
# The old `measure_<name>_overlap_full.py` filename test cannot see these, so
# ~30 fully-measured indicators were being branded "no campaign has been run".
CAMPAIGN_DOCS = {
    "TalibPortsMeasured.md": "TALIB-1",
    "AltportPortsMeasured.md": "ALTPORT",
    "CandlePatternsMeasured.md": "CANDLE-1",
    "PineAlternatesMeasured.md": "PINEBI-1c",
}

_SWEPT_CACHE = {}


def SWEPT_SET():
    """{indicator: how the engine reaches it} from INDREF-2's measurement.

    Returns {} when that file is absent, and every caller must then fall back
    to naming the limits of its own scan rather than asserting a negative.
    """
    if _SWEPT_CACHE:
        return _SWEPT_CACHE.get("d", {})
    d = {}
    if INDREF2.is_file():
        try:
            f = json.loads(INDREF2.read_text(encoding="utf8"))
        except (ValueError, OSError):
            f = {}
        specs = set(f.get("specs") or [])
        imported = set(f.get("imported") or [])
        called = set(f.get("called") or [])
        for n in specs | imported | called:
            how = []
            if n in specs:
                how.append("`INDICATOR_SPECS` bulk dispatch")
            if n in imported:
                how.append("imported alias")
            if n in called:
                how.append("literal call site")
            d[n] = " + ".join(how)
    _SWEPT_CACHE["d"] = d
    return d


_ANALYSIS_CACHE = {}


def ANALYSIS_CALLERS():
    """{indicator: (script, …)} for every `scripts/analysis/*.py` that calls it.

    INDREF-2's facts cover only the two engine modules, so a page that said
    "not reached by any call path" was denying call sites nobody had looked
    for.  This is the scan that makes the narrower claim checkable.
    """
    if _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE.get("d", {})
    d = {}
    if ANALYSIS.is_dir():
        for p in sorted(ANALYSIS.glob("*.py")):
            try:
                src = p.read_text(encoding="utf8", errors="replace")
            except OSError:
                continue
            found = set(re.findall(r"\bta\.([a-z_0-9]+)\s*\(", src))
            found |= set(re.findall(r"\.ta\.([a-z_0-9]+)\s*\(", src))
            for m in re.finditer(r"from\s+pandas_ta[.\w]*\s+import\s+([^\n(]+)", src):
                for piece in m.group(1).split(","):
                    found.add(piece.strip().split(" as ")[0].strip())
            for n in found:
                d.setdefault(n, []).append(p.name)
    _ANALYSIS_CACHE["d"] = {k: tuple(v) for k, v in d.items()}
    return _ANALYSIS_CACHE["d"]


def CAMPAIGN_FOR(name, cols):
    """Which batch campaign doc records a measurement for this indicator.

    The test is the indicator's own EMITTED COLUMN NAMES, not its function
    name.  A campaign doc names plenty of indicators it did not measure --
    `atr`, `ema`, `stoch` and friends run all through them as Gate E
    *comparators* -- so matching the function name marks 47 indicators
    measured where the campaigns ported roughly 30.  A shipped column name
    (`ATRwr_14`, `CVI_10_10`) is specific to the port, so it is the honest
    signal.  Columns under 4 characters are skipped as too collision-prone
    to carry the claim.
    """
    probes = [c for c in (cols or []) if c and len(c) >= 4]
    if not probes:
        # The five indicators whose dictionary probe RAISES have no probed
        # columns, so the column-name test cannot run at all.  Returning []
        # here made "could not look" indistinguishable from "looked and found
        # nothing", and branded `sarext` -- whose Gate E (rho +0.9850,
        # n=408,075) is in a tracked file -- as uncampaigned.  Fall back to the
        # declared stem, which is what the campaign docs actually tabulate.
        probes = [name.upper()]
    hits = []
    for doc, tag in sorted(CAMPAIGN_DOCS.items()):
        p = HERE / doc
        if not p.is_file():
            continue
        try:
            src = p.read_text(encoding="utf8", errors="replace")
        except OSError:
            continue
        if any(re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(c), src)
               for c in probes):
            hits.append((doc, tag))
    return hits


# --------------------------------------------------------------- the name set

def module_path(name):
    fn = getattr(ta, name, None)
    mod = inspect.getmodule(fn)
    if mod is None or not getattr(mod, "__file__", None):
        return None
    p = Path(mod.__file__).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def shipped():
    """{name: {"category":…, "registered":bool, "ext":bool}} — see the module docstring."""
    from pandas_ta.core import AnalysisIndicators as AI

    not_indicators = {"above", "above_value", "below", "below_value", "cross",
                      "cross_value", "constants", "indicators", "strategy", "ticker"}
    registered = {n: c for c, names in ta.Category.items() for n in names}
    accessor = {n for n, v in vars(AI).items()
                if not n.startswith("_") and inspect.isfunction(v)} - not_indicators
    module_only = {n for n in dir(ta)
                   if not n.startswith("_") and callable(getattr(ta, n, None))
                   and n not in registered and n not in accessor
                   and n in ("ma", "drawdown", "vp")}

    out = {}
    for n in sorted(set(registered) | accessor | module_only):
        if n == "ma":                      # dispatcher, not an indicator
            continue
        if not callable(getattr(ta, n, None)):
            continue
        mp = module_path(n)
        if mp and mp.startswith("pandas_ta/"):
            cat = mp.split("/")[1]
        else:
            cat = registered.get(n, "—")
        out[n] = {"category": registered.get(n, cat),
                  "registered": n in registered,
                  "ext": n in accessor,
                  "module": mp}
    return out, registered, accessor, sorted(module_only)


# ------------------------------------------------------------------ the probe

def probe(names):
    """{name: rec} reusing the dictionary generator's probe verbatim.

    `gid.out` already holds every name the dictionary covers; the handful this
    generator adds (the callable-but-unregistered ones the dictionary's `cats`
    loop never sees) are probed here with the SAME helpers, so a column's ML
    form on a page and in the dictionary can never disagree."""
    have = {}
    for cat, recs in gid.out.items():
        for n, r in recs.items():
            have[n] = r
    recs = {}
    for n in names:
        if n in have:
            recs[n] = have[n]
            continue
        fn = getattr(ta, n)
        title, dsc = gid.summary(fn)
        rec = {"title": title, "desc": dsc, "signature": str(inspect.signature(fn)),
               "ext": True, "cols": [], "error": None}
        try:
            r1 = gid.as_frame(gid.call(fn, gid.df1.copy(deep=True)))
            r2 = gid.as_frame(gid.call(fn, gid.df2.copy(deep=True)))
            if r1 is None:
                rec["error"] = "no frame/series returned"
            else:
                for c in r1.columns:
                    if r2 is not None and c in r2.columns:
                        scale, warm, rng_ = gid.classify(r1[c], r2[c])
                    else:
                        scale, warm, rng_ = "unknown", None, None
                    ov = gid.FORM_OVERRIDES.get(n)
                    if ov and ov[0](str(c)):
                        scale = ov[1]
                    rec["cols"].append({"name": str(c), "scale": scale,
                                        "warmup": warm, "range": rng_})
        except Exception as e:                                   # noqa: BLE001
            rec["error"] = "%s: %s" % (type(e).__name__, e)
        if n in gid.PROBE_CANNOT_CONSTRUCT and rec.get("error"):
            rec["error"] = None
            rec["probe_note"] = ("not probed: %s -- harness limitation, not a "
                                 "runtime break" % gid.PROBE_CANNOT_CONSTRUCT[n])
        recs[n] = rec
    return recs


STEM_RE = re.compile(r"(?:_-?\d+(?:\.\d+)?)+$")


def stem(col):
    """`STOCHk_14_3_3` -> `STOCHk`; `TVS_DIR_14_3.0` -> `TVS_DIR`.

    The parameter tail is what a mined rule varies, so the tail is what a grep
    for "did mining ever pick this indicator up" must drop."""
    s = STEM_RE.sub("", str(col))
    return s or str(col)


# ------------------------------------------------------------- the slow facts

def junit_counts(xml_path):
    """{'tests.test_x': {'passed': n, ...}} from a pytest --junitxml run."""
    per, totals = {}, {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    root = ET.parse(xml_path).getroot()
    for tc in root.iter("testcase"):
        mod = tc.get("classname", "").split(".")
        mod = ".".join(mod[:2]) if len(mod) >= 2 else tc.get("classname", "")
        kind = "passed"
        for child in tc:
            if child.tag in ("failure", "error", "skipped"):
                kind = {"failure": "failed"}.get(child.tag, child.tag)
        d = per.setdefault(mod, {"passed": 0, "failed": 0, "error": 0, "skipped": 0})
        d[kind] += 1
        totals[kind] += 1
    return per, totals


def scan_backtest_results(stems):
    """{stem: n files under backtest_results/ mentioning it}.

    ONE pass over the tree.  `backtest_results/` was 383 non-image files / 4.9 GB
    when this last ran, most of it in two very large trade-ledger CSVs, so the
    per-indicator `grep -rl` the template describes -- 233 of them -- would
    re-read the whole tree 233 times.  Same answer, one read.  The size is
    printed on every `--refresh-facts` run rather than baked in here.
    `.gitignore` is deliberately not honoured: `backtest_results/<batch>/` is
    ignored, which is why the template makes `--no-ignore-files` mandatory."""
    if not BACKTEST_RESULTS.is_dir():
        return {}
    pats = sorted({s for s in stems if len(s) >= 3})
    if not pats:
        return {}
    # Boundary-aware: a stem must not be glued to another word.  A bare
    # substring search for a 3-letter stem like `ISA` matches inside unrelated
    # tokens and turns an occurrence count into noise.  A trailing `_` or digit
    # IS allowed, because that is exactly the parameter tail `stem()` stripped.
    rx = re.compile(("(?<![A-Za-z0-9])(?:%s)(?![A-Za-z])"
                     % "|".join(re.escape(p) for p in pats)).encode())
    overlap = max(len(p) for p in pats) + 2
    hits = {p: 0 for p in pats}
    files = [p for p in sorted(BACKTEST_RESULTS.rglob("*"))
             if p.is_file() and p.suffix.lower() not in (".png", ".jpg", ".jpeg")]
    total = sum(p.stat().st_size for p in files)
    done = 0
    print("  scanning %d files / %.1f GB under backtest_results/ "
          "(images excluded) — this is the slow half of --refresh-facts"
          % (len(files), total / 1e9), flush=True)
    for path in files:
        if not path.is_file():
            continue
        seen = set()
        try:
            with open(path, "rb") as fh:
                carry = b""
                while True:
                    chunk = fh.read(1 << 22)
                    if not chunk:
                        break
                    buf = carry + chunk
                    for m in rx.finditer(buf):
                        seen.add(m.group(0).decode())
                    # A stem can straddle a chunk boundary; carry the longest
                    # pattern's worth of tail so it is still seen next round.
                    carry = buf[-overlap:] if overlap else b""
        except OSError:
            continue
        for s in seen:
            hits[s] += 1
        done += path.stat().st_size
        print("    %5.1f%%  %s" % (100.0 * done / total if total else 100.0,
                                   path.name), flush=True)
    return hits


def scan_strategy_master(stems):
    if not STRATEGY_MASTER.is_file():
        return {}
    text = STRATEGY_MASTER.read_text(encoding="utf8", errors="replace")
    lines = text.splitlines()
    out = {}
    for s in stems:
        if len(s) < 3:
            continue
        rx = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z])" % re.escape(s))
        out[s] = sum(1 for ln in lines if rx.search(ln))
    return out


def scan_engine(names):
    out = {}
    for label, path in (("IE", IE), ("SI", SI)):
        text = path.read_text(encoding="utf8", errors="replace") if path.is_file() else ""
        for n in names:
            rx = re.compile(r"(?:\bta\.%s\s*\(|\.ta\.%s\s*\()" % (re.escape(n), re.escape(n)))
            out.setdefault(n, {})[label] = len(rx.findall(text))
    return out


def git_added(names, modules):
    out = {}
    for n in names:
        mp = modules.get(n)
        if not mp:
            out[n] = None
            continue
        try:
            r = subprocess.run(
                ["git", "log", "--diff-filter=A", "--format=%ad", "--date=short",
                 "-1", "--", mp],
                cwd=str(ROOT), capture_output=True, text=True, timeout=60)
            out[n] = (r.stdout.strip().splitlines() or [None])[0]
        except Exception:                                        # noqa: BLE001
            out[n] = None
    return out


def refresh_facts(names, modules, stems_by_name):
    print("refreshing facts — this runs the full pytest suite and reads "
          "backtest_results/ once; expect several minutes")
    tmp = HERE / "_junit_indref.xml"
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--no-header",
                        "-p", "no:cacheprovider", "--junitxml", str(tmp)],
                       cwd=str(ROOT), capture_output=True, text=True)
    per, totals = junit_counts(tmp) if tmp.is_file() else ({}, {})
    tmp.unlink(missing_ok=True)
    print("  pytest exit=%s totals=%s" % (r.returncode, totals))

    all_stems = sorted({s for v in stems_by_name.values() for s in v})
    facts = {
        "date": datetime.date.today().isoformat(),
        "pytest": {"per_module": per, "totals": totals, "exit": r.returncode},
        "strategy_master": scan_strategy_master(all_stems),
        "backtest_results": scan_backtest_results(all_stems),
        "engine": scan_engine(names),
        "git_added": git_added(names, modules),
    }
    FACTS.parent.mkdir(parents=True, exist_ok=True)
    FACTS.write_text(json.dumps(facts, indent=1, sort_keys=True) + "\n", encoding="utf8")
    return facts


def load_facts():
    if FACTS.is_file():
        return json.loads(FACTS.read_text(encoding="utf8"))
    return {"date": datetime.date.today().isoformat(), "pytest": {},
            "strategy_master": {}, "backtest_results": {}, "engine": {},
            "git_added": {}}


# ------------------------------------------------------------- register join

def load_register():
    """{column name: verdict} from the parent repo's per-column ML register."""
    out = {}
    if not REGISTER.is_file():
        return out
    for ln in REGISTER.read_text(encoding="utf8", errors="replace").splitlines():
        if not ln.startswith("| "):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("Verdict", "---------"):
            continue
        col = cells[1].strip("`")
        if col and re.fullmatch(r"[\w.\-]+", col):
            out.setdefault(col, cells[0])
    return out


def register_verdict(reg, name, col):
    for key in (col, "%s_%s" % (name, col)):
        if key in reg:
            return reg[key], key
    return None, None


# -------------------------------------------------------------- the guard API

def load_guard():
    spec = importlib.util.spec_from_file_location(
        "_indref_guard", ROOT / "tests" / "test_indref_pages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ rendering

def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def fence(text, lang=""):
    """Machine-quoted source text.  Fenced on purpose: the guard skips fenced
    blocks, and a docstring is a quotation, not a claim this page is making."""
    return ["```" + lang] + [ln.rstrip() for ln in str(text).splitlines()] + ["```"]


def doc_sources(mod_file):
    """The `Sources:` block of the module docstring, verbatim, or None."""
    if not mod_file:
        return None
    p = ROOT / mod_file
    if not p.is_file():
        return None
    try:
        tree = __import__("ast").parse(p.read_text(encoding="utf8", errors="replace"))
    except SyntaxError:
        return None
    doc = __import__("ast").get_docstring(tree) or ""
    keep, on = [], False
    for ln in doc.splitlines():
        s = ln.strip()
        if re.match(r"(?i)^sources?\s*:", s):
            on = True
            continue
        if on:
            if s and re.match(r"(?i)^(calculation|args|kwargs|returns|note)s?\s*:", s):
                break
            if s:
                keep.append(s)
            elif keep:
                break
    return "\n".join(keep) or None


def render(name, meta, rec, facts, reg, guard):
    cat = meta["category"]
    mod = meta["module"] or "pandas_ta/%s/%s.py" % (cat, name)
    mod_abs = ROOT / mod
    cols = rec.get("cols") or []
    L = []
    A = L.append

    title = (rec.get("title") or "").strip().rstrip(".") or name
    A("# `%s` — %s" % (name, esc(title)))
    A("")

    harness = ANALYSIS / ("measure_%s_overlap_full.py" % name)
    harness_rel = "../Backtesting/scripts/analysis/measure_%s_overlap_full.py" % name
    has_harness = harness.is_file()
    # ONE source of truth for campaign coverage.  The banner used to run its
    # own filename-only test while §7 ran CAMPAIGN_FOR, so on every page where
    # a campaign was found the two cells contradicted each other -- the banner
    # is the first line a reader sees, and it was still printing the
    # unmeasured absolute this fix exists to remove.
    campaigns = CAMPAIGN_FOR(name, [c.get("name") for c in cols])
    if has_harness:
        gate_cov = ("a dedicated overlap harness exists (`%s`) but its CSVs were not "
                    "opened by this generator: §7–§9 are stubs naming it" % harness_rel)
    elif campaigns:
        gate_cov = ("measurements naming this indicator's columns are recorded in %s "
                    "(§7) — that match does not distinguish a ported column from a "
                    "Gate E comparator, so read the campaign doc"
                    % ", ".join("`docs/%s`" % d for d, _ in campaigns))
    else:
        gate_cov = ("this generator found no campaign record for this indicator: "
                    "§6–§9 are stubs")

    A("> **INDREF page — GENERATED by `docs/gen_indicator_pages.py`** (INDREF-1). Section names and")
    A("> citation discipline match the parent repo's family docs")
    A("> (`../Backtesting/docs/indicators/family-*.md`); the shape is fixed by")
    A("> [`_TEMPLATE.md`](_TEMPLATE.md) and the worked example is [`tvstop.md`](tvstop.md).")
    A("> Code anchors are FUNCTION NAMES or immutable Pine/C source line numbers, never a bare")
    A("> Python line number.")
    A(">")
    A("> **MEASUREMENT LAW.** Everything on this page was read from a live probe, a file on disk, or")
    A("> a run recorded in `_facts.json`. **Nothing here was hand-asserted.** Fields no measurement")
    A("> covers carry the literal stub token instead of a plausible value.")
    A(">")
    A("> **Gate coverage:** %s." % gate_cov)
    A(">")
    A("> **Owed by a human, and marked as such below:** §1 (what it measures), §3 (which source this")
    A("> was ported from), §4 (formula as computed here), §6, §11, and the *effective defaults* row.")
    A("")

    # ---- header table
    if meta["registered"]:
        reg_cell = "yes — `Category['%s']`, so `df.ta.strategy()` sweeps it" % meta["category"]
    else:
        reg_cell = ("**no** — callable but absent from `Category`, so a `df.ta.strategy()` "
                    "sweep and the category runs skip it")
    if meta["ext"]:
        acc_cell = "yes — `df.ta.%s()`" % name
    else:
        acc_cell = "**no — standalone**; call `ta.%s(...)` and join the result yourself" % name

    tmod = "tests/test_%s.py" % name
    pk = "tests.test_%s" % name
    pcounts = (facts.get("pytest", {}).get("per_module", {}) or {}).get(pk)
    if pcounts:
        tests_cell = ("`%s` — %d passed / %d skipped, `python -m pytest %s -q`, %s"
                      % (tmod, pcounts["passed"], pcounts["skipped"], tmod, facts["date"]))
    elif (ROOT / tmod).is_file():
        tests_cell = "`%s` exists but produced no case in the recorded full-suite run" % tmod
    else:
        tests_cell = ("no `%s`; covered only by the suite-wide guards "
                      "(`tests/test_wiring_accessors.py`, the category suites)" % tmod)

    eng = (facts.get("engine", {}) or {}).get(name, {})
    ie_n, si_n = eng.get("IE", 0), eng.get("SI", 0)
    # A `ta.<name>(` grep is STRUCTURALLY BLIND to the two ways the engine
    # actually reaches most indicators: `getattr(ta, func_name)` over
    # `AdvancedIndicatorCalculator.INDICATOR_SPECS` (104 entries) and
    # `from pandas_ta.x import y as _y` aliases.  It sees 26; the true swept
    # set is 171.  Stating the grep's blindness as "not called by the parent
    # engine" was an unmeasured absolute -- exactly what this repo forbids.
    # INDREF-2's measurement is the authority; fall back to naming the scan.
    swept = SWEPT_SET()
    if name in swept:
        how = swept[name]
        wire = "**called by the parent engine** — %s" % how
        if ie_n or si_n:
            wire += " (`IE:` %d, `SI:` %d literal `ta.%s(` site(s))" % (ie_n, si_n, name)
    elif ie_n or si_n:
        wire = "`IE:` %d call site(s), `SI:` %d — grep `ta.%s(`" % (ie_n, si_n, name)
    elif swept:
        # "not reached by ANY engine call path" was a fresh absolute the
        # source cannot support: `_indref2_facts.json` only covers
        # indicator_engine.py and speedy_indicators.py.  27 of the 62 are
        # imported or called by the Gate-E scripts under scripts/analysis/,
        # which the cell must not deny.  Scope the claim, and count them.
        n_ge = len(ANALYSIS_CALLERS().get(name, ()))
        wire = ("**not reached by the engine** — absent from `INDICATOR_SPECS`, "
                "the import aliases and the `ta.%s(` scan of "
                "`indicator_engine.py` / `speedy_indicators.py` (INDREF-2 §5b). "
                "Call sites outside those two modules are a separate question: "
                % name)
        wire += ("**%d Gate-E/analysis script(s)** under "
                 "`../Backtesting/scripts/analysis/` do call it" % n_ge
                 if n_ge else
                 "no script under `../Backtesting/scripts/analysis/` calls it either")
    else:
        wire = ("no literal `ta.%s(` call site; a `getattr`/alias dispatch is "
                "not visible to this scan" % name)

    added = (facts.get("git_added", {}) or {}).get(name)
    status = ("module first appears in this repo's history %s "
              "(`git log --diff-filter=A -- %s`)" % (added, mod)) if added else (
        "STUB: not measured — fill from docs/indicators/_facts.json")

    A("| | |")
    A("|---|---|")
    A("| Module | `%s` |" % mod)
    A("| Category | `%s` |" % cat)
    A("| Registered in `Category` | %s |" % reg_cell)
    A("| Accessor | %s |" % acc_cell)
    A("| Tests | %s |" % tests_cell)
    A("| Inputs | %s |" % gid.inputs(rec.get("signature", "()")))
    A("| Params (**declared signature**) | %s |" % gid.params(rec.get("signature", "()")))
    A("| Params (**effective defaults**) | %s |" % (STUB % mod))
    warms = [c["warmup"] for c in cols if isinstance(c.get("warmup"), int) and c["warmup"] >= 0]
    A("| Warm-up (dictionary probe) | %s |"
      % (max(warms) if warms
         else ("**probe raised — see §2**" if rec.get("error")
               else "— no probed column")))
    A("| Engine wiring | %s |" % wire)
    A("| Provenance | %s |" % (STUB % mod))
    A("| Status | %s |" % status)
    A("")

    # ---- 1
    A("## 1. What it measures")
    A("")
    A("%s" % (STUB % mod))
    A("")
    A("The generator will not write this paragraph. `_TEMPLATE.md` is explicit that the docstring's")
    A("first sentence is a **seed, not an answer**: §1 has to say what economic quantity the column")
    A("carries and, where a column was built and not shipped, why. Below is the seed, quoted from the")
    A("module docstring so a reader can see exactly how much of §1 is still owed.")
    A("")
    L.extend(fence("\n".join(x for x in [rec.get("title") or "", rec.get("desc") or ""] if x)
                   or "(the module carries no docstring)"))
    A("")

    # ---- 2
    A("## 2. Columns and ML form")
    A("")
    if rec.get("probe_note"):
        A("⚠ **Not probed.** %s" % esc(rec["probe_note"]))
        A("")
    elif rec.get("error"):
        A("⚠ **The probe could not call this indicator:** `%s`" % esc(rec["error"])[:160])
        A("")
        A("This is a **probe result, not a verdict on the indicator**: an empty §2 table below means")
        A("the harness could not obtain columns, NOT that the indicator emits none. Whether the same")
        A("call fails for a consumer (`df.ta.%s()`) or only under the probe's kwargs is" % name)
        A("**not determined here** and has no ticket — see the index's caveat.")
        A("")
    A("Machine-filled from the live probe in `docs/gen_indicator_dictionary.py` (synthetic 600-bar")
    A("OHLCV frame, computed twice with price ×137). The register verdict is joined on column name")
    A("from `../Backtesting/docs/knowledgebase/IndicatorMLRegister.md` and copied verbatim; \"no row\"")
    A("means the engine's production config does not emit a column of that name, which is a fact")
    A("about the engine, not about this indicator.")
    A("")
    A("| Column | Dictionary ML form | warm-up | observed range on the probe fixture | Register verdict |")
    A("|---|---|---|---|---|")
    if not cols:
        A("| — no column probed | — | — | %s | — |" % (STUB % "docs/gen_indicator_dictionary.py"))
    for c in cols:
        v, key = register_verdict(reg, name, c["name"])
        rng_ = c.get("range")
        rng_cell = ("%.6g … %.6g" % (rng_[0], rng_[1])) if rng_ else "— no value on the fixture"
        A("| `%s` | `%s` | %s | %s | %s |"
          % (esc(c["name"]), gid.tag(c["scale"]),
             c["warmup"] if isinstance(c.get("warmup"), int) and c["warmup"] >= 0 else "—",
             rng_cell,
             ("%s (as `%s`)" % (v, key)) if v else "no row"))
    A("")
    A("Per-column one-line descriptions are owed with §1: %s" % (STUB % mod))
    A("")
    A("⚠ A probe `range` is a **fixture measurement, not a bound**. Real-data extremes, where")
    A("measured, belong in §6.")
    A("")
    A("⚠ A `CONST` tag means the column never fired *on the synthetic probe frame*. That is a flag to")
    A("check on real data, not a verdict — `fvg`'s `IN_FVG_*` were diagnosed dead on synthetic frames")
    A("and were alive on real prices (`CLAUDE.md`, FVGDEAD).")
    A("")

    # ---- 3
    A("## 3. Provenance")
    A("")
    nlines = 0
    nbytes = 0
    if mod_abs.is_file():
        raw = mod_abs.read_bytes()
        nbytes = len(raw)
        nlines = raw.count(b"\n")
    A("| | |")
    A("|---|---|")
    A("| Source | %s |" % (STUB % mod))
    A("| Module length | %d newline-terminated lines, %d bytes (`grep -c '' %s`) |"
      % (nlines, nbytes, mod))
    A("| Version / licence | %s |" % (STUB % mod))
    A("| TA-Lib equivalent | %s |" % (STUB % "docs/TalibPortsMeasured.md"))
    A("| Gate A anchor | %s |" % (STUB % mod))
    A("")
    src = doc_sources(mod)
    if src:
        A("The module docstring names its own sources; quoted verbatim, unverified by this generator:")
        A("")
        L.extend(fence(src))
    else:
        A("The module docstring carries no `Sources:` block, so the generator has nothing to quote")
        A("and the rows above stay stubs. Identifying the source — upstream pandas-ta, a Pine script")
        A("in `docs/pine/`, or a TA-Lib C function — is the hand-written half of this page.")
    A("")

    # ---- 4
    A("## 4. Formula AS COMPUTED HERE")
    A("")
    A("%s" % (STUB % mod))
    A("")
    A("A transliteration and its deliberate divergences from the source — NaN handling, unenforced UI")
    A("slider bounds, `int/int` being fractional in Pine v6, `ddof=0` for `ta.stdev(biased=true)` —")
    A("cannot be read off a probe. The module body is the only record until someone writes this.")
    A("")

    # ---- 5
    A("## 5. Causality (Gate B)")
    A("")
    rule = gid.LEAK_RULES.get(name)
    if rule:
        leaking = [c["name"] for c in cols if rule[0](c["name"])] or ["(every column)"]
        A("**A documented leak.** `LEAK_RULES` in `docs/gen_indicator_dictionary.py` records this")
        A("indicator as not causal at default parameters, for %s:"
          % ", ".join("`%s`" % x for x in leaking))
        A("")
        A("> %s" % esc(rule[1]))
        A("")
        A("This is the probe's own output, re-read this run, not a quotation.")
    else:
        A("`LEAK_RULES` in `docs/gen_indicator_dictionary.py` records **no** causality exception for")
        A("this indicator, and the dictionary's *Leak watchlist* therefore does not list it. That is a")
        A("positive statement about a real probe output, so it is not a stub — but it is also not")
        A("Gate B: `LEAK_RULES` is a hand-maintained list of KNOWN leaks, and only a mutant test")
        A("(`importlib`-read the module, shift a write index earlier, `exec` it, show the real module")
        A("clean and the mutant caught) proves the absence of back-dating. No such test is recorded")
        A("for this indicator unless §12 says otherwise.")
    A("")

    # ---- 6
    A("## 6. ML-suitability (Gate D)")
    A("")
    A("The `×137` scale ratio behind each ML-form tag in §2 is the dictionary probe's, measured on one")
    A("synthetic frame. Gate D is stricter — ×8/×64 bit-identical, ×10/×3.7 within tolerance with NaN")
    A("masks matching, and `0 < fires < n` so a constant column cannot pass — and no such run is")
    A("recorded here.")
    A("")
    A("%s" % (STUB % ("tests/test_%s.py" % name)))
    A("")

    # ---- 7
    A("## 7. Overlap (Gate E)")
    A("")
    if has_harness:
        A("A harness exists at `%s`. Its CSVs live under the parent repo's gitignored" % harness_rel)
        A("`backtest_results/`, were not opened by this generator, and are not quoted here — quoting a")
        A("ρ whose artifact you did not open is the exact defect these pages exist to prevent.")
        A("")
        A("%s" % (STUB % harness_rel))
    else:
        camp = campaigns
        if camp:
            A("**A batch campaign document carries measurements naming this indicator's columns.**")
            A("There is no `%s`, because the campaigns gated many" % harness_rel)
            A("indicators in one run rather than one harness each:")
            A("")
            for doc, tag in camp:
                A("- **%s** — per-column Gate A/C/D/E record in [`docs/%s`](../%s)."
                  % (tag, doc, doc))
            A("")
            A("⚠ **This match is by column name, and it does not distinguish a column the campaign")
            A("*ported* from one it used as a Gate E *comparator*.** Both appear in the document.")
            A("Open it to see which this indicator is — that is a two-line read and this generator")
            A("will not guess it for you. The ρ values, sample sizes and ship/revert verdicts are")
            A("there; they are deliberately not re-quoted here, because quoting a ρ whose artifact")
            A("you did not open is the exact defect these pages exist to prevent.")
        else:
            A("**This generator found no campaign record for this indicator.** There is no")
            A("`%s`, and none of the batch campaign documents" % harness_rel)
            A("(%s) names any of this"
              % ", ".join("`docs/%s`" % d for d in sorted(CAMPAIGN_DOCS)))
            A("indicator's emitted column names. **That is what the scan tested — column names, not")
            A("prose mentions** — so it is a statement about this scan, not proof that no")
            A("measurement exists. To start")
            A("a campaign, copy any existing `measure_*_overlap_full.py` and grid the shipped")
            A("columns against `IndicatorEngine(include_advanced=True).compute_all()`.")
            A("")
            A("%s" % (STUB % harness_rel))
    A("")
    A("Ship line: ρ ≈ 0.9 → revert · 0.76–0.80 → ship with disclosure · below 0.76 → ship.")
    A("")

    # ---- 8
    A("## 8. Reachability (Gate C)")
    A("")
    A("Per-frame firing counts against `BeamMiner(min_support=30)`")
    A("(`../Backtesting/backtesting_engine/contract_miner.py`). A pooled pass with most frames below")
    A("`min_support` is a PARTIAL, not a PASS.")
    A("")
    A("%s" % (STUB % harness_rel))
    A("")

    # ---- 9
    A("## 9. BIST specifics")
    A("")
    A("Behaviour on the DI-5 / DI-5b contaminated frames (`MGROS.IS`, `ARCLK.IS`) against clean")
    A("controls, and the SHAPE of any failure — suppression, fabrication, or a pinned value.")
    A("")
    A("%s" % (STUB % harness_rel))
    A("")

    # ---- 10
    A("## 10. Mining track record")
    A("")
    stems = sorted({stem(c["name"]) for c in cols} or {name.upper()})
    sm = facts.get("strategy_master", {}) or {}
    br = facts.get("backtest_results", {}) or {}
    A("Column-name stems (the parameter tail is what a mined rule varies, so the grep drops it):")
    A("")
    L.extend(fence("\n".join(
        "grep -c '%s' ../Backtesting/datastore/source/StrategyMaster.csv\n"
        "grep -rl --no-ignore-files '%s' ../Backtesting/backtest_results/" % (s, s)
        for s in stems), "sh"))
    A("")
    A("| stem | lines in `StrategyMaster.csv` | files under `backtest_results/` |")
    A("|---|---|---|")
    tot_sm = tot_br = 0
    for s in stems:
        a = sm.get(s)
        b = br.get(s)
        tot_sm += a or 0
        tot_br += b or 0
        miss = ("not scanned — stem shorter than 3 characters, which would match "
                "everything" if len(s) < 3 else STUB % "docs/indicators/_facts.json")
        A("| `%s` | %s | %s |"
          % (esc(s), a if a is not None else miss, b if b is not None else miss))
    A("")
    if any(len(s) < 5 for s in stems):
        A("⚠ At least one stem above is shorter than five characters. Even with the boundary rule")
        A("the generator applies (a stem must not be glued to a letter on either side), a short stem")
        A("can still collide with an unrelated token, so read these two columns as an upper bound.")
        A("")
    if tot_sm == 0 and tot_br == 0:
        A("**Nothing in either.** This generator cannot tell you whether that means *no mining sweep")
        A("has run since this module landed* or *swept and never selected* — those have opposite")
        A("consequences and separating them needs the mining-run inventory that is INDREF-2's job, not")
        A("this page's. Do not read a zero here as \"no edge\".")
    else:
        A("The counts above are occurrences, not selections: a stem can appear in a results file")
        A("because the sweep *offered* the column, not because a rule kept it. Turning occurrence into")
        A("selection is INDREF-2's job.")
    A("")
    A("⚠ `--no-ignore-files` is mandatory in the second grep: the parent repo's default `grep` is a")
    A("ugrep wrapper honouring `.gitignore`, and `backtest_results/<batch>/` is ignored there. The")
    A("counts above come from one direct read of the tree, which honours no ignore file at all.")
    A("")

    # ---- 11
    A("## 11. Improvement ideas")
    A("")
    A("%s" % (STUB % mod))
    A("")

    A("---")
    A("")

    # ---- 12
    A("## 12. Gate ledger")
    A("")
    totals = (facts.get("pytest", {}) or {}).get("totals") or {}
    exit_code = (facts.get("pytest", {}) or {}).get("exit")
    if pcounts:
        gf = ("%d passed / %d skipped in `%s`, recorded full-suite run %s"
              % (pcounts["passed"], pcounts["skipped"], tmod, facts["date"]))
    elif totals:
        gf = ("no dedicated test module; the recorded full-suite run was "
              "%d passed / %d failed / %d error / %d skipped, pytest exit %s, %s"
              % (totals.get("passed", 0), totals.get("failed", 0),
                 totals.get("error", 0), totals.get("skipped", 0),
                 exit_code, facts["date"]))
    else:
        gf = STUB % "docs/indicators/_facts.json"
    A("| Gate | Verdict | Where the evidence is |")
    A("|---|---|---|")
    A("| A Correctness | %s | source not identified yet — see §3 |" % (STUB % mod))
    A("| B Causality | %s | §5: `LEAK_RULES` %s this indicator; no mutant test recorded |"
      % ("documented leak" if rule else "no recorded exception",
         "lists" if rule else "does not list"))
    A("| C Reachability | %s | §8 |" % (STUB % harness_rel))
    A("| D Scale-free | probe tag only, see §2 | `docs/gen_indicator_dictionary.py` ×137 ratio |")
    A("| E Attribution | %s | §7 |" % (STUB % harness_rel))
    A("| F Suites | %s | §12 row above, `docs/indicators/_facts.json` |" % gf)
    A("")
    A("---")
    A("")

    # ---- 13
    A("## 13. Provenance metrics")
    A("")
    A("Counts below are produced by `docs/gen_indicator_pages.py`, which runs")
    A("`tests/test_indref_pages.py`'s own grouping function over this rendered page. They are")
    A("bookkeeping, not evidence: their job is to fail the suite the moment a later editor adds,")
    A("changes, or deletes a number here without saying where it came from.")
    A("")
    A("<!-- indref:metrics -->")
    A("")

    body = "\n".join(L) + "\n"
    counts, _ = guard._groups(guard._split(body + "\n| metric | n | @ artifact / provenance class |\n")[0])

    # The probe-derived rows (0, 2, 5, 6) are re-run LIVE on every generation --
    # `gen_indicator_dictionary` runs its probe at import.  Stamping them with
    # `facts["date"]`, which is frozen in `_facts.json`, dated a fresh
    # measurement with a stale day the moment the package moved.  Say what the
    # date actually means instead; a live date here would also break the
    # byte-stability the whole cache exists to provide.
    LIVE = ("live probe, re-run at generation time against the installed "
            "package; cache last refreshed %s" % facts["date"])
    prov = {
        "0": "@ docs/gen_indicator_dictionary.py — %s + docs/indicators/_facts.json" % LIVE,
        "2": "@ docs/gen_indicator_dictionary.py — %s — joined to "
             "../Backtesting/docs/knowledgebase/IndicatorMLRegister.md" % LIVE,
        "3": "@ %s — direct read, %s" % (mod, facts["date"]),
        "5": "@ docs/gen_indicator_dictionary.py — LEAK_RULES, %s" % LIVE,
        "6": "@ docs/gen_indicator_dictionary.py — ×137 probe ratio, %s" % LIVE,
        "7": "@ %s" % harness_rel,
        "10": "@ ../Backtesting/datastore/source/StrategyMaster.csv + one direct read of "
              "../Backtesting/backtest_results/, %s" % facts["date"],
        "12": "@ DERIVED %s from the recorded full-suite pytest run in "
              "docs/indicators/_facts.json" % facts["date"],
    }
    what = {
        "0": "header table — probe/accessor/warm-up/wiring facts",
        "2": "probed columns, ML form, warm-up, fixture range, register verdict",
        "3": "module length as read from disk",
        "5": "the leak rule this indicator does or does not carry",
        "6": "the probe's scale ratio",
        "7": "overlap ship line",
        "10": "mining-grep counts per column stem",
        "12": "gate ledger",
    }
    A("| metric | n | @ artifact / provenance class |")
    A("|---|---|---|")
    for anchor in sorted(counts):
        secn = anchor.split("#")[0].lstrip("§").split(".")[0]
        A("| %s — %s | n=%d | %s |"
          % (anchor, what.get(secn, "generated content"), counts[anchor],
             prov.get(secn, "@ DERIVED %s by docs/gen_indicator_pages.py from the page above"
                      % facts["date"])))
    A("")
    A("⚠ Parsed by `tests/test_indref_pages.py`. Every group holding a number appears above with a")
    A("matching `n=`; adding a table, adding a row, or adding a number to a paragraph without")
    A("updating the count **fails the suite**.")
    A("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------- index

def render_index(names, meta_all, recs, facts, registered, accessor, module_only,
                 measured, guard):
    L = []
    A = L.append
    A("# INDREF — per-indicator reference pages")
    A("")
    A("> **GENERATED by `docs/gen_indicator_pages.py`** (INDREF-1). Do not hand-edit a page without")
    A("> also updating its §13 metrics counts — `tests/test_indref_pages.py` fails otherwise, which")
    A("> is the point of it.")
    A("")
    A("One page per shipped indicator: what it emits, what ML form each column takes, what the gates")
    A("say, and — for the large majority — an explicit record that the gates were never run.")
    A("Template: [`_TEMPLATE.md`](_TEMPLATE.md). Worked example, hand-written and NOT regenerated:")
    A("[`tvstop.md`](tvstop.md).")
    A("")
    A("## 1. What \"shipped\" means here")
    A("")
    A("`TODO.md`'s INDREF-1 line asked for \"all 201\". That number was stale when this ran and it was")
    A("also ambiguous: this package has three indicator surfaces and they are all true at once. The")
    A("definition applied by the generator, and applied to every page below:")
    A("")
    A("> **shipped** = every name registered in `pandas_ta.Category`, **plus** every indicator")
    A("> callable on the package that `Category` does not know about, **minus** `ma`.")
    A("")
    A("`ma` is excluded because it is a moving-average *dispatcher*: it returns another indicator's")
    A("output and emits no column of its own. That is not a fresh judgement — `gen_indicator_dictionary.py`")
    A("already carries `SKIP = {\"ma\"}` and the dictionary lists `ta.ma` under *Not indicators*. The")
    A("unregistered ones get a page because a consumer can call them; their header table says in")
    A("terms that a `df.ta.strategy()` sweep skips them.")
    A("")
    A("| surface | n |")
    A("|---|---|")
    A("| registered in `Category` | %d |" % len(registered))
    A("| callable as `df.ta.<name>()` | %d |" % len(accessor))
    A("| callable on the module only | %d |" % len(module_only))
    A("| **pages in this directory** | **%d** |" % len(names))
    A("")
    unreg = sorted(n for n in names if not meta_all[n]["registered"])
    A("The %d callable-but-unregistered indicators that got a page: %s. `ma` is the one callable this"
      % (len(unreg), ", ".join("`%s`" % n for n in unreg)))
    A("definition deliberately drops.")
    A("")
    A("## 2. Measured vs stub")
    A("")
    A("A page is counted **measured** if ANY of three things is true, and the union is what the")
    A("table below counts:")
    A("")
    A("1. a dedicated overlap harness")
    A("   (`../Backtesting/scripts/analysis/measure_<name>_overlap_full.py`) exists for that")
    A("   indicator name;")
    A("2. one of the batch campaign documents in this directory's parent")
    A("   (%s) names one of the indicator's emitted column names;"
      % ", ".join("`docs/%s`" % d for d in sorted(CAMPAIGN_DOCS)))
    A("3. the page is hand-written (`tvstop.md`).")
    A("")
    A("⚠ **The caveat on (2), stated once here rather than argued on 33 pages.** The campaign docs")
    A("name comparator columns as well as ported ones, so a column-name match proves a measurement")
    A("*mentions* this indicator, not that the campaign *ported* it. Each affected page says so and")
    A("points at the document; open it to see which. An earlier version of this index applied only")
    A("test (1) and therefore reported 3 measured / 230 stub, which understated the measured set by")
    A("an order of magnitude — `sarext`, whose Gate E is recorded at ρ +0.9850 over 408,075 bars in")
    A("`docs/TalibPortsMeasured.md`, was counted a stub. Matching on the FUNCTION name instead of")
    A("column names swings it the other way, to 47, by catching every comparator mention; the")
    A("column-name test is the compromise, and it is a compromise, not a proof.")
    A("")
    A("⚠ **Five indicators (`beta`, `ht_trendline`, `hwma`, `mama`, `sarext`) raise under the")
    A("dictionary probe**, so they have no probed columns and test (2) falls back to their declared")
    A("stem. Their §2 tables are empty because the harness could not call them, NOT because they")
    A("emit nothing, and whether the same call fails for a real consumer is undetermined and")
    A("currently has no ticket.")
    A("")
    A("| | pages |")
    A("|---|---|")
    A("| measured — dedicated harness, campaign-doc match, or hand-written | %d |" % len(measured))
    A("| §6–§9 stubbed | %d |" % (len(names) - len(measured)))
    A("")
    A("That is **%.1f %%** of the pages carrying the stub token in §6–§9 — the number is derived here"
      % (100.0 * (len(names) - len(measured)) / len(names)))
    A("from the two rows above and appears in no artifact.")
    A("")
    A("Pages in the measured column: %s."
      % ", ".join("[`%s`](%s.md)" % (n, n) for n in sorted(measured)))
    A("")
    nh = len(sorted(ANALYSIS.glob("measure_*overlap*.py"))) if ANALYSIS.is_dir() else 0
    A("**Every page's Gate A, C and E rows are stubs unless that page says otherwise.**")
    A("`ls ../Backtesting/scripts/analysis/measure_*overlap*.py` returns **%d** harnesses (counted by" % nh)
    A("this generator on %s) against %d pages, and most of those harnesses are batch harnesses"
      % (facts["date"], len(names)))
    A("covering a single recent port campaign. The gates were run for recent ports, not for the")
    A("upstream body of the package, and the pages say so rather than leaving an inviting blank.")
    A("")
    A("## 3. What is machine-filled")
    A("")
    A("Machine-filled from a real run: the header table's declared rows, §2 (columns, ML form,")
    A("warm-up, probe range, register verdict), §3's module length and first-appearance date, §5's")
    A("leak flag, §10's mining greps, §12's Gate F pass count. Owed by a human and stub-tokened: §1,")
    A("§3's source identification, §4, §6, §7, §8, §9, §11 and the *effective defaults* row.")
    A("")
    A("The *effective defaults* row is stubbed on purpose. On this fork's ports every validated")
    A("parameter is declared `None` and resolved by a `_validated_int` / `_validated_float` fallback")
    A("in the function body, so `inspect.signature` reports `None` and quietly substituting the real")
    A("value into a row labelled \"declared signature\" would contradict the dictionary row cited")
    A("beside it.")
    A("")
    A("## 4. Regenerating")
    A("")
    A("```sh")
    A("python docs/gen_indicator_pages.py                 # re-emit from the fact cache (no diff)")
    A("python docs/gen_indicator_pages.py --refresh-facts # re-run pytest + rescan backtest_results/")
    A("python -m pytest tests/test_indref_pages.py -q     # the guard")
    A("```")
    A("")
    A("Slow and clock-dependent inputs live in `_facts.json`, so a plain re-run is byte-stable.")
    A("")
    A("## 5. The pages")
    A("")
    by_cat = {}
    for n in names:
        by_cat.setdefault(meta_all[n]["category"], []).append(n)
    for cat in sorted(by_cat):
        A("### 5.%d `%s` (%d)" % (1 + sorted(by_cat).index(cat), cat, len(by_cat[cat])))
        A("")
        A("| indicator | in `Category` | columns probed | §6–§9 |")
        A("|---|---|---|---|")
        for n in sorted(by_cat[cat]):
            r = recs[n]
            A("| [`%s`](%s.md) | %s | %d | %s |"
              % (n, n, "yes" if meta_all[n]["registered"] else "**no**",
                 len(r.get("cols") or []),
                 "measured" if n in measured else "stub"))
        A("")
    A("## 6. Provenance metrics")
    A("")
    A("Counts are computed by the generator with `tests/test_indref_pages.py`'s own grouping")
    A("function, over this rendered page.")
    A("")
    A("<!-- indref:metrics -->")
    A("")
    body = "\n".join(L) + "\n"
    counts, _ = guard._groups(guard._split(body + "\n| metric | n | @ x |\n")[0])
    A("| metric | n | @ artifact / provenance class |")
    A("|---|---|---|")
    for anchor in sorted(counts):
        A("| %s — generated inventory | n=%d | @ DERIVED %s by docs/gen_indicator_pages.py from "
          "the live package and docs/indicators/_facts.json |" % (anchor, counts[anchor], facts["date"]))
    A("")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------ cli

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-facts", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if any page would change")
    args = ap.parse_args()

    meta_all, registered, accessor, module_only = shipped()
    names = sorted(meta_all)
    recs = probe(names)
    modules = {n: meta_all[n]["module"] for n in names}
    stems_by_name = {n: sorted({stem(c["name"]) for c in (recs[n].get("cols") or [])}
                               or {n.upper()}) for n in names}

    facts = refresh_facts(names, modules, stems_by_name) if args.refresh_facts else load_facts()
    reg = load_register()
    guard = load_guard()

    # "Measured" is not the same as "has a per-indicator harness file". The
    # batch campaigns (TALIB-1, ALTPORT, CANDLE-1, PINEBI-1c) gated ~30
    # indicators without ever creating a `measure_<name>_overlap_full.py`;
    # counting only the filename understated the measured set by an order of
    # magnitude and branded fully-gated indicators as stubs.
    own_harness = {n for n in names
                   if (ANALYSIS / ("measure_%s_overlap_full.py" % n)).is_file()}
    by_campaign = {n for n in names
                   if CAMPAIGN_FOR(n, [c.get("name")
                                       for c in (recs[n].get("cols") or [])])}
    measured = own_harness | by_campaign | PROTECTED

    PAGES.mkdir(parents=True, exist_ok=True)
    changed = []
    for n in names:
        if n in PROTECTED:
            continue
        text = render(n, meta_all[n], recs[n], facts, reg, guard)
        p = PAGES / ("%s.md" % n)
        old = p.read_text(encoding="utf8") if p.is_file() else None
        if old != text:
            changed.append(p.name)
            if not args.check:
                p.write_text(text, encoding="utf8", newline="\n")

    idx = render_index(names, meta_all, recs, facts, registered, accessor,
                       module_only, measured, guard)
    p = PAGES / "README.md"
    if (p.read_text(encoding="utf8") if p.is_file() else None) != idx:
        changed.append(p.name)
        if not args.check:
            p.write_text(idx, encoding="utf8", newline="\n")

    print("shipped=%d (Category=%d, accessor=%d, module-only=%d, `ma` excluded)"
          % (len(names), len(registered), len(accessor), len(module_only)))
    print("pages written=%d (protected, not regenerated: %s)"
          % (len(names) - len(PROTECTED), ", ".join(sorted(PROTECTED))))
    print("measured=%d  stub=%d" % (len(measured), len(names) - len(measured)))
    print("changed=%d" % len(changed))
    if args.check and changed:
        print("WOULD CHANGE: " + ", ".join(changed[:20]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
