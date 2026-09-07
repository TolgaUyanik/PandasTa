# -*- coding: utf-8 -*-
"""`IndicatorList.md`'s verdict tables must equal their CSVs.

The ta-lib section published `port - alternate impl` 42 / `have` 19 /
`unknown` 1 while its own CSV held 31 / 29 / 2 — stale by a full review round,
in the document that IS the TALIB-2 deliverable. The pandas-ta-classic section
had drifted the same way twice before that.

Every count in that file is now inside a generated `<!--BEGIN:tag-->` block, and
this fails if a block disagrees with the CSV it summarises or if someone
re-types a count outside one. The precedent is `test_readme_counts.py`, which
pins the README to the live package for exactly this reason.
"""
import csv
import os
import re
from collections import Counter

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
SIBLING = os.path.join(os.path.dirname(_FORK), "AlternativeRepos")
DOC = os.path.join(SIBLING, "IndicatorList.md")
GEN = os.path.join(_FORK, "docs", "gen_indicator_list_tables.py")

SECTIONS = [("ptclassic", "altrepo_pandas_ta_classic.csv", "name"),
            ("tti", "altrepo_tti.csv", "class_name"),
            ("talib", "altrepo_talib.csv", "name")]


def _doc():
    if not os.path.exists(DOC):
        pytest.skip("IndicatorList.md absent (sibling repo not checked out)")
    return open(DOC, encoding="utf8").read()


def _rows(name):
    path = os.path.join(SIBLING, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def test_the_table_generator_exists():
    assert os.path.exists(GEN), GEN


@pytest.mark.parametrize("tag,csv_name,key", SECTIONS)
def test_each_published_block_matches_its_csv(tag, csv_name, key):
    rows = _rows(csv_name)
    if rows is None:
        pytest.skip(f"{csv_name} absent")
    doc = _doc()
    match = re.search(re.escape(f"<!--BEGIN:{tag}-->") + r"(.*?)"
                      + re.escape(f"<!--END:{tag}-->"), doc, re.S)
    assert match, f"no generated block for {tag}; a hand-typed table has returned"
    block = match.group(1)

    counts = Counter(r["verdict"] for r in rows)
    for verdict, n in counts.items():
        cell = re.search(rf"\| `{re.escape(verdict)}` \| \*\*(\d+)\*\*", block)
        assert cell, f"{tag}: `{verdict}` missing from the published table"
        assert int(cell.group(1)) == n, (
            f"{tag}: table says {verdict}={cell.group(1)}, CSV says {n}"
        )

    gap = sorted(r[key] for r in rows if r["verdict"] == "port")
    stated = re.search(r"\*\*The gap \((\d+)\):\*\*", block)
    assert stated and int(stated.group(1)) == len(gap), (
        f"{tag}: gap count {stated.group(1) if stated else None} vs {len(gap)}"
    )
    listed = set(re.findall(r"`([A-Za-z_0-9]+)`",
                            block[block.index("**The gap"):]))
    assert set(gap) <= listed, (
        f"{tag}: gap names in the CSV but not published: {sorted(set(gap) - listed)}"
    )


def test_no_verdict_count_is_typed_outside_a_generated_block():
    """A count outside the markers is a count nothing checks."""
    doc = _doc()
    stripped = re.sub(r"<!--BEGIN:\w+-->.*?<!--END:\w+-->", "", doc, flags=re.S)
    strays = re.findall(r"\| `(have|port|port - alternate impl)` \| \*\*\d+\*\*",
                        stripped)
    assert strays == [], (
        f"hand-typed verdict counts outside the generated blocks: {strays}"
    )
