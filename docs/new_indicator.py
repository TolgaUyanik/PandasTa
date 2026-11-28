# -*- coding: utf-8 -*-
"""Scaffold a new indicator: the five wiring touch points, nothing else (#331 GEN-1).

    python docs/new_indicator.py <category> <name>

Run from the repo root. `<category>` is a key of `pandas_ta.Category` (read from the package,
not retyped here); `<name>` is a new lower-case identifier.

MANIFEST -- `git status` afterwards shows exactly these five paths (A = added, M = modified):

    A  pandas_ta/<category>/<name>.py     the indicator; its body returns None until you write it
    M  pandas_ta/<category>/__init__.py   one `from .<name> import <name>` line
    M  pandas_ta/__init__.py              one `"<name>",` line in `Category[<category>]` (sorted)
    M  pandas_ta/core.py                  one `df.ta.<name>()` accessor inside the category's section
    A  tests/test_<name>.py               Gate B (mutant), C (reachability) and D (scale) tests,
                                          already written; they FAIL until the indicator is real

Each edit is one line or one block, placed before the first entry that sorts after the new name
(`Category` is fully sorted; most `__init__` files and core.py sections only roughly), so two ports
in the same category touch different lines unless their names are neighbours. In
`overlap/__init__.py` a new import always goes below the `ma` import (that file's ordering hazard).
All five texts are built in memory first; nothing is written unless every edit succeeds.

Refuses, writing nothing, when the category is unknown, the name is not a valid identifier, or the
name already exists anywhere (module file, `ta.<name>`, `Category`, accessor, test module). It does
not regenerate `docs/IndicatorDictionary.md`: do that once the indicator returns a Series (step list
in docs/ImplementingAnIndicator.md).
"""
import keyword
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MANIFEST = (
    ("A", "pandas_ta/{category}/{name}.py"),
    ("M", "pandas_ta/{category}/__init__.py"),
    ("M", "pandas_ta/__init__.py"),
    ("M", "pandas_ta/core.py"),
    ("A", "tests/test_{name}.py"),
)

MODULE = '''# -*- coding: utf-8 -*-
"""{upper} -- issue #<N>. Source: <cite it; Gate A checks the code against it>.

TODO(port): the formula, the Gate A reading and the causality argument
(docs/ImplementingAnIndicator.md).
"""
from pandas_ta.utils import get_offset, verify_series


def {name}(close, length=None, offset=None, **kwargs):
    """Indicator: {upper} (scaffolded by docs/new_indicator.py, not implemented yet)"""
    length = int(length) if length and int(length) > 0 else 10
    close = verify_series(close, length)
    offset = get_offset(offset)
    if close is None:
        return

    result = None  # TODO(port): compute from bars <= t only
    if result is None:
        return  # unimplemented: tests/test_{name}.py fails until this is a Series

    if offset != 0:
        result = result.shift(offset)
    result.name = f"{upper}_{{length}}"
    result.category = "{category}"
    return result
'''

ACCESSOR = '''    def {name}(self, length=None, offset=None, **kwargs):
        close = self._get_column(kwargs.pop("close", "close"))
        result = {name}(close=close, length=length, offset=offset, **kwargs)
        return self._post_process(result, **kwargs)

'''

TEST = '''# -*- coding: utf-8 -*-
"""`{name}` -- scaffolded by docs/new_indicator.py (#331); these tests FAIL until it is implemented.

Replace this docstring with what is pinned, in order of how much it would hurt to lose, with the
measured numbers (CLAUDE.md, "Port test modules"). Add the Gate A test against the source.
"""
import inspect
import sys

import numpy as np
import pandas as pd

from pandas_ta.{category}.{name} import {name}

N = 600


def _close(n=N, seed=0):
    rng = np.random.default_rng(seed)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))), index=pd.RangeIndex(n))


def _same(a, b):
    """Equal values and equal NaN masks."""
    return a.isna().equals(b.isna()) and a[a.notna()].equals(b[b.notna()])


def _reach(fn, n=N):
    """Largest number of bars before a cut whose output moves when only bars >= cut change."""
    close = _close(n)
    base = fn(close)
    worst = 0
    for cut in range(100, n - 20, 25):
        pert = close.copy()
        pert.iloc[cut:] = pert.iloc[cut:] * 1.37
        moved = fn(pert)
        head_b, head_m = base.iloc[:cut], moved.iloc[:cut]
        diff = ~((head_b == head_m) | (head_b.isna() & head_m.isna()))
        if diff.any():
            worst = max(worst, cut - int(np.argmax(diff.to_numpy())))
    return worst


def _mutant():
    """The module with its result read one bar AHEAD: a real non-causal implementation."""
    src = inspect.getsource(sys.modules["pandas_ta.{category}.{name}"])
    line = "    result.name = "
    assert src.count(line) == 1, "update the mutant: the module's final write moved"
    src = src.replace(line, "    result = result.shift(-1)\\n" + line)
    ns = {{"__name__": "{name}_mutant"}}
    exec(compile(src, "{name}_mutant", "exec"), ns)
    return ns["{name}"]


def test_it_returns_a_series():
    assert isinstance({name}(_close()), pd.Series)


def test_no_look_ahead_and_the_mutant_is_caught():
    assert _reach({name}) == 0
    assert _reach(_mutant()) >= 1


def test_scale_free():
    close = _close()
    base = {name}(close)
    for f in (8.0, 64.0):           # powers of two: bit-identical
        assert _same({name}(close * f), base), f
    for f in (10.0, 3.7):           # tolerance, NaN masks matching
        out = {name}(close * f)
        assert out.isna().equals(base.isna()), f
        np.testing.assert_allclose(out.dropna(), base.dropna(), rtol=1e-9, atol=0)


def test_produces_values_and_is_not_constant():
    \"\"\"A floor, not Gate C: some bars produce a value, and not all the same value.\"\"\"
    out = {name}(_close()).dropna()
    assert len(out) > 0 and out.nunique() > 1
'''


class Refused(Exception):
    """A refusal or a locate failure; raised before any file is written."""


def fail(msg):
    print(f"new_indicator: {msg}", file=sys.stderr)
    sys.exit(2)


def insert_before_first_later(lines, lo, hi, pattern, key, new):
    """Insert `new` before the first line in [lo, hi) whose `pattern` group sorts after `key`,
    else after the last matching line. Most category `__init__` files and core.py sections are
    not fully sorted, so this is the rule, not "sorted position"."""
    hits = [(i, m.group(1)) for i in range(lo, hi) for m in [re.match(pattern, lines[i])] if m]
    if not hits:
        raise Refused(f"no line matching {pattern!r} in the expected block")
    later = [i for i, k in hits if k > key]
    pos = later[0] if later else hits[-1][0] + 1
    lines[pos:pos] = new if isinstance(new, list) else [new]


# overlap/__init__.py: modules that import atr()/ma() must be imported below `from .ma import ma`
# (a circular self-import otherwise binds the submodule; see the comment block in that file).
# A new module cannot know yet what it will import, so it always goes below this marker.
INIT_FLOOR_MARKER = "# Must stay below the `ma` import."


def edit_init(text, name):
    lines = text.split("\n")
    lo = next((i + 1 for i, x in enumerate(lines) if x.strip() == INIT_FLOOR_MARKER), 0)
    insert_before_first_later(lines, lo, len(lines), r"from \.(\w+) import", name,
                              f"from .{name} import {name}")
    return "\n".join(lines)


def edit_category(text, category, name):
    lines = text.split("\n")
    try:
        lo = lines.index(f'    "{category}": [')
        hi = next(i for i in range(lo, len(lines)) if lines[i] == "    ],")
    except (ValueError, StopIteration):
        raise Refused(f"Category[{category!r}] block not found in pandas_ta/__init__.py")
    insert_before_first_later(lines, lo, hi, r'        "(\w+)",$', name, f'        "{name}",')
    return "\n".join(lines)


def edit_core(text, category, categories, name):
    lines = text.split("\n")
    headers = {f"    # {c.capitalize()}" for c in categories} | {"    # Utility"}
    try:
        lo = lines.index(f"    # {category.capitalize()}")
    except ValueError:
        raise Refused(f"no '# {category.capitalize()}' section in pandas_ta/core.py")
    # The section ends at the next category header, or at the end of the class/file
    # (`volume` is the last section and core.py ends inside the class).
    hi = next((i for i in range(lo + 1, len(lines)) if lines[i] in headers), None)
    if hi is None:
        hi = next((i for i in range(lo + 1, len(lines))
                   if lines[i] and not lines[i].startswith((" ", "#"))), len(lines))
    defs = [(i, m.group(1)) for i in range(lo, hi) for m in [re.match(r"    def (\w+)\(", lines[i])] if m]
    if not defs:
        raise Refused(f"no accessor in core.py's {category} section")
    block = ACCESSOR.format(name=name).split("\n")[:-1]   # ends with one blank line
    later = [i for i, k in defs if k > name]
    if later:
        pos = later[0]
    else:  # after the section's last accessor: just past its last non-blank line
        pos = hi
        while pos > lo and lines[pos - 1].strip() == "":
            pos -= 1
        block = [""] + block[:-1]
    lines[pos:pos] = block
    return "\n".join(lines)


def plan(category, name, ta, accessor_cls, repo=REPO):
    """Every path the scaffold writes -> its new full text. Nothing is written here, so a
    refusal or a failed locate leaves the tree untouched."""
    categories = list(ta.Category)
    if category not in categories:
        raise Refused(f"unknown category {category!r}; one of {categories}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
        raise Refused(f"{name!r} is not a lower-case identifier")
    rel = [p.format(category=category, name=name) for _, p in MANIFEST]
    taken = [why for why, hit in (
        (f"{rel[0]} exists", (repo / rel[0]).exists()),
        (f"{rel[4]} exists", (repo / rel[4]).exists()),
        (f"ta.{name} exists", hasattr(ta, name)),
        (f"df.ta.{name} exists", hasattr(accessor_cls, name)),
        (f"{name!r} is in Category", any(name in v for v in ta.Category.values())),
    ) if hit]
    if taken:
        raise Refused(f"refusing: {'; '.join(taken)}")
    read = lambda r: (repo / r).read_text(encoding="utf8")
    return {
        rel[0]: MODULE.format(name=name, upper=name.upper(), category=category),
        rel[1]: edit_init(read(rel[1]), name),
        rel[2]: edit_category(read(rel[2]), category, name),
        rel[3]: edit_core(read(rel[3]), category, categories, name),
        rel[4]: TEST.format(name=name, category=category),
    }


def main(argv):
    if len(argv) != 3:
        fail("usage: python docs/new_indicator.py <category> <name>")
    sys.path.insert(0, str(REPO))
    import pandas_ta as ta
    from pandas_ta.core import AnalysisIndicators

    try:
        texts = plan(argv[1], argv[2], ta, AnalysisIndicators)
    except Refused as e:
        fail(f"{e}; nothing written")
    for rel, text in texts.items():
        (REPO / rel).write_text(text, encoding="utf8")
    for (kind, _), rel in zip(MANIFEST, texts):
        print(f"{kind}  {rel}")
    print("next: docs/ImplementingAnIndicator.md")


if __name__ == "__main__":
    main(sys.argv)
