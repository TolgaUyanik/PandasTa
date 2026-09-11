# -*- coding: utf-8 -*-
"""TALIB-2: the ta-lib coverage CSV must stay honest and reproducible.

This guard did not exist when TALIB-2 was first marked done, while the other two
sibling scans each had one -- so nothing failed when a row asserted "no fork name
matches" about `CORREL` while `ta.correlation` sat on the surface, mapped and
uncalled, and nothing failed when 20 rows were stamped `audited=yes` on the
strength of `type(a) is not type(b)`.

The ALTREPO contract names the regeneration guard as its central clause. A green
tick against that contract without this file was a completion claim with the
clause unmet.
"""
import csv
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
GEN = os.path.join(_FORK, "docs", "gen_altrepo_talib.py")
CSV_PATH = os.path.join(os.path.dirname(_FORK), "AlternativeRepos",
                        "altrepo_talib.csv")

VERDICTS = {"have", "port", "port - alternate impl",
            "unknown - not comparable", "n/a - routed to CANDLE-2",
            "n/a - arithmetic helper, not a feature"}


def _rows():
    if not os.path.exists(CSV_PATH):
        pytest.skip(f"{CSV_PATH} absent")
    with open(CSV_PATH, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def _talib():
    try:
        import talib
        return talib
    except ImportError:
        pytest.skip("TA-Lib not installed in this environment")


def test_the_scanner_exists_even_when_the_csv_does_not():
    assert os.path.exists(GEN), GEN


def test_every_row_has_a_known_verdict():
    rows = _rows()
    assert rows, "empty CSV"
    bad = sorted({r["verdict"] for r in rows} - VERDICTS)
    assert bad == [], f"unrecognised verdicts: {bad}"


def test_it_covers_every_function_the_installed_library_exposes():
    talib = _talib()
    expected = set(talib.get_functions())
    got = {r["name"] for r in _rows()}
    assert got == expected, (
        f"only-CSV={sorted(got - expected)}, "
        f"only-library={sorted(expected - got)}"
    )


def test_have_rows_carry_a_receipt_that_opens():
    broken = []
    for row in _rows():
        if row["verdict"] != "have":
            continue
        evidence, equivalent = row["audit_evidence"], row["pandas_ta_equivalent"]
        if not evidence or ":" not in evidence:
            broken.append((row["name"], f"no receipt: {evidence!r}"))
            continue
        rel, _, lineno = evidence.rpartition(":")
        path = os.path.join(_FORK, rel)
        if not os.path.exists(path):
            broken.append((row["name"], f"missing file: {rel}"))
            continue
        lines = open(path, encoding="utf8").read().splitlines()
        index = int(lineno) - 1
        if not (0 <= index < len(lines)) or not lines[index].lstrip().startswith(
                f"def {equivalent}("):
            broken.append((row["name"], f"{rel}:{lineno} is not "
                                        f"`def {equivalent}(`"))
    assert broken == [], f"`have` rows whose receipt does not check out: {broken}"


def test_no_equivalent_names_a_fork_function_that_does_not_exist():
    """`BETA -> beta` pointed at a name the fork lacks and failed silently."""
    import inspect

    from .context import pandas_ta
    from pandas_ta.core import AnalysisIndicators as AI

    surface = {n for v in pandas_ta.Category.values() for n in v}
    surface |= {n for n, v in vars(AI).items()
                if not n.startswith("_") and inspect.isfunction(v)}
    surface |= {n for n, v in vars(pandas_ta).items()
                if not n.startswith("_") and inspect.isfunction(v)}
    phantom = sorted({r["pandas_ta_equivalent"] for r in _rows()
                      if r["pandas_ta_equivalent"]} - surface)
    assert phantom == [], f"equivalence to nonexistent fork names: {phantom}"


def test_a_mapped_name_is_never_reported_as_absent():
    """The CRITICAL: a harness limitation laundered into a measured absence.

    `CORREL` shipped as `port` with the note "no fork name matches" while
    `ta.correlation` existed and was mapped -- the probe simply could not build
    a two-series call. `port` asserts absence; it may not be reached with a
    mapped equivalent in hand.
    """
    offenders = [(r["name"], r["pandas_ta_equivalent"]) for r in _rows()
                 if r["verdict"] == "port" and r["pandas_ta_equivalent"]]
    assert offenders == [], (
        f"rows claiming absence while naming a fork equivalent: {offenders}. "
        f"An uncomparable pair is `unknown - not comparable`, never `port`."
    )


def test_the_csv_records_the_environment_its_verdicts_depend_on():
    talib = _talib()
    stamps = {r.get("probe_env", "") for r in _rows()}
    assert stamps and "" not in stamps, "no probe_env column"
    assert len(stamps) == 1, f"rows disagree about the environment: {stamps}"
    stamp = stamps.pop()
    assert f"talib {talib.__version__}" in stamp, (
        f"CSV generated under {stamp!r}, running talib {talib.__version__}"
    )


def test_regenerating_reproduces_the_committed_rows(tmp_path):
    """Verdict AND identity AND receipt -- not the verdict alone.

    Diffing only the verdict let the identity map drift silently, which is the
    entire deliverable of a coverage scan.
    """
    _talib()
    out = tmp_path / "regen.csv"
    proc = subprocess.run([sys.executable, GEN, str(out)],
                          capture_output=True, text=True, cwd=_FORK)
    assert proc.returncode == 0, proc.stderr[-2000:]
    key = lambda r: (r["verdict"], r["pandas_ta_equivalent"],
                     r["audit_evidence"], r["match"])
    with open(out, encoding="utf8") as fh:
        fresh = {r["name"]: key(r) for r in csv.DictReader(fh)}
    committed = {r["name"]: key(r) for r in _rows()}
    moved = {n: (committed[n], fresh[n]) for n in committed.keys() & fresh.keys()
             if committed[n] != fresh[n]}
    assert moved == {}, f"rows changed on re-run: {moved}"
    assert committed.keys() == fresh.keys(), "row set changed on re-run"
