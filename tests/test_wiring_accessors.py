# -*- coding: utf-8 -*-
"""Tests for the DataFrame-extension wiring itself (WIRING-1, WIRING-2).

These do not test any indicator's MATH.  They pin the fifth touch point of a
port -- the `df.ta.<name>` accessor in `pandas_ta/core.py` -- which is the one
that was skipped on eleven indicators (`wavetrend`, `ema_align`, `ichimoku_ml`,
`linreg_channel`, `bos`, `choch`, `fvg`, `halftrend`, `ob`, `zigzag`,
`vol_delta`).  Each was registered in `Category` but had no accessor, so
`df.ta.strategy()` and the affected `df.ta.strategy("<category>")` runs raised
`AttributeError` and every column those eleven produce was dark.

`test_every_registered_indicator_has_an_accessor` is the guard that keeps that
from recurring: it fails the moment a name enters `Category` without a matching
method, which is exactly the state the eleven were in.

`test_full_strategy_runs_with_no_exclude_list` is the end-to-end form of the
same claim, and is also what pins the two import/API defects that blocked it:
`aberration` (its `sma` bound the submodule, not the function) and `mcgd`
(`Series.append`, removed in pandas 2.0).
"""
import pathlib
import subprocess
import sys
import types

import numpy as np
import pandas as pd
import pytest

from .context import pandas_ta


def _ohlcv(n=600, level=100.0, seed=11):
    """A deterministic OHLCV frame long enough for every indicator's warm-up."""
    rng = np.random.default_rng(seed)
    close = level * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    spread = close * np.abs(rng.normal(0, 0.006, n))
    open_ = close * (1 + rng.normal(0, 0.004, n))
    high = np.maximum.reduce([close + spread, open_, close])
    low = np.minimum.reduce([close - spread, open_, close])
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(1e5, 1e6, n).astype(float),
        },
        index=pd.date_range("2022-01-03", periods=n, freq="B"),
    )


ELEVEN = [
    "wavetrend", "ema_align", "ichimoku_ml", "linreg_channel", "bos", "choch",
    "fvg", "halftrend", "ob", "zigzag", "vol_delta",
]


def _registered_names():
    return sorted({n for names in pandas_ta.Category.values() for n in names})


def test_every_registered_indicator_has_an_accessor():
    """Every name in `Category` is reachable as `df.ta.<name>`.

    `Category` is what `df.ta.strategy()` iterates, so a name in it without an
    accessor is not a cosmetic gap -- it is an `AttributeError` mid-run.
    """
    df = pd.DataFrame()
    missing = [n for n in _registered_names() if not hasattr(df.ta, n)]
    assert missing == [], (
        f"{len(missing)} indicator(s) registered in Category with no accessor "
        f"in core.py: {missing}"
    )


def _price_kwargs(fn, df):
    """The OHLCV arguments `fn` actually declares, taken from `df`."""
    declared = fn.__code__.co_varnames[:fn.__code__.co_argcount]
    return {
        arg: df[col]
        for arg, col in (("open_", "open"), ("high", "high"), ("low", "low"),
                         ("close", "close"), ("volume", "volume"))
        if arg in declared
    }


def _as_frame(result):
    return result.to_frame() if isinstance(result, pd.Series) else result


# One NON-DEFAULT value per accessor parameter.  Defaults are useless here: a
# parameter forwarded under the wrong name lands in **kwargs, is ignored, and
# the indicator silently returns its default-length output -- the exact defect
# the `supertrend` accessor carries a comment about (core.py, "unread").  These
# values must differ from the indicator's own defaults or the second assertion
# in the test below is vacuous.
NON_DEFAULT_KWARGS = {
    "wavetrend": {"n1": 7, "n2": 15},
    "ema_align": {},                       # takes no parameter beyond offset
    "ichimoku_ml": {"tenkan": 5, "kijun": 13, "senkou": 34},
    "linreg_channel": {"length": 40},
    "bos": {"swing_length": 12},
    "choch": {"swing_length": 12},
    "fvg": {"max_zones": 3},
    "halftrend": {"atr_period": 9, "amplitude": 3},
    "ob": {"max_zones": 3},
    "zigzag": {"pct_threshold": 0.02},
    "vol_delta": {},                       # takes no parameter beyond offset
}


@pytest.mark.parametrize("name", ELEVEN)
def test_the_eleven_return_data_through_their_accessor(name):
    """Each new accessor resolves its own price columns and returns real data.

    A method that exists but hands the indicator the wrong column would still
    satisfy `hasattr`, so this asserts the result is non-empty and agrees with
    the standalone call on the same frame.
    """
    df = _ohlcv()
    result = getattr(df.ta, name)()
    assert result is not None, f"df.ta.{name}() returned None"

    frame = _as_frame(result)
    assert len(frame) == len(df)
    assert frame.notna().to_numpy().any(), f"df.ta.{name}() is entirely NaN"

    # Same indicator, called the standard way -- the accessor must not change
    # the numbers, only where the inputs come from.
    fn = getattr(pandas_ta, name)
    direct = _as_frame(fn(**_price_kwargs(fn, df)))
    pd.testing.assert_frame_equal(frame, direct, check_names=False)


# Every accessor parameter can now be shown to change its indicator's output.
# `fvg` was the lone exception until FVGDEAD landed: `max_zones` capped two
# columns that were constant zero by construction, so the cap could not matter.
NO_OBSERVABLE_EFFECT = set()


@pytest.mark.parametrize("name", ELEVEN)
def test_offset_is_honored_by_every_new_accessor(name):
    """`offset` — the one keyword all eleven accept — actually shifts.

    Every accessor forwards `offset` by hand, so a typo in that single line
    (`offsett=offset`) would be invisible to the parameter tests above, which
    only exercise indicator-specific keywords.  `ichimoku_ml` is included
    deliberately: its indicator has no `offset`, so its accessor applies the
    shift itself, and refusing the keyword instead would abort any
    `df.ta.strategy(..., offset=n)` run.
    """
    df = _ohlcv()
    shifted = _as_frame(getattr(df.ta, name)(offset=2))
    base = _as_frame(getattr(df.ta, name)())
    pd.testing.assert_frame_equal(shifted, base.shift(2), check_names=False)


@pytest.mark.parametrize("name", [n for n in ELEVEN if NON_DEFAULT_KWARGS[n]])
def test_the_eleven_forward_their_parameters_under_the_right_name(name):
    """Each parameter arrives at the indicator, spelled the way it declares it.

    This is the guard against the defect the `supertrend` accessor carries a
    comment about: a keyword forwarded under the wrong name lands in `**kwargs`,
    is ignored, and the indicator quietly returns default output.  A spy on the
    function `core.py` actually calls catches that for EVERY parameter,
    including ones whose value happens not to move the numbers.
    """
    df = _ohlcv()
    kwargs = NON_DEFAULT_KWARGS[name]
    seen = {}

    real = getattr(pandas_ta.core, name)

    def spy(*args, **kw):
        seen.update(kw)
        return real(*args, **kw)

    setattr(pandas_ta.core, name, spy)
    try:
        getattr(df.ta, name)(**kwargs)
    finally:
        setattr(pandas_ta.core, name, real)

    assert seen, f"df.ta.{name}() never called {name}()"
    for key, value in kwargs.items():
        assert key in seen, (
            f"df.ta.{name}({kwargs}) did not pass {key!r} to {name}(); it was "
            f"dropped or renamed. Passed: {sorted(seen)}"
        )
        assert seen[key] == value, (
            f"df.ta.{name} passed {key}={seen[key]!r}, expected {value!r}"
        )


@pytest.mark.parametrize(
    "name",
    [n for n in ELEVEN if NON_DEFAULT_KWARGS[n] and n not in NO_OBSERVABLE_EFFECT],
)
def test_non_default_parameters_change_the_output(name):
    """The forwarded value is actually USED, and matches the standalone call.

    Equality with the standalone call proves the value arrives intact;
    inequality with the all-defaults call proves the indicator acts on it.
    """
    df = _ohlcv()
    kwargs = NON_DEFAULT_KWARGS[name]
    fn = getattr(pandas_ta, name)

    via_accessor = _as_frame(getattr(df.ta, name)(**kwargs))
    direct = _as_frame(fn(**_price_kwargs(fn, df), **kwargs))
    pd.testing.assert_frame_equal(via_accessor, direct, check_names=False)

    defaults = _as_frame(getattr(df.ta, name)())
    same_values = via_accessor.shape == defaults.shape and np.array_equal(
        via_accessor.to_numpy(), defaults.to_numpy(), equal_nan=True
    )
    assert not same_values, (
        f"df.ta.{name}({kwargs}) is identical to df.ta.{name}() -- the "
        f"parameter reached {name}() but changed nothing"
    )


def test_full_strategy_runs_with_no_exclude_list():
    """The SERIAL form of the WIRING-1 acceptance criterion, `cores=0`.

    It exercises the eleven new accessors together with `aberration`
    (WIRING-2) and `mcgd`, and fails with `AttributeError` or `TypeError` if
    any of them regress.  `cores=0` keeps a failure in this process, where
    pytest can show it; the default multiprocessing path is covered separately
    by `test_full_strategy_runs_on_the_default_multiprocessing_path`.
    """
    df = _ohlcv()
    before = df.shape[1]
    df.ta.strategy(cores=0)  # cores=0 keeps the failure in THIS process
    assert df.shape[1] > before, "strategy() appended no columns"

    # Spot-check that the previously dark indicators actually contributed --
    # one column from each of the three defects this task fixed.
    for column in ("WAVETREND", "ICHI_PRICE_VS_CLOUD", "EMA_ALIGN_BULL",
                   "BOS_BULL", "CHoCH_BULL", "FVG_BULL", "HALFTREND",
                   "LINREG_SLOPE"):
        assert column in df.columns, f"{column} missing after strategy()"
    assert any(c.startswith("ZIGZAG_") for c in df.columns)      # zigzag
    assert any(c.startswith("OB_") for c in df.columns)          # ob
    assert any(c.startswith("VOL_DELTA") for c in df.columns)    # vol_delta
    assert any(c.startswith("ABER_") for c in df.columns)        # WIRING-2
    assert any(c.startswith("MCGD_") for c in df.columns)        # pandas 2.x fix


def test_full_strategy_runs_on_the_default_multiprocessing_path():
    """The criterion as WRITTEN: bare `df.ta.strategy()`, default `cores`.

    The serial test above uses `cores=0`, which is a different code path --
    the default fans out through `Pool.imap` and `_mp_worker`, and rebuilds the
    frame parent-side.  An accessor that only works in-process would pass there
    and fail here.
    """
    df = _ohlcv()
    before = df.shape[1]
    df.ta.strategy()
    assert df.shape[1] > before, "strategy() appended no columns"
    for column in ("WAVETREND", "ICHI_PRICE_VS_CLOUD", "EMA_ALIGN_BULL",
                   "BOS_BULL", "CHoCH_BULL", "FVG_BULL", "HALFTREND",
                   "LINREG_SLOPE"):
        assert column in df.columns, f"{column} missing after strategy()"
    assert any(c.startswith("ABER_") for c in df.columns)
    assert any(c.startswith("MCGD_") for c in df.columns)


@pytest.mark.parametrize("category", ["overlap", "trend", "momentum", "volume"])
def test_each_previously_broken_category_runs(category):
    """The four category runs that used to raise on a missing accessor.

    Run with a strategy-level `offset`, which `strategy()` fans into every
    indicator call: an accessor that rejects the keyword instead of honouring it
    takes the whole category down, which is how the `ichimoku_ml` accessor
    regressed once already.
    """
    df = _ohlcv()
    before = df.shape[1]
    df.ta.strategy(category, cores=0, offset=1)
    assert df.shape[1] > before, f"strategy({category!r}) appended no columns"
    if category == "overlap":
        assert "ICHI_PRICE_VS_CLOUD" in df.columns


def test_no_module_shadows_a_function_name_anywhere_in_the_package():
    """The WIRING-2 defect CLASS, not the one instance that was reported.

    `from pandas_ta.overlap import sma` binds the SUBMODULE while pandas_ta is
    still importing itself, and the call site then raises
    `TypeError: 'module' object is not callable`.  Three modules had it:
    `volatility/aberration.py` (reported), `overlap/zlma.py` (every `mamode`)
    and `volatility/ui.py` (`everget=True`).  Fixing the reported one only is
    how the other two survived, so this scans the whole package instead.
    """
    offenders = []
    for module_name, module in sorted(sys.modules.items()):
        if not module_name.startswith("pandas_ta.") or module is None:
            continue
        for attr in dir(module):
            if attr.startswith("_"):
                continue
            value = getattr(module, attr, None)
            # The gate asks the SHADOWING MODULE whether it defines a callable
            # of the same name -- `pandas_ta.overlap.sma.sma`. Checking only the
            # package top level would miss any helper that is not re-exported
            # there, while its call site still raises.
            if (isinstance(value, types.ModuleType)
                    and value.__name__.startswith("pandas_ta.")
                    and (callable(getattr(value, attr, None))
                         or callable(getattr(pandas_ta, attr, None)))):
                offenders.append(f"{module_name}.{attr} -> module {value.__name__}")

    assert offenders == [], (
        "module bound where a function of the same name exists; calling it "
        "raises TypeError: 'module' object is not callable:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "call",
    [
        "ta.aberration(h, l, c)",
        "ta.zlma(c, mamode='sma')",
        "ta.ui(c, everget=True)",
    ],
)
def test_shadowed_call_sites_work_in_a_fresh_interpreter(call):
    """Each site that used to raise, exercised as an early call in its own process.

    The binding is decided once, at `import pandas_ta`, by module-level `from`
    statements -- no test can rebind it afterwards, so an in-process check would
    do.  The subprocess buys isolation from whatever this session already
    imported, and from an installed copy shadowing the repo one.
    """
    code = (
        "import numpy as np, pandas as pd, pandas_ta as ta\n"
        "c = pd.Series(np.linspace(100.0, 120.0, 150))\n"
        "h, l = c * 1.01, c * 0.99\n"
        f"out = {call}\n"
        "assert out is not None and out.notna().to_numpy().any()\n"
        "print(','.join(out.columns) if hasattr(out, 'columns') else out.name)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        cwd=str(pathlib.Path(__file__).resolve().parents[1]),
    )
    assert proc.returncode == 0, f"fresh-interpreter `{call}` failed:\n{proc.stderr}"
    assert proc.stdout.strip(), f"`{call}` produced no output"


def test_aberration_returns_its_four_columns_in_a_fresh_interpreter():
    """WIRING-2's acceptance criterion, to the column: four, named, in order."""
    code = (
        "import numpy as np, pandas as pd, pandas_ta as ta\n"
        "c = pd.Series(np.linspace(100.0, 120.0, 150))\n"
        "out = ta.aberration(c * 1.01, c * 0.99, c)\n"
        "print(','.join(out.columns))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        cwd=str(pathlib.Path(__file__).resolve().parents[1]),
    )
    assert proc.returncode == 0, f"fresh-interpreter aberration failed:\n{proc.stderr}"
    assert proc.stdout.strip().split(",") == [
        "ABER_ZG_5_15", "ABER_SG_5_15", "ABER_XG_5_15", "ABER_ATR_5_15",
    ], proc.stdout


def test_mcgd_concat_preserves_the_series_shape_and_first_value():
    """The pandas-2 `concat` fix, pinned on values rather than on a column name.

    `Series.append` was removed in pandas 2.0; the replacement had to keep the
    same shape, index and seeding (`close[:1]` followed by the rolled cells).
    A concat that mis-aligned the index would still produce an `MCGD_*` column.
    """
    df = _ohlcv(n=200)
    close = df["close"]
    out = pandas_ta.mcgd(close, length=10)

    assert len(out) == len(close)
    assert out.index.equals(close.index)
    assert out.isna().sum() == 0, "concat left NaNs the append form did not"
    assert out.iloc[0] == close.iloc[0], "series is not seeded with close[0]"
    pd.testing.assert_series_equal(
        _as_frame(df.ta.mcgd(length=10)).iloc[:, 0], out, check_names=False
    )


@pytest.mark.parametrize("name", ["squeeze", "squeeze_pro"])
@pytest.mark.parametrize("kwargs", [
    {}, {"offset": 1}, {"offset": 2, "detailed": True},
    {"offset": 1, "fillna": 0}, {"offset": 1, "asint": False},
    {"lazybear": True, "offset": 1},
])
def test_squeeze_survives_a_non_zero_offset(name, kwargs):
    """SQZOFF: the flag columns cast to int over a shifted, NaN-led series.

    `astype(int)` raised `ValueError: cannot convert float NaN to integer` for
    every non-zero `offset`, taking whole `df.ta.strategy("momentum", offset=n)`
    runs down with it. Upstream defect, invisible because `offset=0` is the
    default.
    """
    df = _ohlcv(n=300)
    result = getattr(df.ta, name)(**kwargs)
    assert result is not None and len(result) == len(df)

    # Not raising is the floor, not the bar: an all-NaN return or a silently
    # dropped offset would pass that alone.
    assert result.notna().to_numpy().any(), f"{name}({kwargs}) is entirely NaN"
    offset = kwargs.get("offset", 0)
    if offset and "fillna" not in kwargs:
        base = getattr(df.ta, name)(**{k: v for k, v in kwargs.items()
                                       if k != "offset"})
        pd.testing.assert_frame_equal(result, base.shift(offset),
                                      check_names=False)


@pytest.mark.parametrize("name", ["squeeze", "squeeze_pro"])
def test_squeeze_flags_stay_int_at_the_default_offset(name):
    """The NaN-safe cast must not silently change the default output's dtype."""
    df = _ohlcv(n=300)
    flags = [c for c in getattr(df.ta, name)().columns if "_ON" in c or "_OFF" in c or "_NO" in c]
    assert flags, f"{name} emitted no flag columns"
    dtypes = getattr(df.ta, name)()[flags].dtypes
    assert all(str(d).startswith("int") for d in dtypes), dict(dtypes.astype(str))
