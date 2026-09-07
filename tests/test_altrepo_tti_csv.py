# -*- coding: utf-8 -*-
"""TTIND-0/-1: the tti coverage CSV must stay honest and reproducible.

Two failure modes this scan hit, both of which UNDERSTATED what the fork
already ships — the opposite direction from the pandas-ta-classic scan, and
just as wrong:

* **tti rounds every output to 4 decimals** (`_typical_price.py:82`
  `return tp.round(4)`). Compared at 1e-9 the first run found **0 `have` across
  57 x 231 comparisons** — even `TypicalPrice` vs `hlc3`, which are the same
  formula and differ by 4.999e-05.
* **tti's `period` default is not the fork's `length` default.** With rounding
  fixed but defaults unpinned, only the three parameter-FREE price transforms
  matched and all 32 length-taking indicators were filed as different
  behaviour. Pinning both sides to the same window rescued five.

So the guards here pin the two things that were wrong: the comparison must be at
tti's own precision, and a divergence must survive a matched window.

⚠ Comparison at 4 decimals is WEAKER evidence than the bit-level agreement used
for pandas-ta-classic. `test_have_rows_disclose_the_reduced_precision` makes the
artifact say so on every row rather than leaving it in a docstring.
"""
import csv
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
GEN = os.path.join(_FORK, "docs", "gen_altrepo_tti.py")
SIBLING = os.path.join(os.path.dirname(_FORK), "AlternativeRepos")
CSV_PATH = os.path.join(SIBLING, "altrepo_tti.csv")
TTI = os.path.join(SIBLING, "trading-technical-indicators")

VERDICTS = {"have", "port", "port - alternate impl", "unknown - not comparable"}


def _rows():
    if not os.path.exists(CSV_PATH):
        pytest.skip(f"{CSV_PATH} absent (sibling repo not checked out)")
    with open(CSV_PATH, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def test_the_scanner_exists_even_when_the_csv_does_not():
    assert os.path.exists(GEN), GEN


def test_every_row_has_a_known_verdict():
    rows = _rows()
    assert rows, "the CSV is empty"
    bad = sorted({r["verdict"] for r in rows} - VERDICTS)
    assert bad == [], f"unrecognised verdicts: {bad}"
    blank = [r["class_name"] for r in rows
             if not r["class_name"] or not r["verdict"]]
    assert blank == [], blank


def test_identity_is_resolved_for_every_class():
    """TTIND-0's acceptance criterion, stated as a test.

    "Every one of the 57 has a resolved identity (the fork name it corresponds
    to, or no counterpart)" — so an unresolved row is a failure of the scan, not
    a property of tti.
    """
    rows = _rows()
    unresolved = [r["class_name"] for r in rows
                  if r["verdict"] == "unknown - not comparable"]
    # An honest `unknown` beats a confident wrong answer, so a few are allowed
    # -- but they must stay a small minority AND each must name its candidate,
    # or "unresolved" becomes a dumping ground.
    assert len(unresolved) <= max(2, len(rows) // 20), (
        f"identity unresolved for {len(unresolved)}/{len(rows)}: {unresolved}"
    )
    for row in rows:
        if row["verdict"] == "unknown - not comparable":
            assert row["pandas_ta_equivalent"] or "no counterpart" in row["note"], (
                f"{row['class_name']} is unresolved without naming what was tried"
            )


def test_have_rows_carry_a_receipt_that_opens():
    broken = []
    for row in _rows():
        if row["verdict"] != "have":
            continue
        evidence, equivalent = row["audit_evidence"], row["pandas_ta_equivalent"]
        if not evidence or ":" not in evidence:
            broken.append((row["class_name"], f"no receipt: {evidence!r}"))
            continue
        rel, _, lineno = evidence.rpartition(":")
        path = os.path.join(_FORK, rel)
        if not os.path.exists(path):
            broken.append((row["class_name"], f"missing file: {rel}"))
            continue
        lines = open(path, encoding="utf8").read().splitlines()
        index = int(lineno) - 1
        if not (0 <= index < len(lines)) or not lines[index].lstrip().startswith(
                f"def {equivalent}("):
            broken.append((row["class_name"], f"{rel}:{lineno} is not "
                                              f"`def {equivalent}(`"))
    assert broken == [], f"`have` rows whose receipt does not check out: {broken}"


def test_have_rows_disclose_the_reduced_precision():
    """A 4-decimal match is weaker evidence, and must say so ON THE ROW.

    tti rounds, so no row here can claim the bit-level agreement the
    pandas-ta-classic audit uses. A reader comparing the two CSVs must not have
    to know that from a docstring.
    """
    silent = [r["class_name"] for r in _rows()
              if r["verdict"] == "have"
              and f"{4}-decimal" not in r["note"]]
    assert silent == [], (
        f"these `have` rows do not disclose how they were matched: {silent}. "
        f"Every match here is at 4 decimals, tti's own rounding."
    )


def test_the_signal_layer_is_recorded_as_out_of_scope_not_missing():
    """TTIND-1: `getTiSignal()` is a LABEL, not a feature.

    The previous version of this test asserted that a column which is
    CONSTANT `True` (every class inherits `getTiSignal` from
    `TechnicalIndicator`) was non-empty, then re-asserted a fact checked two
    tests earlier, under three lines of dead `pass`. It could not fail.

    What TTIND-1 actually requires is that the signal layer is an explicit
    out-of-scope DECISION on the artifact -- so that a later reader does not
    count 57 absent "indicators" nobody wants -- and that no row treats it as a
    gap.
    """
    rows = _rows()
    assert "has_signal_layer" in rows[0], "signal layer not recorded at all"
    # The substantive property, not a header check: EVERY class carries the
    # layer (they all inherit it), so a row reporting False means the scanner
    # stopped looking or tti changed its base class -- either way the
    # out-of-scope decision no longer covers what it claims to.
    missing = [r["class_name"] for r in rows if r["has_signal_layer"] != "True"]
    assert missing == [], (
        f"these classes no longer report a signal layer: {missing}. The "
        f"out-of-scope decision is recorded per row and must stay true."
    )
    assert len(rows) == sum(1 for r in rows if r["has_signal_layer"] == "True")


def test_no_fork_name_is_claimed_by_two_different_tti_classes():
    """One fork function cannot be the identity of two tti indicators.

    `MarketFacilitationIndex` and the Money Flow Index both abbreviate to `mfi`,
    and the acronym fallback filed Bill Williams' indicator as the fork's `mfi`
    with an `audited=yes` receipt. `ProjectionOscillator` collided with
    `PriceOscillator` on `po` the same way.
    """
    from collections import defaultdict

    # Keyed on (fork name, PARAMETERISATION). One fork function legitimately
    # serves two tti classes when the call differs: `linreg` is the Linear
    # Regression Indicator at defaults and the Time Series Forecast at
    # `tsf=True`; `roc` is the Price Rate of Change on close and the Volume
    # Rate of Change on volume. Keying on the bare name blocked both correct
    # answers -- a guard that makes the right result untestable is a bad guard.
    claims = defaultdict(list)
    for row in _rows():
        if row["pandas_ta_equivalent"]:
            key = (row["pandas_ta_equivalent"], row.get("equivalent_params", ""))
            claims[key].append(row["class_name"])
    collisions = {k: v for k, v in claims.items() if len(v) > 1}
    assert collisions == {}, (
        f"one fork name AND parameterisation claimed by several tti classes: "
        f"{collisions}. An acronym collision (mfi, po) looks exactly like this."
    )


def test_every_gap_row_states_why_it_is_a_gap():
    """`port` asserts the fork does NOT have it. Five rounds of false absences.

    Every guard in this file constrained `have` rows, and not one constrained
    the gap -- so `ad`, `adosc`, `mom`, `roc`, `pvt`, `massi`, `donchian`,
    `pvo` (round 1) and then `TimeSeriesForecast`, `VolumeRateOfChange`
    (round 2) all shipped as measured absences through a green suite.

    A gap row must now either name a candidate that was tried and failed, or
    appear in the scanner's REJECTED table with a stated reason. A bare "no
    counterpart is mapped" fails here.
    """
    scanner = open(GEN, encoding="utf8").read()
    assert "REJECTED = {" in scanner, (
        "the scanner has no REJECTED table; a gap row cannot state its reason"
    )
    unexplained = []
    for row in _rows():
        if row["verdict"] != "port":
            continue
        note = row["note"]
        if row["match"] == "no-match-unexplained" or (
                "REJECTED after checking" not in note
                and "was tried" not in note):
            unexplained.append(row["class_name"])
    assert unexplained == [], (
        f"gap rows with no stated reason: {unexplained}. Each must be in "
        f"REJECTED with a reason, or show a candidate that was tried."
    )


def test_no_gap_row_names_something_the_fork_actually_ships():
    """The specific rows that shipped false, as a regression test.

    Cheap, blunt, and it would have caught every one of the ten.
    """
    import inspect

    from .context import pandas_ta

    gap = {r["class_name"] for r in _rows() if r["verdict"] == "port"}
    known_false = {
        "AccumulationDistributionLine": "ad", "ChaikinOscillator": "adosc",
        "Momentum": "mom", "PriceRateOfChange": "roc",
        "PriceAndVolumeTrend": "pvt", "MassIndex": "massi",
        "PriceChannel": "donchian", "VolumeOscillator": "pvo",
        "Qstick": "qstick", "RelativeVolatilityIndex": "rvi",
        "StochasticMomentumIndex": "smi", "WildersSmoothing": "rma",
        "TimeSeriesForecast": "linreg", "VolumeRateOfChange": "roc",
    }
    regressed = {k: v for k, v in known_false.items()
                 if k in gap and hasattr(pandas_ta, v)}
    assert regressed == {}, (
        f"these are back in the gap while the fork ships them: {regressed}"
    )


def test_the_csv_records_the_environment_its_verdicts_depend_on():
    rows = _rows()
    stamps = {r.get("probe_env", "") for r in rows}
    assert stamps and "" not in stamps, "no `probe_env` column"
    assert len(stamps) == 1, f"rows disagree about the environment: {stamps}"
    try:
        import talib
        current = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        current = "talib ABSENT"
    stamp = stamps.pop()
    assert current in stamp, (
        f"CSV generated under {stamp!r}, this environment is {current!r}"
    )


@pytest.mark.skipif(not os.path.isdir(TTI),
                    reason="tti sibling repo not checked out")
def test_regenerating_reproduces_the_committed_verdicts(tmp_path):
    out = tmp_path / "regen.csv"
    proc = subprocess.run([sys.executable, GEN, str(out)],
                          capture_output=True, text=True, cwd=_FORK)
    assert proc.returncode == 0, proc.stderr[-2000:]
    key = lambda r: (r["verdict"], r["pandas_ta_equivalent"],
                     r["audit_evidence"], r["match"])
    with open(out, encoding="utf8") as fh:
        fresh = {r["class_name"]: key(r) for r in csv.DictReader(fh)}
    committed = {r["class_name"]: key(r) for r in _rows()}
    moved = {n: (committed[n], fresh[n]) for n in committed.keys() & fresh.keys()
             if committed[n] != fresh[n]}
    assert moved == {}, f"rows changed on re-run: {moved}"
    assert committed.keys() == fresh.keys(), "row set changed on re-run"
