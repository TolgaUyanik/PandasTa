# -*- coding: utf-8 -*-
"""Rewrite every verdict table and gap list in `IndicatorList.md` from its CSV.

The tables were hand-maintained and went stale within one review round: the
ta-lib section published `port - alternate impl` 42 / `have` 19 / `unknown` 1
while its own CSV held 31 / 29 / 2, and that document IS the TALIB-2
deliverable. The pandas-ta-classic section had already drifted twice the same
way.

So no verdict count in that file is typed any more. Each section carries a
generated block between HTML markers, and
`tests/test_indicator_list_tables.py` fails if the committed block disagrees
with the CSV.

Usage:  python docs/gen_indicator_list_tables.py
"""
import csv
import io
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
DOC = os.path.join(SIBLING, "IndicatorList.md")

SECTIONS = [
    ("ptclassic", "altrepo_pandas_ta_classic.csv", "name",
     "## pandas-ta-classic"),
    ("tti", "altrepo_tti.csv", "class_name",
     "## trading-technical-indicators (tti)"),
    ("talib", "altrepo_talib.csv", "name", "## ta-lib-python"),
]

MEANING = {
    "have": "the fork already ships it, proven by matching output",
    "port - alternate impl": "same indicator, **different behaviour**",
    "port": "genuinely absent — **this is the gap**",
    "n/a - arithmetic helper, not a feature": "scalar/vector maths, not features",
    "n/a - routed to CANDLE-2": "TA-Lib's `CDL*` set; `cdl_pattern` wraps it",
    "unknown - not comparable": "the probe could not decide; NOT an absence",
}


def _rows(name):
    path = os.path.join(SIBLING, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def block_for(rows, key):
    counts = Counter(r["verdict"] for r in rows)
    gap = sorted(r[key] for r in rows if r["verdict"] == "port")
    lines = [f"| verdict | n | meaning |", "|---|---|---|"]
    for verdict, n in counts.most_common():
        lines.append(f"| `{verdict}` | **{n}** | {MEANING.get(verdict, '')} |")
    lines.append("")
    lines.append(f"**The gap ({len(gap)}):** " +
                 ("`" + "` `".join(gap) + "`" if gap else "_none_"))
    lines.append("")
    lines.append(f"_{len(rows)} rows total. Generated from the CSV by "
                 f"`docs/gen_indicator_list_tables.py`; "
                 f"`tests/test_indicator_list_tables.py` fails if this block "
                 f"disagrees with it._")
    return "\n".join(lines)


def main():
    doc = io.open(DOC, encoding="utf8").read()
    for tag, csv_name, key, heading in SECTIONS:
        rows = _rows(csv_name)
        if rows is None:
            print(f"  {tag}: CSV absent, skipped")
            continue
        begin, end = f"<!--BEGIN:{tag}-->", f"<!--END:{tag}-->"
        block = f"{begin}\n{block_for(rows, key)}\n{end}"
        if begin in doc:
            doc = re.sub(re.escape(begin) + r".*?" + re.escape(end), block,
                         doc, 1, re.S)
        else:
            assert heading in doc, f"heading not found: {heading}"
            insert = doc.index(heading) + len(heading)
            doc = doc[:insert] + "\n\n" + block + doc[insert:]
        print(f"  {tag}: {len(rows)} rows")
    io.open(DOC, "w", encoding="utf8", newline="\n").write(doc)
    print(f"wrote {DOC}")


if __name__ == "__main__":
    main()
