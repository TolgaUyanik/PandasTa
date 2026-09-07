# -*- coding: utf-8 -*-
"""PTCLASSIC-1: the divergence classification must stay honest and reproducible.

PTCLASSIC-0 found 53 same-name-different-behaviour pairs. This artifact says WHY
each differs, and the value of it is entirely in the `maths` bucket being small
and real -- that bucket is the one that costs a human a two-body read.

The classifier was wrong twice while being written, in the same direction both
times: it over-filled `maths`.

* First version, no `warmup` or `seeding` class: **33 of 53** in `maths`, most
  of them showing Pearson r = 1.0000. That is a reader sent to compare two
  identical formulas.
* Adding `warmup` alone caught 2, because recursive indicators seeded
  differently CONVERGE without ever becoming bit-equal, which a strict
  equality test cannot see. `seeding` catches those: 19 of them.

So the guard that matters is not "is the vocabulary valid" but "are the cheap
explanations actually tested before the expensive one is claimed".
"""
import csv
import io
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
GEN = os.path.join(_FORK, "docs", "gen_altrepo_ptclassic_divergence.py")
SIBLING = os.path.join(os.path.dirname(_FORK), "AlternativeRepos")
CSV_PATH = os.path.join(SIBLING, "altrepo_ptclassic_divergence.csv")
SOURCE_CSV = os.path.join(SIBLING, "altrepo_pandas_ta_classic.csv")
CLASSIC = os.path.join(SIBLING, "pandas-ta-classic")

CLASSES = {"default-only", "shape", "warmup", "seeding", "scaling", "offset",
           "maths", "unresolved", "warmup-offset"}
# Classes that explain a divergence CHEAPLY. If one of these applies, claiming
# `maths` instead wastes a body-read.
CHEAP = {"default-only", "shape", "warmup", "seeding", "scaling", "offset"}


def _rows():
    if not os.path.exists(CSV_PATH):
        pytest.skip(f"{CSV_PATH} absent (sibling repo not checked out)")
    with open(CSV_PATH, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def test_the_generator_exists_even_when_the_csv_does_not():
    assert os.path.exists(GEN), GEN


def test_every_class_is_from_the_vocabulary_and_carries_a_detail():
    rows = _rows()
    assert rows, "the CSV is empty"
    bad = sorted({r["divergence_class"] for r in rows} - CLASSES)
    assert bad == [], f"unrecognised divergence classes: {bad}"
    silent = [r["name"] for r in rows if not r["detail"].strip()]
    assert silent == [], f"rows with a class but no stated reason: {silent}"


def test_it_explains_exactly_the_rows_ptclassic_0_flagged():
    """No row invented, none quietly dropped."""
    if not os.path.exists(SOURCE_CSV):
        pytest.skip("PTCLASSIC-0 CSV absent")
    with open(SOURCE_CSV, encoding="utf8") as fh:
        expected = {r["name"] for r in csv.DictReader(fh)
                    if r["verdict"] == "port - alternate impl"}
    got = {r["name"] for r in _rows()}
    assert got == expected, (
        f"only-here={sorted(got - expected)}, "
        f"only-in-PTCLASSIC-0={sorted(expected - got)}"
    )


def test_the_expensive_bucket_did_not_swallow_the_cheap_explanations():
    """`maths` must stay a minority, and the cheap classes must be populated.

    This is the regression that actually happened: with `warmup` and `seeding`
    missing, `maths` held 33 of 53 and every one of them was a lie of omission.
    Pinning the exact split would break on any upstream change, so this pins the
    SHAPE of the answer -- the cheap classifiers must be doing work.
    """
    rows = _rows()
    counts = {}
    for row in rows:
        counts[row["divergence_class"]] = counts.get(
            row["divergence_class"], 0) + 1

    maths = counts.get("maths", 0)
    assert maths < len(rows) / 2, (
        f"`maths` holds {maths} of {len(rows)} rows. That is what the CSV "
        f"looked like before `warmup` and `seeding` existed; a cheap "
        f"explanation is probably missing again. Split: {counts}"
    )
    cheap_used = sorted(k for k in counts if k in CHEAP)
    assert len(cheap_used) >= 3, (
        f"only {cheap_used} of the cheap classes fired; the classifier is "
        f"likely short-circuiting to `maths`. Split: {counts}"
    )


def test_seeding_rows_really_do_converge():
    """`seeding` is a strong claim: same recurrence, different start.

    Re-measured by `docs/verify_ptclassic_seeding.py`, in a SUBPROCESS.

    ⚠ It cannot run in-process. `pandas_ta_classic` registers the DataFrame
    accessor under the same name as this fork (`register_dataframe_accessor
    ("ta")`), so importing it REPLACES `df.ta` for every DataFrame built
    afterwards. An earlier version of this test imported it here and took the
    suite from green to 109 failures -- every one an `AttributeError` on an
    accessor that exists. See `test_importing_classic_in_process_is_forbidden`.
    """
    if not os.path.isdir(CLASSIC):
        pytest.skip("pandas-ta-classic sibling repo not checked out")
    script = os.path.join(_FORK, "docs", "verify_ptclassic_seeding.py")
    assert os.path.exists(script), script

    proc = subprocess.run([sys.executable, script], capture_output=True,
                          text=True, cwd=_FORK)
    tail = proc.stdout.strip().splitlines()
    assert tail, f"verifier produced no output; stderr={proc.stderr[-800:]}"
    summary = json.loads(tail[-1])
    if "skipped" in summary:
        pytest.skip(summary["skipped"])
    assert proc.returncode == 0, (
        f"`seeding` rows that do not converge: {summary.get('failures')}; "
        f"unverifiable: {summary.get('unverifiable')}; "
        f"checked {summary.get('checked')} of {summary.get('total')}"
    )


def test_importing_classic_in_process_is_forbidden():
    """No test module may import `pandas_ta_classic` at module or test scope.

    This is the hazard that actually bit, so it is a guard rather than a note:
    both packages claim the `df.ta` accessor, last import wins, and the loser's
    entire accessor surface disappears from every DataFrame created after it.
    The scanners and the verifier are all subprocess-invoked for this reason.
    """
    # AST, not grep: the first version matched the phrase inside its OWN
    # docstring and failed itself. A prose mention of the hazard is not the
    # hazard; only a real import statement is.
    import ast

    offenders = []
    for name in sorted(os.listdir(_HERE)):
        if not name.startswith("test_") or not name.endswith(".py"):
            continue
        path = os.path.join(_HERE, name)
        try:
            tree = ast.parse(io.open(path, encoding="utf8").read())
        except SyntaxError:                                 # pragma: no cover
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name.split(".")[0] == "pandas_ta_classic"
                       for a in node.names):
                    offenders.append(f"{name}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] == "pandas_ta_classic":
                    offenders.append(f"{name}:{node.lineno}")

    assert offenders == [], (
        f"these test modules import pandas_ta_classic in-process: {offenders}. "
        f"It hijacks the `df.ta` accessor for the rest of the session. Shell "
        f"out to docs/verify_ptclassic_seeding.py instead."
    )


@pytest.mark.skipif(not os.path.isdir(CLASSIC),
                    reason="pandas-ta-classic sibling repo not checked out")
def test_regenerating_reproduces_the_committed_classes(tmp_path):
    out = tmp_path / "regen.csv"
    proc = subprocess.run([sys.executable, GEN, str(out)],
                          capture_output=True, text=True, cwd=_FORK)
    assert proc.returncode == 0, proc.stderr[-2000:]
    with open(out, encoding="utf8") as fh:
        fresh = {r["name"]: r["divergence_class"] for r in csv.DictReader(fh)}
    committed = {r["name"]: r["divergence_class"] for r in _rows()}
    moved = {n: (committed[n], fresh[n])
             for n in committed.keys() & fresh.keys()
             if committed[n] != fresh[n]}
    assert moved == {}, f"divergence classes changed on re-run: {moved}"
    assert committed.keys() == fresh.keys(), "row set changed on re-run"
