# -*- coding: utf-8 -*-
"""MINOR (round 9): the README's indicator inventory is checked, not typed.

The headline said 199 registered "(201 counting `drawdown` and `vp`)", the
per-category headers summed to 200 because `performance (4)` counted
`drawdown`, and the paragraph below them listed `drawdown` as being OUTSIDE
`Category`. Three numbers in one section, one of them contradicting itself
twelve lines later.

Correcting the numbers fixes today's instance and nothing else -- the section is
hand-maintained, so it drifts again on the next indicator added. These guards
compare it to the live package: every category header's count and its name list,
the headline, and the set of indicators that sit outside `Category`. Adding an
indicator without updating the README is now a test failure, which is the only
mechanism that has held in this repo.

Definitions, stated once so the three counts stop being confused:

* `Category` -- what `df.ta.strategy()` and the category runs sweep. The headline.
* `df.ta.<name>()` -- the accessor surface. `Category` plus anything given a
  method but never registered.
* `ta.<name>()` -- module-level. Adds indicators with neither.
"""
import inspect
import io
import os
import re

import pytest

from .context import pandas_ta
from pandas_ta.core import AnalysisIndicators

_HERE = os.path.dirname(os.path.abspath(__file__))
README = os.path.join(os.path.dirname(_HERE), "README.md")

# Accessor methods that are not indicators. Named explicitly because the
# alternative -- subtracting `Category` -- would define the difference away and
# make the "callable but unregistered" count unfalsifiable.
NOT_INDICATORS = {
    "above", "above_value", "below", "below_value", "cross", "cross_value",
    "constants", "indicators", "strategy", "ticker",
}

# A bare `## ` header ends the section; `**name (n)** — `a` `b`` are its rows.
CATEGORY_ROW = re.compile(
    r"^\*\*([a-z_]+) \((\d+)\)\*\* [-—] (.+?)(?=\n\n|\n\*\*|\n##)",
    re.M | re.S)


def _readme():
    assert os.path.exists(README), README
    return io.open(README, encoding="utf8").read()


def _category_rows():
    rows = CATEGORY_ROW.findall(_readme())
    assert rows, "no `**category (n)** — ...` rows found; the format changed"
    return {name: (int(n), set(re.findall(r"`([a-z0-9_]+)`", body)))
            for name, n, body in rows}


def _accessor_indicators():
    return {n for n, v in vars(AnalysisIndicators).items()
            if not n.startswith("_") and inspect.isfunction(v)} - NOT_INDICATORS


def test_every_category_is_listed_with_the_right_count():
    """Each `**name (n)**` header must match `Category` -- both n and the names.

    `performance (4)` passed review for weeks because nobody added four names
    and counted them. The count and the list are asserted separately: a header
    saying 3 above a list of four names is the drift that actually happens.
    """
    listed = _category_rows()
    actual = {k: set(v) for k, v in pandas_ta.Category.items()}

    assert set(listed) == set(actual), (
        f"README categories vs Category: only-README="
        f"{sorted(set(listed) - set(actual))}, "
        f"only-package={sorted(set(actual) - set(listed))}"
    )

    wrong_count, wrong_names = {}, {}
    for name, (claimed, names) in listed.items():
        if claimed != len(actual[name]):
            wrong_count[name] = (claimed, len(actual[name]))
        if claimed != len(names):
            wrong_names[name] = (claimed, len(names), "header vs its own list")
        extra, missing = names - actual[name], actual[name] - names
        if extra or missing:
            wrong_names[name] = {"listed_not_registered": sorted(extra),
                                 "registered_not_listed": sorted(missing)}

    assert wrong_count == {}, (
        f"category headers disagree with `Category` {{cat: (readme, actual)}}: "
        f"{wrong_count}"
    )
    assert wrong_names == {}, f"category name lists are wrong: {wrong_names}"


def test_the_headline_states_the_category_count():
    """The bold headline must be the `Category` total, and nothing else."""
    text = _readme()
    match = re.search(r"\*\*(\d+) indicators\*\* registered in `Category`", text)
    assert match, "the README headline no longer states a `Category` count"
    assert int(match.group(1)) == sum(len(v) for v in pandas_ta.Category.values())


def test_the_accessor_count_is_right_where_the_readme_states_it():
    """The second count -- callable on `df.ta` -- must also be measured.

    Stated as "**201** are callable as `df.ta.<name>()`". If someone adds an
    accessor without registering it (which is how `hwma` and `vp` got here),
    this moves and the README must move with it.
    """
    match = re.search(r"\*\*(\d+)\*\* are callable\s+as `df\.ta\.<name>\(\)`",
                      _readme())
    assert match, "the README no longer states the df.ta accessor count"
    assert int(match.group(1)) == len(_accessor_indicators())


def test_the_outside_category_paragraph_names_exactly_the_right_indicators():
    """The set that `df.ta.strategy()` silently skips must be complete.

    This is the one that bites a user: an indicator present, documented and
    callable, that a strategy run never computes. Under-listing it is worse
    than a wrong count -- `drawdown` was simultaneously counted INSIDE
    `performance` and listed here, so both readings had support.
    """
    registered = {n for names in pandas_ta.Category.values() for n in names}
    accessor_only = _accessor_indicators() - registered
    # Module-level indicators with neither a Category entry nor an accessor.
    # `ma` and `drawdown` are the two; everything else at module level is a
    # utility, a primitive, or a performance metric with its own paragraph.
    module_only = {n for n in ("ma", "drawdown")
                   if callable(getattr(pandas_ta, n, None))}
    expected = accessor_only | module_only

    text = _readme()
    para = re.search(
        r"Present but outside `Category`, so skipped by `df\.ta\.strategy\(\)`:(.+?)\n\n",
        text, re.S)
    assert para, "the outside-`Category` paragraph is gone"
    named = set(re.findall(r"`([a-z0-9_]+)`", para.group(1)))

    missing = sorted(expected - named)
    assert missing == [], (
        f"callable but unregistered, and not named in the README: {missing}. "
        f"A user running df.ta.strategy() never computes these."
    )
    # And nothing may be named there that IS registered -- the `drawdown`
    # contradiction in reverse.
    contradictory = sorted(named & registered)
    assert contradictory == [], (
        f"named as outside `Category` while registered in it: {contradictory}"
    )


@pytest.mark.parametrize("name", ["hwma", "vp"])
def test_the_unregistered_accessors_really_are_callable(name):
    """The paragraph claims they work; prove it rather than asserting prose."""
    assert callable(getattr(AnalysisIndicators, name, None))
    assert name not in {n for names in pandas_ta.Category.values() for n in names}
