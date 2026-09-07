# -*- coding: utf-8 -*-
"""PTCLASSIC-0: the pandas-ta-classic coverage CSV must stay honest.

The ALTREPO contract's rule is that the classifier IS the artifact: counts may
drift with the upstream repo, VERDICTS may not. These guards enforce that, plus
the two failure modes this scan actually hit while it was being written -- both
of which produced a WRONG `have`, the one direction that silently deletes a real
port:

* a cross-name alias pointing at a fork function that does not exist
  (`npabs` -> `abs`) became a `have` with a fabricated "reachable as df.ta.abs()"
  note;
* two indicators that both return their input unchanged at default parameters
  (`edecay` and `highest`, whose `length` resolves to 1) compared equal, so the
  search reported them as the same indicator.

The CSV is written OUTSIDE this repo, to `../AlternativeRepos/`, because the
audit spans three sibling repos. It is therefore not guaranteed present on a
clone; the guards skip as a group when it is absent, and
`test_the_scanner_exists_even_when_the_csv_does_not` keeps that from hiding a
deleted scanner.
"""
import csv
import io
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
GEN = os.path.join(_FORK, "docs", "gen_altrepo_pandas_ta_classic.py")
CSV_PATH = os.path.join(os.path.dirname(_FORK), "AlternativeRepos",
                        "altrepo_pandas_ta_classic.csv")
CLASSIC = os.path.join(os.path.dirname(_FORK), "AlternativeRepos",
                       "pandas-ta-classic")

VERDICTS = {
    "have", "port", "port - alternate impl", "unknown - not comparable",
    "n/a - arithmetic helper, not a feature",
}
DIVERGENCE = {"identical", "divergent", "not-compared", "not-callable",
              "degenerate", "warmup-offset", "shape", "unknown", ""}


def _rows():
    if not os.path.exists(CSV_PATH):
        pytest.skip(f"{CSV_PATH} absent (sibling repo not checked out)")
    with open(CSV_PATH, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def test_the_scanner_exists_even_when_the_csv_does_not():
    """The CSV may be absent on a clone; the generator may not.

    Without this, deleting the scanner would turn every guard below into a
    skip and the suite would stay green over nothing.
    """
    assert os.path.exists(GEN), GEN


def test_every_row_has_a_known_verdict_and_divergence():
    rows = _rows()
    assert rows, "the CSV is empty"
    bad = sorted({r["verdict"] for r in rows} - VERDICTS)
    assert bad == [], f"unrecognised verdicts: {bad}"
    bad_div = sorted({r["divergence"] for r in rows} - DIVERGENCE)
    assert bad_div == [], f"unrecognised divergence values: {bad_div}"
    blank = [r["name"] for r in rows if not r["name"] or not r["verdict"]]
    assert blank == [], blank


def test_have_rows_carry_a_receipt_that_opens():
    """`have` means "the fork already ships this". Prove it, per row.

    Not a format check: the file is opened at the cited line and the `def` must
    be there. A receipt whose shape is checked but whose content is not was
    already shipped once in this repo (PINEBI-0).
    """
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
            broken.append((row["name"], f"cited file missing: {rel}"))
            continue
        lines = io.open(path, encoding="utf8").read().splitlines()
        index = int(lineno) - 1
        if not (0 <= index < len(lines)):
            broken.append((row["name"], f"line {lineno} beyond {rel}"))
            continue
        if not lines[index].lstrip().startswith(f"def {equivalent}("):
            broken.append((row["name"],
                           f"{rel}:{lineno} is not `def {equivalent}(`, it is "
                           f"{lines[index].strip()[:50]!r}"))
    assert broken == [], f"`have` rows whose receipt does not check out: {broken}"


def test_no_have_row_rests_on_a_degenerate_match():
    """Agreement between two identity or constant functions is not evidence.

    `edecay` and `highest` both return `close` unchanged at default parameters,
    and the equivalence search called them the same indicator until the identity
    guard landed. Anything the scanner marks degenerate must NOT be a `have`.
    """
    leaked = [r["name"] for r in _rows()
              if r["verdict"] == "have" and r["divergence"] == "degenerate"]
    assert leaked == [], (
        f"these `have` verdicts rest on a degenerate match: {leaked}"
    )


def test_every_alias_target_exists_on_the_fork():
    """An alias is a claim of equivalence; an unresolvable one became a `have`.

    Read out of the CSV rather than the scanner's table, so a row whose
    `pandas_ta_equivalent` names something the fork lacks fails here even if the
    scanner's own ALIAS dict is clean.
    """
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
    assert phantom == [], (
        f"the CSV claims equivalence to fork names that do not exist: "
        f"{phantom}"
    )


def test_absence_was_searched_for_not_assumed():
    """`port` asserts the fork does NOT have it. That claim was searched.

    Four cross-name equivalents were found by search after three were found by
    eye — `medprice`/`typprice`/`avgprice`/`md` map to `hl2`/`hlc3`/`ohlc4`/`mad`
    — so a `port` list built from names alone is known to be wrong. This pins
    that those four are not back in the gap.
    """
    verdict_of = {r["name"]: r["verdict"] for r in _rows()}
    for classic_name, fork_name in (("medprice", "hl2"), ("typprice", "hlc3"),
                                    ("avgprice", "ohlc4"), ("md", "mad")):
        if classic_name not in verdict_of:
            continue
        assert verdict_of[classic_name] == "have", (
            f"{classic_name} is classified {verdict_of[classic_name]!r}; the "
            f"fork ships it as {fork_name} and the search proved it"
        )


@pytest.mark.skipif(not os.path.isdir(CLASSIC),
                    reason="pandas-ta-classic sibling repo not checked out")
def test_regenerating_reproduces_the_committed_verdicts(tmp_path):
    """Counts may drift with upstream; verdicts may not."""
    out = tmp_path / "regen.csv"
    proc = subprocess.run([sys.executable, GEN, str(out)],
                          capture_output=True, text=True, cwd=_FORK)
    assert proc.returncode == 0, proc.stderr[-2000:]

    with open(out, encoding="utf8") as fh:
        fresh = {r["name"]: r["verdict"] for r in csv.DictReader(fh)}
    committed = {r["name"]: r["verdict"] for r in _rows()}

    moved = {n: (committed[n], fresh[n])
             for n in committed.keys() & fresh.keys()
             if committed[n] != fresh[n]}
    assert moved == {}, f"verdicts changed on re-run: {moved}"
    assert committed.keys() == fresh.keys(), (
        f"row set changed: only-committed="
        f"{sorted(committed.keys() - fresh.keys())}, only-fresh="
        f"{sorted(fresh.keys() - committed.keys())}"
    )


def test_the_csv_records_the_environment_its_verdicts_depend_on():
    """A verdict is conditional on the probe environment. Say which one.

    Installing TA-Lib moved `dm` from `port - alternate impl` to `have`: both
    packages defer to TA-Lib when it is importable, so their outputs converge.
    Nothing in the artifact said the answer depended on that. A reader who
    regenerates on a box without TA-Lib gets a different CSV and no way to tell
    whether the fork changed or their environment did.

    So the stamp must be present, consistent across rows, and must match the
    interpreter running this test -- a mismatch is a loud failure instead of a
    silent reclassification.
    """
    rows = _rows()
    stamps = {r.get("probe_env", "") for r in rows}
    assert stamps and "" not in stamps, (
        "the CSV has no `probe_env` column; its verdicts are environment-"
        "dependent and must say which environment produced them"
    )
    assert len(stamps) == 1, f"rows disagree about the probe environment: {stamps}"

    try:
        import talib
        current = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        current = "talib ABSENT"

    stamp = stamps.pop()
    assert current in stamp, (
        f"the committed CSV was generated under {stamp!r} but this environment "
        f"is {current!r}. Regenerate it here, or run where it was made -- the "
        f"verdicts are not portable across that difference."
    )
