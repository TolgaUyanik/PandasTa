# -*- coding: utf-8 -*-
"""The shipped examples, pinned. Offline, no network, no sibling repo.

WHAT THIS MODULE PINS, in order of how much it would hurt to lose
------------------------------------------------------------------
1. **Zero swallowed exceptions.** The example's spec table is derived from a real one in which
   **16 argument lists did not match the function signature**. Every one raised on every call and
   was swallowed by a bare `except: continue`, so those 16 indicators had never emitted a column
   and no output ever said so. `test_no_spec_fails` is the assertion that construct could not
   make, and `test_all_sixteen_repaired_specs_are_present` stops the table quietly shrinking back
   to the subset that happened to work.

2. **The look-ahead registry is exactly right.** `KNOWN_LOOKAHEAD` names the columns whose value
   at bar T legitimately depends on bars after T. `test_no_unknown_lookahead` fails the moment
   any OTHER column starts reading the future, and `test_dpo_default_still_reads_the_future`
   fails if a listed entry stops leaking - so the list cannot rot in either direction.
   Every one of the six entries is guarded, not a subset - two by a single-cut probe and four
   by the `bos` sweep, because the two leaks have different shapes. An unprobed entry would
   linger as a false warning to readers with nothing to retire it. This matters because the same
   list was described as "complete" at two entries until `ssf` turned out to be a third, and that
   one was a bug rather than a design choice.

3. **`bos`'s look-ahead is BOUNDED, and the bound is what is pinned.** It detects swings with
   `rolling(swing_length, center=True)`, so a pivot is confirmed up to `(swing_length - 1) // 2`
   bars after it forms and is written back to the pivot bar. That is the analytic bound from the
   window geometry, not an observation. What the sweep below MEASURES is at or under it and not
   always at it: 20 cuts (`range(200, 460, 13)`) on a 500-bar synthetic frame give 2 bars at
   `swing_length=5`, **2 at 7**, 4 at 9. A sweep only sees the pivots it happens to straddle, so
   asserting equality with the bound would pin a sampling accident.

4. **No strategy content.** `docs/SHOWCASE_SCOPE.md` records the owner's decision to DROP the
   scoring layer rather than synthesise neutral constants. `test_examples_contain_no_strategy_content`
   is what makes that decision enforceable instead of merely written down.

5. **Offline, and no import from the private sibling repo.** The example must run in a clone that
   has neither network nor `../Backtesting`.

6. **No ticker or universe from the private repo appears in either example.** The scope
   document forbids it in prose; `test_no_private_universe_leaks_into_the_examples`
   forbids it in a way that fails.

7. **Coverage is computed, never retyped.** `test_coverage_is_computed_from_the_live_package`
   pins that the number comes from `ta.Category`, so it cannot go stale silently.

WHY THE NOTEBOOK IS NOT EXECUTED HERE
--------------------------------------
`examples/speedy_analysis.ipynb` is the narrative tour and is deliberately NOT run by this suite
(owner decision, 2026-09-12): executing it would add `nbclient` as a test dependency and several
minutes of runtime. It is prose with committed outputs. `examples/market_dashboard.py` is the
tested artifact, and the two are kept honest by carrying the same measurements.
"""
import hashlib
import importlib.util
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pandas_ta as ta

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SCRIPT = _EXAMPLES / "market_dashboard.py"

# NOT `pytest.importorskip`, and NOT a `sys.path` mutation.
#
# `importorskip` is for optional third-party packages. Used on a first-party file it
# turns a syntax error, a rename, or a deleted `examples/` into 33 silent SKIPS - and
# SHOWCASE-5's gate is `pytest -q` at 0 failed, which 33 skips satisfy perfectly. That is
# a gate with a hole shaped exactly like the failure it exists to catch.
#
# Loading by path also avoids putting `examples/` on `sys.path` for the whole session,
# where any future `examples/<stdlib name>.py` would shadow it for every other module.
assert SCRIPT.exists(), f"{SCRIPT} is missing - the example is a shipped artifact"
_spec = importlib.util.spec_from_file_location("market_dashboard", SCRIPT)
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)
NOTEBOOK = _EXAMPLES / "speedy_analysis.ipynb"
SCOPE_DOC = Path(__file__).resolve().parents[1] / "docs" / "SHOWCASE_SCOPE.md"

# The sixteen whose argument lists were wrong in the source table. Named individually so a
# regression names the indicator rather than a count.
REPAIRED_SPECS = (
    "aberration", "eom", "hilo", "kc", "long_run", "pdist", "pgo", "pvol",
    "pvr", "rvgi", "short_run", "smi", "squeeze", "thermo", "trend_return", "ttm_trend",
)


@pytest.fixture(scope="module")
def frame():
    """Synthetic, deterministic, offline. Never `load()` - that may reach the network."""
    return md.synthetic_ohlcv(n=420, seed=11)


@pytest.fixture(scope="module")
def built(frame):
    return md.build(frame)


@pytest.fixture(scope="module")
def scaled_panel(frame):
    """Computed ONCE. `check_scale_free` runs the whole spec table twice per call, so three
    tests each calling it was three quarters of this module's runtime."""
    return md.check_scale_free(frame, lambda f: md.run_specs(f)[0])


# ----------------------------------------------------------------------------------
# SHOWCASE-1 / -2  --  the sweep runs, and nothing is swallowed
# ----------------------------------------------------------------------------------
def test_no_spec_fails(built):
    """The assertion a bare `except: continue` is structurally unable to make."""
    failures = built["failures"]
    assert failures == [], (
        "the example's own sweep reported failures:\n  "
        + "\n  ".join(f"{n}: {why}" for n, why in failures))


def test_all_sixteen_repaired_specs_are_present():
    """13 of these were in the notebook; three take a DERIVED series and were absent.

    `long_run(fast, slow)`, `short_run(fast, slow)` and `trend_return(close, trend)` cannot be
    expressed in a table keyed on frame-column names, which is precisely why the original table
    called them wrongly. They live in DERIVED_SPECS.
    """
    named = {n for n, _, _ in md.SPECS} | set(md.DERIVED_SPECS)
    missing = [s for s in REPAIRED_SPECS if s not in named]
    assert not missing, f"repaired specs dropped from the example: {missing}"


def test_the_three_derived_input_specs_actually_produce_columns(frame):
    """Presence in a dict is not evidence they run."""
    for name in ("long_run", "short_run", "trend_return"):
        result = md.DERIVED_SPECS[name](frame)
        assert result is not None, f"{name} returned None"
        n_cols = 1 if isinstance(result, pd.Series) else result.shape[1]
        assert n_cols >= 1


def test_run_specs_reports_a_failure_rather_than_hiding_it(frame):
    """A blind test: if the reporting path is broken, every other test here is worthless."""
    bogus = [("definitely_not_an_indicator", ["close"], {}),
             ("rsi", ["nonexistent_column"], {}),
             # THE ORIGINAL DEFECT, reinstated on purpose: aberration(high, low, close) called
             # with close alone. This is the `except Exception` branch - the one that actually
             # hid the sixteen. The two cheap branches above never touch it.
             ("aberration", ["close"], {})]
    panel, failures = md.run_specs(frame, specs=bogus, derived={})
    assert len(failures) == 3, f"expected all three bogus specs reported, got {failures}"
    by_name = dict(failures)
    assert "TypeError" in by_name["aberration"], (
        f"the raising branch was not reported as an exception: {by_name['aberration']!r}")
    assert panel.empty or panel.shape[1] == 0

    # the fork runner has its own loop and its own chance to swallow
    _, fork_failures = md.run_fork_specs(frame, specs={
        "explodes": lambda d: (_ for _ in ()).throw(ValueError("boom"))})
    assert len(fork_failures) == 1 and "ValueError" in fork_failures[0][1]


def test_no_bare_except_in_the_example():
    """The construct that hid the 16 for the life of the source file."""
    src = SCRIPT.read_text(encoding="utf8")
    code = [ln for ln in src.split("\n") if re.match(r"\s*except\s*:", ln)]
    assert not code, f"bare `except:` found: {code}"


def test_exit_status_reflects_failure(frame, monkeypatch, capsys):
    """`report` must return non-zero when anything failed, or CI cannot see a break."""
    good = md.build(frame)
    assert md.report(frame, "test", good) == 0

    broken = dict(good, failures=[("fake", "ValueError: injected")])
    assert md.report(frame, "test", broken) == 1
    capsys.readouterr()


# ----------------------------------------------------------------------------------
# SHOWCASE-3  --  it exercises THIS fork, and the count is asserted not printed
# ----------------------------------------------------------------------------------
def test_coverage_is_computed_from_the_live_package():
    cov = md.coverage()
    registered = set()
    for group in ta.Category.values():
        registered.update(group)
    assert cov["registered"] == len(registered), (
        "coverage() disagrees with ta.Category - the count is being derived from something else")
    independent = len(md.exercised_names() & registered)
    assert cov["exercised"] == independent, (
        f"coverage() reports {cov['exercised']}; recomputing it here gives {independent}")


# Callable on the module but deliberately absent from `Category`, each for a stated reason.
# Verified against the live package 2026-09-12. `macd` IS registered - do not add it here.
UNREGISTERED_BY_DESIGN = {
    "drawdown": "module-level utility, not swept",
    "hwma": "module-level; hwc is the registered channel form",
    "ht_trendline": "TALIB-1: a price LEVEL. Ships as a percent distance; the level is raw=True "
                    "and registered nowhere, so a sweep cannot emit an unusable column.",
    "mama": "TALIB-1: MAMA/FAMA are price levels, same treatment as ht_trendline",
    "sarext": "TALIB-1: a price level, same treatment",
}


def test_the_example_calls_no_name_that_is_not_registered():
    """A typo in a spec table is otherwise invisible: getattr fails and the row is skipped.

    The allowlist is not a convenience - each entry is a DESIGN decision about what a
    `df.ta.strategy()` sweep may emit. Anything else appearing here is a mistake.
    """
    cov = md.coverage()
    unexpected = set(cov["called_but_unregistered"]) - set(UNREGISTERED_BY_DESIGN)
    assert not unexpected, (
        "the example calls names absent from Category with no recorded reason: "
        f"{sorted(unexpected)}")


def test_the_unregistered_allowlist_has_not_gone_stale():
    """If one of these gets registered, the allowlist entry must go, not linger."""
    registered = set()
    for group in ta.Category.values():
        registered.update(group)
    now_registered = sorted(set(UNREGISTERED_BY_DESIGN) & registered)
    assert not now_registered, (
        f"{now_registered} are now in Category; remove them from UNREGISTERED_BY_DESIGN")


def test_the_example_exercises_a_majority_of_registered_indicators():
    """A floor, not a target. Stated as a fraction of what is registered."""
    cov = md.coverage()
    assert cov["fraction"] > 0.78, (
        f"coverage fell to {cov['fraction']:.0%} ({cov['exercised']}/{cov['registered']})")


def test_fork_only_indicators_are_exercised():
    """Guards against the example silently reverting to an upstream-only demo."""
    for name in ("pzo", "vzo", "frama", "stc_tv", "vstop", "imi", "sarext", "mama",
                 "bos", "choch", "fvg", "ob", "ichimoku_ml", "wilder_rma"):
        assert name in md.FORK_SPECS or name in {n for n, _, _ in md.SPECS}, \
            f"{name} is no longer exercised by the example"


def test_the_whole_hilbert_family_is_exercised():
    """Seven read-outs of ONE state machine with two warm-ups (12 and 37 bars)."""
    for name in ("ht", "ht_dcperiod", "ht_dcphase", "ht_phasor",
                 "ht_sine", "ht_trendline", "ht_trendmode", "mama"):
        assert name in md.FORK_SPECS, f"{name} missing from the fork demo"


def test_consolidated_sources_matches_what_the_function_actually_calls(frame, monkeypatch):
    """`exercised_names()` folds these into the coverage count, so a retyped list goes stale."""
    called = set()
    for name in md.CONSOLIDATED_SOURCES:
        real = getattr(ta, name)

        def spy(*a, _n=name, _f=real, **k):
            called.add(_n)
            return _f(*a, **k)

        monkeypatch.setattr(ta, name, spy)
    md.consolidate_multi_output(frame)
    assert called == set(md.CONSOLIDATED_SOURCES), (
        f"declared {sorted(md.CONSOLIDATED_SOURCES)} but called {sorted(called)}")


def test_all_five_ml_companion_columns_are_reachable(built):
    """MLCOL-1 shipped five. If a parent stops emitting one, this says which."""
    columns = set(built["panel"].columns) | set(built["fork"].columns)
    missing = [c for c in md.ML_COMPANION_COLUMNS if c not in columns]
    assert not missing, f"ML companion columns absent from the example output: {missing}"


def test_hw_mid_companion_stays_deliberately_absent(built):
    """Its companion reads rho +0.9257 / +0.9213 against the two edges that ARE kept.

    Three columns for one signal is what the non-redundancy rule forbids. A future contributor
    "completing the set" is exactly what this stops.
    """
    columns = set(built["panel"].columns) | set(built["fork"].columns)
    assert "HW-MID_DIST_PCT" not in columns
    assert "HW-UPPER_DIST_PCT" in columns and "HW-LOWER_DIST_PCT" in columns


def test_indicators_out_of_category_are_not_called():
    """`beta` needs a benchmark; `up_and_down_volume` and `volume_delta` need a finer frame.

    All three are out of Category ON PURPOSE so a sweep cannot call them with inputs it cannot
    supply. An example that calls them anyway teaches the wrong lesson.
    """
    called = md.exercised_names()
    for name in ("beta", "up_and_down_volume", "volume_delta"):
        assert name not in called, f"{name} is deliberately out of Category; do not demo it"


def test_gate_e_reverts_are_not_resurrected():
    """Seven Pine built-ins were built, MEASURED, and deleted for restating a shipped column.

    `REVERTED_ON_GATE_E` in `docs/gen_pine_builtin_coverage.py` exists so their CSV rows cannot
    flip back to `port` and invite a re-port. Same guard, applied to the examples: demoing one
    is the first step to shipping it again.
    """
    called = md.exercised_names()
    for name in ("kcw", "rwi", "rms", "demarker", "ift", "relative_volume", "williams_fractal"):
        assert name not in called, (
            f"{name} was measured and reverted on Gate E; the example must not resurrect it")


# ----------------------------------------------------------------------------------
# The feature contract the example claims to check
# ----------------------------------------------------------------------------------
def test_no_unknown_lookahead(frame):
    """Anything not on the registry that reads the future is a finding, not a nuance."""
    report = md.check_causality(frame, {
        "ssf": lambda d: ta.ssf(d[md.C], length=10),
        "rsi": lambda d: ta.rsi(d[md.C], length=14),
        "frama": lambda d: ta.frama(d[md.H], d[md.L], d[md.C]),
        "ichimoku_ml": lambda d: ta.ichimoku_ml(d[md.H], d[md.L], d[md.C]),
        "choch": lambda d: ta.choch(d[md.H], d[md.L], d[md.C]),
        "halftrend": lambda d: ta.halftrend(d[md.H], d[md.L], d[md.C]),
        "dpo_safe": lambda d: ta.dpo(d[md.C], centered=False),
    })
    unknown = report[report["verdict"] == "UNKNOWN LEAK"]
    assert unknown.empty, (
        "columns read the future and are NOT in KNOWN_LOOKAHEAD:\n"
        + unknown.to_string(index=False))


# Which test guards which registry entry against going stale. Split because the two leaks have
# different SHAPES: `ICS_26` and `DPO_20` shift unconditionally, so one perturbation cut sees
# them. `bos` writes a pivot back only when a cut happens to straddle one, so a single cut
# frequently shows zero drift on a perfectly leaky implementation - it needs the sweep in
# `test_bos_lookahead_is_within_half_the_swing_window`, which asserts a NON-ZERO measured reach.
# Discovered by this test failing on the module fixture while `bos` was demonstrably leaking.
SINGLE_CUT_GUARDED = {("ichimoku", "ICS_26"), ("dpo(centered=True)", "DPO_20")}
SWEEP_GUARDED = {("bos", "BOS_BULL"), ("bos", "BOS_BEAR"),
                 ("bos", "HIGHER_HIGH"), ("bos", "LOWER_LOW")}


def test_every_known_lookahead_entry_still_leaks(frame):
    """The other direction. A registry excusing a column that no longer leaks is a lie.

    Keyed on (probe label, column) on purpose: `ta.dpo(close)` and `ta.dpo(close,
    centered=False)` BOTH emit `DPO_20`, so a column-only key would hand the safe variant the
    unsafe one's excuse.
    """
    report = md.check_causality(frame, {
        "ichimoku": lambda d: ta.ichimoku(d[md.H], d[md.L], d[md.C])[0],
        "dpo(centered=True)": lambda d: ta.dpo(d[md.C]),
    })
    leaking = {(r["probe"], r["column"]) for _, r in report.iterrows()
               if r["max prefix drift"] > 0}
    stale = SINGLE_CUT_GUARDED - leaking
    assert not stale, (
        f"excused as known look-ahead but no longer leaking: {sorted(stale)}. Remove them from "
        "KNOWN_LOOKAHEAD and delete the warnings that cite them.")

    # And nothing is guarded by neither test.
    covered = SINGLE_CUT_GUARDED | SWEEP_GUARDED
    assert set(md.KNOWN_LOOKAHEAD) == covered, (
        f"registry entries with no still-leaks guard: {sorted(set(md.KNOWN_LOOKAHEAD) - covered)}")


def test_a_raising_probe_is_reported_not_swallowed(frame):
    """Three independent reviewers found this by inspection. Pinned so there is no fourth.

    The error row once landed under a key called `causal` while every reader looked at
    `verdict`, so a probe that blew up became a NaN: not clean, not known, not an unknown leak,
    invisible to the printed summary, to the exit status, and to the test above. A bare
    `except: continue` rebuilt out of a typo, inside the function whose whole job is finding
    what other code hides.
    """
    def boom(_):
        raise RuntimeError("probe blew up")
    report = md.check_causality(frame, {"exploding": boom,
                                        "rsi": lambda d: ta.rsi(d[md.C], 14)})
    assert "causal" not in report.columns, "the phantom `causal` column is back"
    assert report["verdict"].notna().all(), "a probe row carries no verdict"
    errored = report[report["verdict"].str.startswith("ERROR")]
    assert len(errored) == 1, f"expected the raising probe reported once, got {len(errored)}"
    assert "RuntimeError" in errored.iloc[0]["verdict"]


def test_ssf_is_causal(frame):
    """It was not, until 2026-09-11. Perturbing bars >= 300 of 400 moved bar 0 by 31.4."""
    report = md.check_causality(frame, {"ssf": lambda d: ta.ssf(d[md.C], length=10)})
    assert (report["max prefix drift"] == 0.0).all(), report.to_string(index=False)


def test_dpo_default_still_reads_the_future(frame):
    """A guard on the WARNING, not on the behaviour.

    If upstream ever flips the default, this test fails and the documentation that tells users to
    pass `centered=False` must be removed. Until then the trap is real and stays stated.
    """
    report = md.check_causality(frame, {"dpo": lambda d: ta.dpo(d[md.C])})
    assert (report["max prefix drift"] > 0).any(), \
        "dpo no longer leaks by default - remove the warnings in the examples and CLAUDE.md"


@pytest.mark.parametrize("swing_length,bound,measured", [(5, 2, 2), (7, 3, 2), (9, 4, 4)])
def test_bos_lookahead_is_within_half_the_swing_window(swing_length, bound, measured):
    """Two assertions: never past the analytic bound, and never zero.

    `(swing_length - 1) // 2` is geometry - how far a centered window reaches. The sweep
    measures 2 / 2 / 4 for swing_length 5 / 7 / 9; at 7 it lands UNDER the bound because these
    cuts never straddle a pivot at maximum reach. Asserting equality with the BOUND would pin
    that accident; asserting only `<=` would let a bos that stopped leaking entirely pass green.
    So both are asserted, against different numbers.
    """
    d = md.synthetic_ohlcv(n=500, seed=3)
    worst = 0
    for cut in range(200, 460, 13):
        b = d.copy()
        for col in (md.O, md.H, md.L, md.C):
            b.iloc[cut:, b.columns.get_loc(col)] *= 1.4
        a_out = ta.bos(d[md.H], d[md.L], d[md.C], swing_length=swing_length)
        b_out = ta.bos(b[md.H], b[md.L], b[md.C], swing_length=swing_length)
        for col in a_out.columns:
            x = np.asarray(a_out[col], float)[:cut]
            y = np.asarray(b_out[col], float)[:cut]
            m = np.isfinite(x) & np.isfinite(y)
            moved = np.where(np.abs(x[m] - y[m]) > 0)[0]
            if len(moved):
                worst = max(worst, cut - int(moved.min()))
    assert worst <= bound, (
        f"bos(swing_length={swing_length}) reached {worst} bars back, past the "
        f"(swing_length-1)//2 = {bound} bound a centered window allows")
    assert worst == measured, (
        f"bos(swing_length={swing_length}) measures {worst} bars on this fixed sweep, not the "
        f"recorded {measured}; the behaviour changed - re-measure and update the docstring")


def test_scale_free_check_separates_a_ratio_from_a_level(scaled_panel):
    """The check is only worth running if it can tell the two apart."""
    report = scaled_panel
    verdict = report.set_index("column")["scale_free"].to_dict()
    assert verdict.get("NATR_14") is True, "NATR is a normalised ratio and must be scale-free"
    assert verdict.get("SMA_20") is False, "SMA_20 is a price level and must NOT be scale-free"


def test_log_return_is_scale_free_but_not_bit_identical(scaled_panel):
    """Why the check reports two verdicts instead of one.

    log(k*a) - log(k*b) differs from log(a) - log(b) in the final float bit. Reporting that as a
    scale-freedom failure would be wrong, and a single-verdict test would do exactly that.
    """
    row = scaled_panel[scaled_panel["column"] == "LOGRET_1"]
    assert not row.empty, "LOGRET_1 is no longer produced; the example lost log_return"
    assert bool(row["scale_free"].iloc[0]) is True
    assert bool(row["bit_identical"].iloc[0]) is False
    assert 0 < float(row["max drift"].iloc[0]) < 1e-12


def test_every_fork_column_probed_for_scale_is_scale_free(frame):
    """The fork's own additions are held to the contract they exist to enforce."""
    report = md.check_scale_free(frame, lambda f: md.run_fork_specs(f, specs={
        "frama": lambda d: ta.frama(d[md.H], d[md.L], d[md.C]),
        "ht": lambda d: ta.ht(d[md.C]),
        "pzo": lambda d: ta.pzo(d[md.C]),
        "vzo": lambda d: ta.vzo(d[md.C], d[md.V]),
        "imi": lambda d: ta.imi(d[md.O], d[md.C]),
        "ichimoku_ml": lambda d: ta.ichimoku_ml(d[md.H], d[md.L], d[md.C]),
        "vstop": lambda d: ta.vstop(d[md.H], d[md.L], d[md.C]),
    })[0])
    failed = report[~report["scale_free"]]
    assert failed.empty, f"fork columns that are not scale-free:\n{failed.to_string(index=False)}"


def test_redundancy_check_finds_the_known_duplicate_pairs(built):
    """If it cannot find RSI vs CMO, it is not measuring anything."""
    pairs = md.check_redundancy(built["panel"])
    assert (pairs >= 0.99).sum() > 0
    top = {frozenset(k) for k in pairs.head(40).index}
    assert frozenset({"RSI_14", "CMO_14"}) in top or (pairs >= 0.999).sum() > 5


# ----------------------------------------------------------------------------------
# SHOWCASE-0 / -4  --  what must NOT be in a public example
# ----------------------------------------------------------------------------------
# SHA-256 prefixes of a sample of the private repo's symbol universes - NOT the symbols.
#
# This file is public. An earlier revision listed the symbols in plaintext, which made the
# leak guard into the leak - the same mistake the scope document briefly made by restating
# the very threshold values it was refusing to publish. Hashing keeps the detection and
# drops the disclosure: the test can still say "a private symbol appears in this example"
# without anyone who reads it learning which symbols those are.
#
# To regenerate after the universes change, run in the PRIVATE repo only:
#     sha256(ticker.encode()).hexdigest()[:16]
_PRIVATE_SYMBOL_DIGESTS = frozenset({
    "05009facdd1ccaa2",
    "1788359deadb2996",
    "290fdb8022dce65d",
    "2fb2c5ef80398bb5",
    "371edc95d4767822",
    "375d61ff5ab1776b",
    "37e1b09973312a10",
    "45decb5256c4cef4",
    "7a8ac9fc81a4d215",
    "7cc9acdb4f7ca705",
    "80b24a79ab942a61",
    "859b43086c77b8bc",
    "ad295520b0156727",
    "b2bfed5d132b8406",
    "b6a15c323f7abdce",
    "d070a3297ed2e322",
    "d1130354863d128f",
    "d7a80affe1063fd4",
    "db9888aa5b68579f",
    "e7d6c25f6a1475eb",
})


def test_no_private_universe_leaks_into_the_examples():
    """The identifier guard below sees NAMES. This one sees VALUES.

    Pasting a private symbol list into an example verbatim would pass every other test here,
    because the constants would be values and not the banned identifier names. One of those
    lists is materially more sensitive than the others; which one is recorded in the private
    repo, not in this file.
    """
    for path in (SCRIPT, NOTEBOOK):
        assert path.exists(), f"{path.name} is missing; the leak guard cannot run"
        text = path.read_text(encoding="utf8")
        found = {hashlib.sha256(t.encode()).hexdigest()[:16]
                 for t in re.findall(r"\b[A-Z0-9]{3,6}\.IS\b", text)}
        leaked = found & _PRIVATE_SYMBOL_DIGESTS
        assert not leaked, (
            f"{path.name} carries {len(leaked)} symbol(s) from a private universe "
            f"(digests {sorted(leaked)}); resolve them in the private repo, not here.")
        assert not re.search(r"\b[A-Z0-9]{3,6}\.IS\b", text), (
            f"{path.name} contains a `.IS` ticker at all; the examples use neutral US symbols")


def test_examples_contain_no_strategy_content():
    """Enforces `docs/SHOWCASE_SCOPE.md` blocks 8-11: the scoring layer was DROPPED.

    A written decision that nothing checks is a decision that erodes.
    """
    banned = ("SIGNAL_THRESHOLDS", "INDICATOR_WEIGHTS", "composite_score", "BIST_SECTORS",
              "GLOBAL_MARKETS", "US_SECTOR_ETFS", "get_all_market_tickers",
              "get_bist_sector_for_stock", "MarketSignalCalculator",
              # A live signal-timing convention is a decision rule too. This one was not in
              # the source file - it was written by hand INTO the public examples, which is
              # why an inventory of the source could never have caught it.
              "iloc[-3]", "the consumer")
    for path in (SCRIPT, NOTEBOOK):
        assert path.exists(), f"{path.name} is missing; the scope guard cannot run"
        text = path.read_text(encoding="utf8")
        hits = [b for b in banned if b in text]
        assert not hits, f"{path.name} carries strategy content: {hits}"


def test_examples_do_not_import_the_private_sibling_repo():
    """A public clone has no `../Backtesting`, and must not need one."""
    for path in (SCRIPT, NOTEBOOK):
        assert path.exists(), f"{path.name} is missing; the import guard cannot run"
        text = path.read_text(encoding="utf8")
        for pattern in (r"import\s+config", r"deploy[/\\]app", r"backtesting_engine"):
            assert not re.search(pattern, text), f"{path.name} references {pattern}"


def test_yfinance_is_not_a_hard_import():
    """The fork's consumer installs it; a reader of the example may not have it.

    Both examples, not just the script - the scope document makes this a rule for the plural.
    """
    src = SCRIPT.read_text(encoding="utf8")
    for line in src.split("\n"):
        if re.match(r"(import|from)\s+yfinance", line):
            pytest.fail(f"module-level yfinance import in {SCRIPT.name}: {line!r}")
    assert "import yfinance as yf" in src, "the optional loader disappeared entirely"

    import json
    nb = json.loads(NOTEBOOK.read_text(encoding="utf8"))
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        for line in "".join(cell["source"]).split("\n"):
            if re.match(r"(import|from)\s+yfinance", line):
                pytest.fail(f"module-level yfinance import in notebook cell {i}: {line!r}")


def test_offline_path_needs_no_network(monkeypatch):
    """Belt and braces: poison the loader, then prove `--offline` never calls it."""
    def explode(*a, **k):
        raise AssertionError("network was touched on the offline path")
    monkeypatch.setattr(md, "load_yahoo", explode)
    frame, source = md.load(offline=True)
    assert len(frame) > 250
    assert "synthetic" in source


def test_load_falls_back_and_says_so(monkeypatch):
    """A silent fallback would let a reader believe synthetic output is real market data."""
    monkeypatch.setattr(md, "load_yahoo",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no network")))
    frame, source = md.load(offline=False)
    assert len(frame) > 250
    assert "synthetic" in source and "no network" in source


def test_the_scope_document_exists_and_records_a_decision():
    """SHOWCASE-0's deliverable. Without it, the IP call lives only in a chat log."""
    assert SCOPE_DOC.exists(), "docs/SHOWCASE_SCOPE.md is missing"
    text = SCOPE_DOC.read_text(encoding="utf8")
    for token in ("publish", "synthesise", "drop", "Sign-off"):
        assert token in text, f"scope doc lacks a `{token}` section"


def test_main_runs_offline_end_to_end(capsys):
    """The whole pipeline, as a user would invoke it."""
    status = md.main(["--offline"])
    out = capsys.readouterr().out
    assert status == 0, "the example exited non-zero on a clean offline run"
    assert "FAILURES        : 0" in out
    assert "UNKNOWN LEAKS   : 0" in out


def test_out_path_is_an_argument(tmp_path, capsys):
    """The source wrote CSVs into a hard-coded sibling directory. This one does not."""
    target = tmp_path / "panel.csv"
    assert md.main(["--offline", "--out", str(target)]) == 0
    capsys.readouterr()
    assert target.exists()
    written = pd.read_csv(target, index_col=0)
    assert written.shape[0] > 200 and written.shape[1] > 200
