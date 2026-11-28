# -*- coding: utf-8 -*-
"""Scaffold a new indicator: the five wiring touch points, nothing else (#331 GEN-1).

    python docs/new_indicator.py <category> <name>

Run from the repo root. `<category>` is a key of `pandas_ta.Category` (read from the package,
not retyped here); `<name>` is a new lower-case identifier.

MANIFEST -- `git status` afterwards shows exactly these five paths (A = added, M = modified):

    A  pandas_ta/<category>/<name>.py     the indicator; its body returns None until you write it
    M  pandas_ta/<category>/__init__.py   one `from .<name> import <name>` line, in sorted position
    M  pandas_ta/__init__.py              one `"<name>",` line in `Category[<category>]`, sorted
    M  pandas_ta/core.py                  one `df.ta.<name>()` accessor, in sorted position inside
                                          the category's section
    A  tests/test_<name>.py               Gate B (mutant), C (reachability) and D (scale) tests,
                                          already written; they FAIL until the indicator is real

Every edit is one line or one block placed by sort order, so two ports in the same category touch
different lines unless their names are alphabetical neighbours.

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


def test_reachable_and_not_constant():
    out = {name}(_close()).dropna()
    assert 0 < len(out) < N + 1 and out.nunique() > 1
'''


def fail(msg):
    print(f"new_indicator: {msg}", file=sys.stderr)
    sys.exit(2)


def insert_sorted(lines, lo, hi, pattern, key, new):
    """Insert `new` before the first line in [lo, hi) whose `pattern` group sorts after `key`."""
    hits = [(i, m.group(1)) for i in range(lo, hi) for m in [re.match(pattern, lines[i])] if m]
    if not hits:
        fail(f"no line matching {pattern!r} in the expected block")
    later = [i for i, k in hits if k > key]
    pos = later[0] if later else hits[-1][0] + 1
    lines[pos:pos] = new if isinstance(new, list) else [new]


def edit_init(path, name):
    lines = path.read_text(encoding="utf8").split("\n")
    insert_sorted(lines, 0, len(lines), r"from \.(\w+) import", name, f"from .{name} import {name}")
    path.write_text("\n".join(lines), encoding="utf8")


def edit_category(path, category, name):
    lines = path.read_text(encoding="utf8").split("\n")
    lo = lines.index(f'    "{category}": [')
    hi = next(i for i in range(lo, len(lines)) if lines[i] == "    ],")
    insert_sorted(lines, lo, hi, r'        "(\w+)",$', name, f'        "{name}",')
    path.write_text("\n".join(lines), encoding="utf8")


def edit_core(path, category, categories, name):
    lines = path.read_text(encoding="utf8").split("\n")
    headers = {f"    # {c.capitalize()}" for c in categories} | {"    # Utility"}
    lo = lines.index(f"    # {category.capitalize()}")
    hi = next((i for i in range(lo + 1, len(lines)) if lines[i] in headers), None)
    if hi is None:   # last section: up to the end of the class
        hi = next(i for i in range(lo + 1, len(lines)) if lines[i] and not lines[i].startswith(" "))
    defs = [(i, m.group(1)) for i in range(lo, hi) for m in [re.match(r"    def (\w+)\(", lines[i])] if m]
    if not defs:
        fail(f"no accessor in core.py's {category} section")
    later = [i for i, k in defs if k > name]
    if later:
        pos = later[0]
    else:  # after the last accessor block: the next blank-then-dedent boundary
        pos = hi
        while lines[pos - 1].strip() == "":
            pos -= 1
        pos += 1
    lines[pos:pos] = ACCESSOR.format(name=name).split("\n")[:-1]
    path.write_text("\n".join(lines), encoding="utf8")


def main(argv):
    if len(argv) != 3:
        fail("usage: python docs/new_indicator.py <category> <name>")
    category, name = argv[1], argv[2]
    sys.path.insert(0, str(REPO))
    import pandas_ta as ta
    from pandas_ta.core import AnalysisIndicators

    categories = list(ta.Category)
    if category not in categories:
        fail(f"unknown category {category!r}; one of {categories}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or keyword.iskeyword(name):
        fail(f"{name!r} is not a lower-case identifier")
    paths = {kind: REPO / p.format(category=category, name=name) for kind, p in
             (("module", MANIFEST[0][1]), ("test", MANIFEST[4][1]))}
    taken = [why for why, hit in (
        (f"{paths['module'].relative_to(REPO)} exists", paths["module"].exists()),
        (f"{paths['test'].relative_to(REPO)} exists", paths["test"].exists()),
        (f"ta.{name} exists", hasattr(ta, name)),
        (f"df.ta.{name} exists", hasattr(AnalysisIndicators, name)),
        (f"{name!r} is in Category", any(name in v for v in ta.Category.values())),
    ) if hit]
    if taken:
        fail(f"refusing, nothing written: {'; '.join(taken)}")

    upper = name.upper()
    paths["module"].write_text(MODULE.format(name=name, upper=upper, category=category), encoding="utf8")
    edit_init(REPO / "pandas_ta" / category / "__init__.py", name)
    edit_category(REPO / "pandas_ta" / "__init__.py", category, name)
    edit_core(REPO / "pandas_ta" / "core.py", category, categories, name)
    paths["test"].write_text(TEST.format(name=name, category=category), encoding="utf8")
    for kind, p in MANIFEST:
        print(f"{kind}  {p.format(category=category, name=name)}")
    print("next: docs/ImplementingAnIndicator.md")


if __name__ == "__main__":
    main(sys.argv)
