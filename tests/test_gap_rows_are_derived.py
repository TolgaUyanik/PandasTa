# -*- coding: utf-8 -*-
"""ALTFIX-2: a `port` verdict must be DERIVED, not trusted.

Nine indicators have been published as absent while the fork ships them, across
three review rounds and three CSVs. Every existing gap guard is an allowlist of
names a reviewer already caught — `test_absence_was_searched_for_not_assumed`
pins four, `test_no_gap_row_names_something_the_fork_actually_ships` pins
fourteen — so none of them could ever catch occurrence ten. They pin history.

This one re-runs the resolver. For every `port` row in every CSV it sweeps the
whole fork surface, under every declared kwargs variant and both windows, and
fails if ANYTHING reproduces the alt-repo output. That is the same computation
the scanner performs, run independently against the committed answer.

⚠ Subprocess, always. `pandas_ta_classic` registers the `df.ta` accessor under
the fork's own name; one in-process import took the suite from green to 109
failures.
"""
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
SIBLING = os.path.join(os.path.dirname(_FORK), "AlternativeRepos")
VERIFIER = os.path.join(_FORK, "docs", "verify_gap_rows.py")

CASES = [
    ("pandas-ta-classic", "altrepo_pandas_ta_classic.csv"),
    ("tti", "altrepo_tti.csv"),
    ("ta-lib", "altrepo_talib.csv"),
]


def _run(scan):
    if not os.path.exists(VERIFIER):
        pytest.fail(f"{VERIFIER} is missing; the gap rows are unverified")
    proc = subprocess.run([sys.executable, VERIFIER, scan],
                          capture_output=True, text=True, cwd=_FORK)
    lines = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")]
    if not lines:
        pytest.skip(f"verifier produced no result for {scan}: "
                    f"{proc.stdout[-300:]} {proc.stderr[-300:]}")
    return json.loads(lines[-1])


@pytest.mark.parametrize("scan,csv_name", CASES)
def test_no_gap_row_is_reproducible_by_the_fork(scan, csv_name):
    """The claim a `port` row makes, re-derived.

    Not "is this name in a list I wrote after being told" — actually run the
    sweep and see whether any fork function reproduces the output.
    """
    if not os.path.exists(os.path.join(SIBLING, csv_name)):
        pytest.skip(f"{csv_name} absent")
    result = _run(scan)
    if "skipped" in result:
        pytest.skip(result["skipped"])
    reproducible = result.get("reproducible", {})
    assert reproducible == {}, (
        f"{scan}: these rows are published as ABSENT but the fork reproduces "
        f"them: {reproducible}. That is occurrence #10 of this defect."
    )


@pytest.mark.parametrize("scan,csv_name", CASES)
def test_the_verifier_actually_examined_the_gap(scan, csv_name):
    """A verifier that checks nothing passes everything.

    If the sweep silently examined zero rows — a bad path, an import failure
    swallowed — the test above would be green over nothing.
    """
    if not os.path.exists(os.path.join(SIBLING, csv_name)):
        pytest.skip(f"{csv_name} absent")
    result = _run(scan)
    if "skipped" in result:
        pytest.skip(result["skipped"])
    # A GENUINELY EMPTY gap is now possible: TALIB-1 ported all ten ta-lib
    # `port` rows on 2026-09-08 and the scan reports 0. That is the task
    # succeeding, not the verifier failing -- but the two look identical from
    # `gap_rows == 0` alone, which is exactly what this test exists to tell
    # apart. The discriminator is the POSITIVE CONTROL: the verifier re-derives
    # a sample of `have` rows and must re-find them. If it still detects those,
    # it is reading the CSV and the gap really is empty; if it detects nothing,
    # the zero is a broken sweep.
    if result.get("gap_rows", 0) == 0:
        probed = result.get("have_probed", 0)
        detected = result.get("detected_have", 0)
        assert probed > 0 and detected >= probed - 2, (
            f"{scan}: gap_rows == 0 AND the positive control found only "
            f"{detected} of {probed} known `have` rows -- that is a verifier "
            f"reading nothing, not an empty gap."
        )
        return

    assert result.get("gap_rows", 0) > 0, (
        f"{scan}: the CSV reports no `port` rows at all — either the gap is "
        f"genuinely empty (say so explicitly) or the verifier is not reading it"
    )
    assert result.get("checked", 0) == result["gap_rows"], (
        f"{scan}: only {result.get('checked')} of {result['gap_rows']} gap rows "
        f"could be re-driven: {result.get('undrivable')}. A row the verifier "
        f"cannot drive is a row nothing is guarding."
    )


@pytest.mark.parametrize("scan,csv_name", CASES)
def test_the_detector_can_actually_detect(scan, csv_name):
    """POSITIVE CONTROL. A detector that has never fired is not a detector.

    The tti arm reported a clean gap for a full round while being structurally
    incapable of finding anything: it rounded the tti side to 4dp, left the fork
    cache at full precision, and compared at rtol=1e-9. Fed the rows tti's own
    CSV publishes as `have` — `TypicalPrice` vs `hlc3`, literally the same
    number — it re-detected 0 of 13.

    So `reproducible == {}` is only meaningful alongside proof that the same
    comparison finds the matches that ARE there.
    """
    if not os.path.exists(os.path.join(SIBLING, csv_name)):
        pytest.skip(f"{csv_name} absent")
    result = _run(scan)
    if "skipped" in result:
        pytest.skip(result["skipped"])
    probed = result.get("have_probed", 0)
    detected = result.get("detected_have", 0)
    assert probed > 0, f"{scan}: no `have` rows were probed as a control"
    # Raised from probed//2 once the shared surface cache landed: the control
    # went 10/7/9 -> 12/12, 10/12, 12/12. A half-threshold accepted a detector
    # that was blind to the whole `identical-when-pinned` class.
    assert detected >= max(1, probed - 2), (
        f"{scan}: the detector re-found only {detected} of {probed} known "
        f"`have` rows. It cannot be trusted to report an empty gap."
    )
