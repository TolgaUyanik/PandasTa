# -*- coding: utf-8 -*-
"""ALTFIX-4: a verdict count typed in prose must match a CSV.

`IndicatorList.md`'s tables are generated and guarded. Everything else that
quotes these numbers — `TODO.md`, the run manifests, `99-summary.md` — is
hand-typed and bound to nothing, and that is exactly where the drift happened:
`Backtesting/TODO.md` published the `rsi` kept set as `7 28` under the words
"this is the list MULTIL-1 wires, and nothing else" while the CSV said `7 50`.

This does not try to know which paragraph describes which scan. It asserts the
weaker but sufficient property: **every verdict count written in prose must
equal that verdict's count in SOME committed CSV.** A stale number matches
nothing, which is precisely the failure mode.

Numbers deliberately quoting a historical value are exempt when the line says so
— the same `<!--stale-by-design-->` convention the split guard uses.
"""
import csv
import io
import os
import re
from collections import Counter

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
SIBLING = os.path.join(os.path.dirname(_FORK), "AlternativeRepos")
STALE = "<!--stale-by-design-->"

CSVS = ["altrepo_pandas_ta_classic.csv", "altrepo_tti.csv", "altrepo_talib.csv"]

# Prose shapes actually used in this repo's write-ups.
# Two shapes: the generated block's "**The gap (N):**" and hand-written
# prose's "Measured gap: **N**". Only the first was matched, so
# `IndicatorList.md` published a gap of 12 against a real 10 with a
# green suite -- in the file that IS the deliverable.
GAP_RE = re.compile(r"\*\*The gap \((\d+)\)|Measured gap: \*\*(\d+)\*\*")
VERDICT_RE = re.compile(
    r"\b(have|port - alternate impl|port)\s+\*\*(\d+)\*\*")


def _allowed():
    """Every count any committed CSV supports, by verdict."""
    allowed = {"have": set(), "port": set(), "port - alternate impl": set()}
    gaps = set()
    found = False
    for name in CSVS:
        path = os.path.join(SIBLING, name)
        if not os.path.exists(path):
            continue
        found = True
        with io.open(path, encoding="utf8") as fh:
            rows = list(csv.DictReader(fh))
        counts = Counter(r["verdict"] for r in rows)
        for verdict in allowed:
            allowed[verdict].add(counts.get(verdict, 0))
        gaps.add(counts.get("port", 0))
    return (allowed, gaps) if found else (None, None)


def _prose_files():
    out = []
    # `IndicatorList.md` is the TALIB-2/PTCLASSIC deliverable and lives in the
    # sibling directory, which is NOT a git repo -- it was outside every guard
    # precisely because it is outside the tree the tests walk.
    for path in (os.path.join(_FORK, "TODO.md"),
                 os.path.join(SIBLING, "IndicatorList.md")):
        if os.path.exists(path):
            out.append(path)
    reviews = os.path.join(_FORK, "docs", "reviews")
    for root, _dirs, files in os.walk(reviews):
        for name in files:
            if name.endswith(".md"):
                out.append(os.path.join(root, name))
    return out


def test_every_prose_gap_count_matches_a_csv():
    allowed, gaps = _allowed()
    if allowed is None:
        pytest.skip("no altrepo CSVs present")
    stray = []
    for path in _prose_files():
        text = io.open(path, encoding="utf8").read()
        for line in text.splitlines():
            if STALE in line:
                continue
            for match in GAP_RE.finditer(line):
                value = match.group(1) or match.group(2)
                if int(value) not in gaps:
                    stray.append((os.path.relpath(path, _FORK),
                                  match.group(0), sorted(gaps)))
    assert stray == [], (
        f"prose gap counts matching no CSV {{(file, text, real gaps)}}: {stray}"
    )


def test_every_prose_verdict_count_matches_a_csv():
    allowed, _ = _allowed()
    if allowed is None:
        pytest.skip("no altrepo CSVs present")
    stray = []
    for path in _prose_files():
        text = io.open(path, encoding="utf8").read()
        for line in text.splitlines():
            if STALE in line:
                continue
            for match in VERDICT_RE.finditer(line):
                verdict, n = match.group(1), int(match.group(2))
                if n not in allowed[verdict]:
                    stray.append((os.path.relpath(path, _FORK), verdict, n,
                                  sorted(allowed[verdict])))
    assert stray == [], (
        f"prose verdict counts matching no CSV "
        f"{{(file, verdict, quoted, real)}}: {stray}"
    )


def test_the_patterns_still_recognise_a_count():
    """A regex that matches nothing passes everything.

    The earlier version of this check asserted that prose counts EXIST, and
    then failed when the finished tasks were pruned and their counts moved into
    the generated blocks in `IndicatorList.md` — which is the desired end state,
    not a regression. So it now proves the PATTERNS work, against a synthetic
    sample, and that the CSVs were actually read.
    """
    sample = ("Split: have **118** · port - alternate impl **38** · "
              "**The gap (33):** `beta`")
    assert GAP_RE.search(sample), "the gap pattern no longer matches"
    verdicts = {m.group(1) for m in VERDICT_RE.finditer(sample)}
    assert verdicts == {"have", "port - alternate impl"}, (
        f"the verdict pattern now matches {verdicts}"
    )

    allowed, gaps = _allowed()
    if allowed is None:
        pytest.skip("no altrepo CSVs present")
    assert gaps and any(allowed.values()), (
        "the CSVs were read but produced no counts to compare against"
    )
    assert _prose_files(), "no prose files found to scan"
