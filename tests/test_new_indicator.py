# -*- coding: utf-8 -*-
"""`docs/new_indicator.py` scaffolds every category correctly, in memory (#331 GEN-1).

What is pinned, worst loss first:

1. **Every category works.** The first version crashed on `volume` (the last core.py section,
   which ends inside the class) AFTER writing three of the five files. `plan()` now builds all five
   texts before anything is written; this runs it for every key of `Category`, with a name that
   sorts first and one that sorts last in its category, and writes nothing.
2. **Exactly the manifest, and only insertions.** Five paths; the three edited files change by
   inserted lines only (1, 1 and the accessor block), and the edited Python still parses.
3. **The overlap ordering hazard.** A new overlap import lands below the `ma` import marker.
4. **Refusal.** A taken name raises before any text is built.
"""
import ast
import difflib
import importlib.util
from pathlib import Path

import pytest

import pandas_ta as ta
from pandas_ta.core import AnalysisIndicators

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("new_indicator", ROOT / "docs" / "new_indicator.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

NAMES = ("aaa0_scaffold_probe", "zzz9_scaffold_probe")   # sort first / last in any category


def _inserted_only(old, new):
    ops = [op for op in difflib.SequenceMatcher(None, old.split("\n"), new.split("\n")).get_opcodes()
           if op[0] != "equal"]
    assert all(op[0] == "insert" for op in ops), ops
    return sum(j2 - j1 for _, _, _, j1, j2 in ops)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("category", list(ta.Category))
def test_every_category_scaffolds_in_memory(category, name):
    texts = gen.plan(category, name, ta, AnalysisIndicators)
    expected = [p.format(category=category, name=name) for _, p in gen.MANIFEST]
    assert list(texts) == expected
    for rel in expected:
        if (ROOT / rel).exists():   # edited, not created
            added = _inserted_only((ROOT / rel).read_text(encoding="utf8"), texts[rel])
            assert added == (5 if rel.endswith("core.py") else 1), (rel, added)
        else:
            assert not (ROOT / rel).exists()
        if rel.endswith(".py"):
            ast.parse(texts[rel])
    # the Category list stays sorted with the new name in it
    tree = ast.parse(texts["pandas_ta/__init__.py"])
    cat = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and getattr(n.targets[0], "id", None) == "Category")
    names = next(ast.literal_eval(v) for k, v in zip(cat.keys, cat.values) if k.value == category)
    assert name in names and names == sorted(names)
    # the accessor sits inside its own category's section of core.py
    core = texts["pandas_ta/core.py"].split("\n")
    at = core.index(f"    def {name}(self, length=None, offset=None, **kwargs):")
    header = max(i for i, x in enumerate(core[:at])
                 if x in {f"    # {c.capitalize()}" for c in ta.Category} | {"    # Utility"})
    assert core[header] == f"    # {category.capitalize()}"


def test_a_new_overlap_import_goes_below_the_ma_marker():
    text = gen.plan("overlap", NAMES[0], ta, AnalysisIndicators)["pandas_ta/overlap/__init__.py"]
    lines = text.split("\n")
    assert lines.index(f"from .{NAMES[0]} import {NAMES[0]}") > lines.index(gen.INIT_FLOOR_MARKER)


@pytest.mark.parametrize("category,name", [("trend", "bos"), ("nope", "x_probe"), ("trend", "Bad")])
def test_refusals_raise_before_anything_is_built(category, name):
    with pytest.raises(gen.Refused):
        gen.plan(category, name, ta, AnalysisIndicators)
