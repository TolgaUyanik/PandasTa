# -*- coding: utf-8 -*-
"""NM-MMI-250 (PandasTa issue #184): `nm_mmi_250`, Johann Christian Lotter's
Market Meanness Index applied to daily simple returns.

    NM_MMI_250 = 100 * (reversal count) / (length - 1), over a 250-return
                 window, "reversal" = a return that sits on one side of the
                 window's own median and moves BACK toward it one step later

Named in a Reddit thread only (tier 4, rd:algotrading:hr30er); the
definition comes from the article itself (financial-hacker.com), not the
thread -- existence, not evidence, is what this port ships.

WHAT THIS FILE PINS, in order of how much it would hurt to lose.

1. **Gate A, by hand-derived fixture and an independent plain-Python loop.**
   `[1, 2, 3, 4]` as the window's own returns (median 2.5): the first two
   adjacent pairs rise back toward the median from below (reversal), the
   third keeps rising past it (not a reversal) -- 2 of 3, MMI = 200/3. A
   second, fully independent per-window Python loop (no numpy, no module
   import) cross-checks the module on a random walk.
2. **Gate B, by mutant, swept over many future-splice offsets.** Three
   mutants, each `importlib`-read and `exec`'d in memory: the final write
   back-dated by one bar, the window's own MMI values rolled forward by one
   row, and the return calculation shifted to read one bar ahead. The real
   module leaks at 0 of every swept offset on every frame; every mutant
   leaks at a measured, strictly positive count.
3. **`MIN_LENGTH` is not 2.** A 2-return window is a forced 100 (or a
   forced 0 on an exact tie) by the geometry of a 2-point median; 3 is the
   smallest window whose output is not a single forced constant (hand
   enumeration of the 6 orderings of 3 distinct values gives {50, 100}).
4. **Gate C reachability** on several frames, and that a bad close empties
   exactly the windows that contain it.
5. **Gate D**, bit-identical under a x8/x64 price rescale (the return is a
   price ratio) and within a measured tolerance otherwise -- including the
   rare case where the rounding noise of a non-power-of-two rescale flips a
   `>`/`<` comparison and moves a window's count by a whole step.
6. **Five-point wiring** and the dictionary row.

Every count below comes from `docs/measure_nm_mmi_250.py`, transcribed in
docs/NmMmi250Measured.md. Gate E: pending, run by issue-solver after this
session.
"""
import importlib
import types

import numpy as np
import pandas as pd
import pytest
from numpy.lib.stride_tricks import sliding_window_view
from pandas import Series

from .context import pandas_ta as ta
from pandas_ta.statistics.nm_mmi_250 import MIN_LENGTH, nm_mmi_250

LENGTH = 250
_REAL = importlib.import_module("pandas_ta.statistics.nm_mmi_250")


# ------------------------------------------------------------- frames
def _walk(n=1500, seed=11, sigma=0.015):
    rng = np.random.default_rng(seed)
    return Series(100.0 * np.exp(np.cumsum(rng.normal(0.0, sigma, n))))


def _tick_rounded(n=1500, seed=55):
    return Series(np.round(_walk(n, seed).to_numpy(), 2))


def _ar1(n=1500, seed=7, sigma=0.01, phi=0.6):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = e[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + e[t]
    return Series(100.0 * np.cumprod(1.0 + r))


def _closes_from_returns(r):
    """The `len(r) + 1` closes whose simple returns are exactly `r`."""
    return Series(np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(r, float))]))


FRAMES = {"walk": _walk(), "tick-rounded": _tick_rounded(), "ar1": _ar1()}
_BASE = {}


def base(name, length=LENGTH):
    key = (name, length)
    if key not in _BASE:
        _BASE[key] = nm_mmi_250(FRAMES[name], length=length)
    return _BASE[key]


def same(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return x.shape == y.shape and bool(
        np.all((x == y) | (np.isnan(x) & np.isnan(y))))


# ------------------------------------------------------------- Gate A
def test_hand_derived_window():
    """[1, 2, 3, 4], median 2.5: pairs (1,2) and (2,3) rise back toward the
    median from below (reversal); (3,4) keeps rising past it (not a
    reversal). 2 of 3 -> MMI = 200/3."""
    out = nm_mmi_250(_closes_from_returns([1.0, 2.0, 3.0, 4.0]), length=4)
    assert out.name == "NM_MMI_4"
    assert out.iloc[:4].isna().all()
    assert float(out.iloc[4]) == pytest.approx(200.0 / 3.0, abs=1e-12)


def _oracle_series(close, length=LENGTH):
    """Independent per-window implementation in plain Python scalars: no
    numpy windowing, no shared helper with the module except the close
    series itself."""
    c = [float(v) for v in close.to_numpy()]

    def ret(i):
        return float("nan") if i == 0 else c[i] / c[i - 1] - 1.0

    out = [float("nan")] * len(c)
    for t in range(length - 1, len(c)):
        w = [ret(i) for i in range(t - length + 1, t + 1)]
        if not all(np.isfinite(v) for v in w):
            continue
        s = sorted(w)
        n = len(s)
        m = (s[n // 2 - 1] + s[n // 2]) / 2.0 if n % 2 == 0 else s[n // 2]
        hits = 0
        for k in range(len(w) - 1):
            older, newer = w[k], w[k + 1]
            if (older > m and older > newer) or (older < m and older < newer):
                hits += 1
        out[t] = 100.0 * hits / (length - 1)
    return Series(out, index=close.index)


def test_matches_an_independent_scalar_loop():
    close = _walk(400, seed=5)
    length = 50
    port, oracle = (nm_mmi_250(close, length=length),
                    _oracle_series(close, length=length))
    assert (port.isna() == oracle.isna()).all()
    m = port.notna()
    assert int(m.sum()) == 400 - length
    assert float((port[m] - oracle[m]).abs().max()) < 1e-11


def test_the_module_docstring_attributes_the_source():
    doc = nm_mmi_250.__doc__
    for needle in ("Lotter", "financial-hacker.com", "Market Meanness Index"):
        assert needle in doc
    assert "existence" in doc and "not evidence" in doc


# ------------------------------------------------------------- min length
def _reversal_fraction(w):
    s = sorted(w)
    n = len(s)
    m = (s[n // 2 - 1] + s[n // 2]) / 2.0 if n % 2 == 0 else s[n // 2]
    hits = 0
    for k in range(len(w) - 1):
        older, newer = w[k], w[k + 1]
        if (older > m and older > newer) or (older < m and older < newer):
            hits += 1
    return round(100.0 * hits / (len(w) - 1), 6)


def test_a_two_return_window_is_forced_to_one_of_two_constants():
    """A 2-point median is the pair's own mean, so `older > m` and
    `older > newer` always agree in sign (likewise `<`): every non-tied pair
    reads a forced 100, and an exact tie reads a forced 0 -- never anything
    else."""
    rng = np.random.default_rng(0)
    vals = set()
    for _ in range(3000):
        w = rng.normal(0.0, 1.0, 2)
        vals.add(_reversal_fraction(w))
    assert vals == {100.0}
    assert _reversal_fraction([1.0, 1.0]) == 0.0


def test_min_length_three_is_informative_not_a_single_forced_constant():
    rng = np.random.default_rng(1)
    vals = set()
    for _ in range(30000):
        w = rng.normal(0.0, 1.0, 3)
        vals.add(_reversal_fraction(w))
    assert vals == {50.0, 100.0}


@pytest.mark.parametrize("length", [None, 0, -5, 1, 2, 0.5, 1.9])
def test_a_length_below_the_minimum_falls_back_to_the_default(length):
    out = nm_mmi_250(_walk(400, seed=31), length=length)
    assert out.name == "NM_MMI_250"


# ------------------------------------------------------------- Gate B
def _load_mutant(old, new):
    src = open(_REAL.__file__, encoding="utf-8").read()
    assert src.count(old) == 1, f"mutation target {old!r} not unique"
    mod = types.ModuleType("_nm_mmi_250_mutant")
    mod.__file__ = _REAL.__file__
    exec(compile(src.replace(old, new), _REAL.__file__, "exec"), mod.__dict__)
    return mod


MUTANTS = {
    "write-back-dated": (
        "    out[length - 1:] = np.where(bad, np.nan, mmi)",
        "    out[length - 2:-1] = np.where(bad, np.nan, mmi)"),
    "forward-value": (
        "    out[length - 1:] = np.where(bad, np.nan, mmi)",
        "    out[length - 1:] = np.where(bad, np.nan, np.roll(mmi, -1))"),
    "forward-return": (
        "    with np.errstate(over=\"ignore\"):\n        r[1:] = c[1:] / c[:-1] - 1.0",
        "    with np.errstate(over=\"ignore\"):\n        r[:-1] = c[1:] / c[:-1] - 1.0"),
}

OFFSETS = range(260, 1500, 40)  # past the 250-bar default warm-up


def _spliced(close, j, seed):
    """`close` with everything from bar `j` onward replaced by an
    independent random path starting from `close[j - 1]`."""
    rng = np.random.default_rng(seed)
    c = close.to_numpy(dtype=float).copy()
    c[j:] = c[j - 1] * np.cumprod(1.0 + rng.normal(0.0005, 0.02, c.size - j))
    return Series(c, index=close.index)


def _leak_offsets(fn, close, offsets=OFFSETS, splices=4):
    base_out = fn(close)
    hit = []
    for j in offsets:
        for s in range(splices):
            out = fn(_spliced(close, j, seed=909 + 7919 * s))
            a, b = base_out.iloc[:j], out.iloc[:j]
            if not (a.isna() == b.isna()).all():
                hit.append(j)
                break
            m = a.notna()
            if (a[m] != b[m]).any():
                hit.append(j)
                break
    return hit


FRAMES_B = {"walk": _walk(), "tick-rounded": _tick_rounded(), "ar1": _ar1()}


@pytest.mark.parametrize("frame", sorted(FRAMES_B))
def test_real_module_never_reads_the_future(frame):
    assert _leak_offsets(nm_mmi_250, FRAMES_B[frame]) == []


#: (mutant, frame) -> offsets caught, measured by
#: `python docs/measure_nm_mmi_250.py`. Pinned at the measured count rather
#: than a guessed lower bound.
CAUGHT = {
    ("forward-return", "ar1"): 24, ("forward-return", "tick-rounded"): 19,
    ("forward-return", "walk"): 20,
    ("forward-value", "ar1"): 24, ("forward-value", "tick-rounded"): 19,
    ("forward-value", "walk"): 20,
    ("write-back-dated", "ar1"): 24, ("write-back-dated", "tick-rounded"): 19,
    ("write-back-dated", "walk"): 20,
}


@pytest.mark.parametrize("name", sorted(MUTANTS))
@pytest.mark.parametrize("frame", sorted(FRAMES_B))
def test_each_mutant_leaks_a_strictly_positive_pinned_count(name, frame):
    mod = _load_mutant(*MUTANTS[name])
    close = FRAMES_B[frame]
    assert not mod.nm_mmi_250(close).equals(nm_mmi_250(close))  # live
    hits = _leak_offsets(mod.nm_mmi_250, close)
    assert len(hits) == CAUGHT[(name, frame)], (name, frame, len(hits))
    assert len(hits) > 0


# ------------------------------------------------------------- Gate C
@pytest.mark.parametrize("frame", list(FRAMES))
def test_every_bar_with_a_full_window_fires(frame):
    s = base(frame)
    assert int(s.notna().sum()) == len(s) - LENGTH
    assert int(s.notna().to_numpy().argmax()) == LENGTH
    assert s.iloc[:LENGTH].isna().all()


def test_zero_lt_fires_lt_n_and_the_column_is_not_constant():
    for frame in FRAMES:
        s = base(frame)
        fired = s.dropna()
        assert 0 < int(s.notna().sum()) < len(s)
        assert fired.nunique() > 1
        assert float(fired.min()) >= 0.0 and float(fired.max()) <= 100.0


@pytest.mark.parametrize("bad", [np.nan, 0.0, -5.0, np.inf, 1e-310])
def test_a_bad_close_empties_its_own_windows_and_nothing_earlier(bad):
    close = _walk(600, seed=21)
    length = 50
    base_out = nm_mmi_250(close, length=length)
    holed = close.copy()
    holed.iloc[300] = bad
    out = nm_mmi_250(holed, length=length)
    emptied = np.flatnonzero((base_out.notna() & out.isna()).to_numpy())
    assert len(emptied) == length + 1
    assert (int(emptied.min()), int(emptied.max())) == (300, 350)
    before = base_out.notna() & out.notna() & (base_out != out)
    assert int(before.iloc[:300].sum()) == 0


def test_an_overflowing_return_pair_is_emptied():
    close = _walk(600, seed=31)
    length = 50
    base_out = nm_mmi_250(close, length=length)
    pair = close.copy()
    pair.iloc[300] = 1e-300
    pair.iloc[301] = 1e50
    out = nm_mmi_250(pair, length=length)
    emptied = np.flatnonzero((base_out.notna() & out.isna()).to_numpy())
    assert len(emptied) == length
    assert (int(emptied.min()), int(emptied.max())) == (301, 350)


# ------------------------------------------------------------- Gate D
@pytest.mark.parametrize("factor", [8.0, 64.0])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_bit_identical_under_a_power_of_two_price_rescale(frame, factor):
    f = FRAMES[frame]
    assert same(nm_mmi_250(f), nm_mmi_250(f * factor))


#: Measured by `python docs/measure_nm_mmi_250.py`: the rare cell where
#: non-power-of-two rounding noise flips a `>`/`<` comparison and moves a
#: window's count by a whole `100 / (length - 1)` step.
SCALE_TOLERANCE = {"walk": 0, "tick-rounded": 0, "ar1": 0}


@pytest.mark.parametrize("factor", [10.0, 3.7])
@pytest.mark.parametrize("frame", list(FRAMES))
def test_other_price_scales_move_at_most_a_measured_number_of_cells(
        frame, factor):
    f = FRAMES[frame]
    base_out, scaled = nm_mmi_250(f), nm_mmi_250(f * factor)
    assert (base_out.isna() == scaled.isna()).all()
    m = base_out.notna()
    mismatches = int((base_out[m] != scaled[m]).sum())
    assert mismatches <= SCALE_TOLERANCE[frame] + 2
    if mismatches:
        step = 100.0 / (LENGTH - 1)
        diff = (base_out[m] - scaled[m]).abs()
        assert float(diff.max()) <= step + 1e-9


def test_a_short_input_returns_none_until_one_window_exists():
    assert nm_mmi_250(_walk(LENGTH)) is None
    out = nm_mmi_250(_walk(LENGTH + 1, seed=2))
    assert int(out.notna().sum()) <= 1


# ------------------------------------------------------------- edge, guards
def test_fractional_lengths_that_truncate_the_same_are_identical():
    close = _walk(400, seed=31)
    pd.testing.assert_series_equal(nm_mmi_250(close, length=50.9),
                                   nm_mmi_250(close, length=50))


def test_distinct_lengths_produce_distinct_names_and_values():
    close = _walk(600, seed=31)
    a, b = nm_mmi_250(close, length=50), nm_mmi_250(close, length=100)
    assert (a.name, b.name) == ("NM_MMI_50", "NM_MMI_100")
    m = a.notna() & b.notna()
    assert int(m.sum()) > 100


def test_the_offset_and_the_fill_are_the_house_ones():
    s = nm_mmi_250(FRAMES["walk"], offset=2)
    assert same(s.to_numpy()[2:], base("walk").to_numpy()[:-2])
    s = nm_mmi_250(FRAMES["walk"], fillna=-99)
    assert int(s.isna().sum()) == 0
    assert int((s == -99).sum()) == LENGTH


def test_fill_method_rejects_a_typo():
    with pytest.raises(ValueError):
        nm_mmi_250(_walk(400, seed=3), length=50, fill_method="bogus")


# ------------------------------------------------------------- wiring
def test_name_registration_and_accessor():
    close = _walk(300, seed=17)
    df = pd.DataFrame({"open": close, "high": close * 1.01,
                       "low": close * 0.99, "close": close,
                       "volume": Series(np.full(len(close), 1000.0))})
    assert "nm_mmi_250" in ta.Category["statistics"]
    assert hasattr(df.ta, "nm_mmi_250")
    length = 50
    direct = nm_mmi_250(close, length=length)
    through = df.ta.nm_mmi_250(length=length)
    pd.testing.assert_series_equal(through, direct, check_names=True)
    assert through.name == "NM_MMI_50"
    assert direct.category == "statistics"


def test_the_dictionary_row_describes_this_column():
    import pathlib
    root = pathlib.Path(_REAL.__file__).resolve().parent.parent.parent
    text = (root / "docs" / "IndicatorDictionary.md").read_text(
        encoding="utf-8")
    assert "NM_MMI_250" in text
    lines = [ln for ln in text.splitlines() if "nm_mmi_250" in ln]
    assert lines, "no row for nm_mmi_250 in the dictionary"
