#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compute a wide indicator panel with this fork, and check the columns it produces.

WHAT THIS IS
------------
A complete, tested reference for using this `pandas_ta` fork on one OHLCV frame. It computes
several hundred columns, then applies the three tests that decide whether a column is usable as a
machine-learning feature: **causal**, **scale-free**, **non-redundant**.

    python examples/market_dashboard.py                    # AAPL via yfinance, or synthetic
    python examples/market_dashboard.py --ticker MSFT
    python examples/market_dashboard.py --offline          # never touch the network
    python examples/market_dashboard.py --out panel.csv    # write the panel

Exit status is 0 only when every indicator call succeeded. A silent sweep is not a working sweep.

WHAT THIS IS NOT
----------------
There is no composite score, no threshold, no weighting scheme and no BULLISH/BEARISH verdict
anywhere in this file, by decision recorded in `docs/SHOWCASE_SCOPE.md`. This library computes
indicators; deciding what they mean is the caller's job, and a scoring layer here would teach the
opposite. `tests/test_showcase.py` pins that absence.

DATA IS NOT CLEANED
-------------------
The optional loader fetches from Yahoo Finance and hands the frame over untouched. No corporate
-action repair, no exchange-limit back-adjustment. If you point this at an exchange with a daily
price limit, unadjusted split cliffs will appear as impossible single-bar moves and will poison
every windowed indicator downstream of them. Cleaning belongs in your data layer, not in an
indicator library.

WHY THE SPEC TABLE LOOKS PARANOID
---------------------------------
It is derived from a real one that carried **16 argument lists that did not match the function
signature**. Each raised on every call and was swallowed by a bare `except: continue`, so those 16
indicators had never emitted a column and nothing in the output said so. Every one of the 16 is
present here with a corrected call, and `run_specs` reports failures instead of hiding them.

PROVENANCE
----------
Written 2026-09-12 against this fork, `github.com/TolgaUyanik/PandasTa`, at package version
`0.2.67b1+tu.1` (branch `dev`, commit `43d0685`). Run `--version` to print the version the
installed package actually reports; prefer that over the commit, which is local to the working
tree until it is pushed.

Scope of what this example may and may not contain: `docs/SHOWCASE_SCOPE.md`.
Pinned by: `tests/test_showcase.py` (offline, no network, no sibling repo).
"""
from __future__ import annotations

import argparse
import sys
import warnings
from typing import Callable, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

import pandas_ta as ta

warnings.filterwarnings("ignore")

# Column names emitted by more than one indicator with IDENTICAL values - benign, but the panel
# holds one column where a caller counting specs would expect two. Populated by `run_specs`.
_DUPLICATES: List[tuple] = []

O, H, L, C, V = "open", "high", "low", "close", "volume"
OHLCV = (O, H, L, C, V)


# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
def synthetic_ohlcv(n: int = 750, seed: int = 7) -> pd.DataFrame:
    """A geometric random walk with a coherent OHLC envelope. No network, deterministic."""
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * (1 + abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - abs(rng.normal(0, 0.006, n)))
    return pd.DataFrame(
        {O: open_, H: high, L: low, C: close,
         V: rng.integers(1e5, 1e6, n).astype(float)},
        index=pd.date_range("2022-01-01", periods=n, freq="B"),
    )


def load_yahoo(ticker: str = "AAPL", period: str = "3y") -> pd.DataFrame:
    """Optional loader. `yfinance` is an extra, imported here and nowhere else.

    Raises rather than falling back, so the caller decides. See `load()`.
    """
    import yfinance as yf                      # noqa: PLC0415 - deliberately local

    raw = yf.download(ticker, period=period, auto_adjust=True,
                      progress=False, multi_level_index=False)
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no rows for {ticker}")
    raw.columns = [str(c).lower() for c in raw.columns]
    frame = raw[list(OHLCV)].dropna()
    if len(frame) < 250:
        raise RuntimeError(f"only {len(frame)} bars for {ticker}; need >= 250")
    return frame


def load(ticker: str = "AAPL", period: str = "3y", offline: bool = False) -> Tuple[pd.DataFrame, str]:
    """Real data if it is available and wanted, synthetic otherwise. Always says which."""
    if offline:
        return synthetic_ohlcv(), "synthetic random walk (--offline)"
    try:
        return load_yahoo(ticker, period), f"{ticker} via yfinance"
    except Exception as exc:                    # noqa: BLE001 - reported, not swallowed
        return synthetic_ohlcv(), f"synthetic random walk (yfinance unavailable: {exc})"


# --------------------------------------------------------------------------------------
# The spec table
# --------------------------------------------------------------------------------------
# (name, [frame columns to pass positionally], {keyword arguments})
#
# The 16 that were broken in the source table are marked FIXED with the defect, so nobody
# "simplifies" them back. Every one of them raised on every call for the life of that file.
SPECS: List[Tuple[str, List[str], dict]] = [
    # --- volatility / range ------------------------------------------------------------
    ("aberration", [H, L, C], {}),                    # FIXED: was [close] -> missing low, close
    ("accbands", [H, L, C], {}),
    ("atr", [H, L, C], {"length": 14}),
    ("natr", [H, L, C], {"length": 14}),
    ("true_range", [H, L, C], {}),
    ("bbands", [C], {"length": 20, "std": 2}),
    ("kc", [H, L, C], {"length": 20}),                # FIXED: was [close] -> missing low, close
    ("donchian", [H, L], {}),
    ("hilo", [H, L, C], {"high_length": 14, "low_length": 14}),   # FIXED: was [high, low]
    ("massi", [H, L], {}),
    ("pdist", [O, H, L, C], {}),                      # FIXED: was [close] -> missing high, low, close
    ("rvi", [H, L, C], {}),
    ("thermo", [H, L, C], {}),                        # FIXED: was [close] -> missing low
    ("ui", [C], {}),
    ("stdev", [C], {"length": 20}),
    ("variance", [C], {}),
    ("chop", [H, L, C], {}),
    # --- momentum / oscillators --------------------------------------------------------
    ("rsi", [C], {"length": 14}),
    ("rsx", [C], {}),
    ("cci", [H, L, C], {"length": 20}),
    ("cmo", [C], {"length": 14}),
    ("roc", [C], {"length": 12}),
    ("mom", [C], {"length": 10}),
    ("stoch", [H, L, C], {"k": 14, "d": 3}),
    ("stochrsi", [C], {"length": 14}),
    ("kdj", [H, L, C], {}),
    ("willr", [H, L, C], {"length": 14}),
    ("uo", [H, L, C], {}),
    ("ao", [H, L], {}),
    ("apo", [C], {}),
    ("ppo", [C], {}),
    ("macd", [C], {}),
    ("tsi", [C], {}),
    ("smi", [C], {}),                                 # FIXED: raised ValueError in the source loop
    ("trix", [C], {"length": 14}),
    ("kst", [C], {}),
    ("coppock", [C], {}),
    ("fisher", [H, L], {}),
    ("er", [C], {}),
    ("cfo", [C], {}),
    ("cg", [C], {}),
    ("bop", [O, H, L, C], {}),
    ("brar", [O, H, L, C], {}),
    ("eri", [H, L, C], {}),
    ("inertia", [C], {}),
    ("pgo", [H, L, C], {}),                           # FIXED: was [close] -> missing low, close
    ("psl", [C], {}),
    ("qstick", [O, C], {}),
    ("rvgi", [O, H, L, C], {}),                       # FIXED: was [close] -> missing high, low, close
    ("squeeze", [H, L, C], {}),                       # FIXED: was [close] -> missing low, close
    ("ebsw", [C], {}),
    ("bias", [C], {}),
    ("imi", [O, C], {}),
    # --- trend ---------------------------------------------------------------------------
    ("adx", [H, L, C], {"length": 14}),
    ("amat", [C], {}),
    ("aroon", [H, L], {"length": 25}),
    ("cksp", [H, L, C], {}),
    ("dpo", [C], {"centered": False}),                # centered=True is a LOOK-AHEAD; see check_causality
    ("increasing", [C], {}),
    ("decreasing", [C], {}),
    ("ttm_trend", [H, L, C], {}),                     # FIXED: was [close] -> missing low, close
    ("vortex", [H, L, C], {"length": 14}),
    # --- overlap / moving averages --------------------------------------------------------
    ("sma", [C], {"length": 20}),
    ("ema", [C], {"length": 200}),
    ("dema", [C], {"length": 20}),
    ("tema", [C], {"length": 20}),
    ("trima", [C], {"length": 20}),
    ("wma", [C], {"length": 20}),
    ("hma", [C], {"length": 20}),
    ("alma", [C], {"length": 20}),
    ("fwma", [C], {"length": 14}),
    ("kama", [C], {"length": 14}),
    ("pwma", [C], {"length": 20}),
    ("sinwma", [C], {"length": 20}),
    ("swma", [C], {"length": 20}),
    ("t3", [C], {"length": 20}),
    ("vidya", [C], {"length": 14}),
    ("zlma", [C], {"length": 20}),
    ("mcgd", [C], {"length": 14}),
    ("hwma", [C], {}),
    ("hwc", [C], {}),
    ("rma", [C], {"length": 14}),
    ("wilder_rma", [C], {}),
    ("ssf", [C], {"length": 10}),
    ("linreg", [C], {"length": 14}),
    ("linreg_channel", [C], {}),
    ("midpoint", [C], {"length": 14}),
    ("midprice", [H, L], {"length": 14}),
    ("vwma", [C, V], {"length": 20}),
    ("hl2", [H, L], {}),
    ("hlc3", [H, L, C], {}),
    ("ohlc4", [O, H, L, C], {}),
    ("wcp", [H, L, C], {}),
    # --- volume ------------------------------------------------------------------------------
    ("ad", [H, L, C, V], {}),
    ("adosc", [H, L, C, V], {"fast": 3, "slow": 10}),
    ("aobv", [C, V], {}),
    ("cmf", [H, L, C, V], {}),
    ("efi", [C, V], {"length": 13}),
    ("eom", [H, L, C, V], {}),                        # FIXED: was [high, low, volume] -> missing close
    ("mfi", [H, L, C, V], {"length": 14}),
    ("bw_mfi", [H, L, C, V], {}),
    ("nvi", [C, V], {}),
    ("obv", [C, V], {}),
    ("pvi", [C, V], {}),
    ("pvo", [V], {}),
    ("pvol", [C, V], {}),                             # FIXED: was [volume] -> missing close
    ("pvr", [C, V], {}),                              # FIXED: was [volume] -> missing close
    ("pvt", [C, V], {}),
    ("vwap", [H, L, C, V], {}),
    ("cvi", [H, L], {}),
    # --- statistics / returns ------------------------------------------------------------------
    ("entropy", [C], {}),
    ("kurtosis", [C], {}),
    ("skew", [C], {}),
    ("mad", [C], {}),
    ("median", [C], {}),
    ("quantile", [C], {"length": 20}),
    ("zscore", [C], {}),
    ("slope", [C], {"length": 14}),
    ("log_return", [C], {}),
    ("percent_return", [C], {}),
    ("decay", [C], {}),
    ("drawdown", [C], {}),
    # --- candles / structure --------------------------------------------------------------------
    ("cdl_doji", [O, H, L, C], {}),
    ("cdl_inside", [O, H, L, C], {}),
    ("ha", [O, H, L, C], {}),
]

# Three of the sixteen take a DERIVED series, not a frame column, which is why a table keyed on
# column names could never have called them correctly. They are built explicitly.
#
#   long_run(fast, slow)      - two series, e.g. a fast and a slow average
#   short_run(fast, slow)     - likewise
#   trend_return(close, trend) - a price series and a BOOLEAN trend mask
DERIVED_SPECS: Dict[str, Callable[[pd.DataFrame], object]] = {
    "long_run": lambda d: ta.long_run(ta.sma(d[C], 10), ta.sma(d[C], 50)),
    "short_run": lambda d: ta.short_run(ta.sma(d[C], 10), ta.sma(d[C], 50)),
    "trend_return": lambda d: ta.trend_return(d[C], ta.sma(d[C], 50) < d[C]),
}

# Indicators this fork adds that upstream pandas-ta does not have. Kept separate from SPECS so
# `--fork-only` can report on them, and so the coverage number can distinguish the two.
FORK_SPECS: Dict[str, Callable[[pd.DataFrame], object]] = {
    # TradingView built-ins
    "pzo": lambda d: ta.pzo(d[C]),
    "szo": lambda d: ta.szo(d[C]),
    "vzo": lambda d: ta.vzo(d[C], d[V]),
    "wpo": lambda d: ta.wpo(d[H], d[C]),
    "frama": lambda d: ta.frama(d[H], d[L], d[C]),
    "stc_tv": lambda d: ta.stc_tv(d[C]),
    "vstop": lambda d: ta.vstop(d[H], d[L], d[C]),
    "vstop2": lambda d: ta.vstop2(d[H], d[L], d[C]),
    # TA-Lib gaps - the Hilbert family is ONE state machine with two warm-ups (12 and 37 bars),
    # not seven algorithms. All seven read-outs are exercised.
    "ht": lambda d: ta.ht(d[C]),
    "ht_dcperiod": lambda d: ta.ht_dcperiod(d[C]),
    "ht_dcphase": lambda d: ta.ht_dcphase(d[C]),
    "ht_phasor": lambda d: ta.ht_phasor(d[C]),
    "ht_sine": lambda d: ta.ht_sine(d[C]),
    "ht_trendline": lambda d: ta.ht_trendline(d[C]),
    "ht_trendmode": lambda d: ta.ht_trendmode(d[C]),
    "mama": lambda d: ta.mama(d[C]),
    "sarext": lambda d: ta.sarext(d[H], d[L], d[C]),
    # chart patterns
    "head_shoulders": lambda d: ta.head_shoulders(d[H], d[L], d[C]),
    "triple_top_bottom": lambda d: ta.triple_top_bottom(d[H], d[L], d[C]),
    "triangle_wedge": lambda d: ta.triangle_wedge(d[H], d[L], d[C]),
    "rounding_cup": lambda d: ta.rounding_cup(d[C]),
    # price structure / SMC
    "bos": lambda d: ta.bos(d[H], d[L], d[C]),
    "choch": lambda d: ta.choch(d[H], d[L], d[C]),
    "fvg": lambda d: ta.fvg(d[H], d[L], d[C]),
    "ob": lambda d: ta.ob(d[O], d[H], d[L], d[C]),
    "smc_sweep": lambda d: ta.smc_sweep(d[O], d[H], d[L], d[C]),
    "halftrend": lambda d: ta.halftrend(d[H], d[L], d[C]),
    "wavetrend": lambda d: ta.wavetrend(d[H], d[L], d[C]),
    "zigzag": lambda d: ta.zigzag(d[C]),
    # the reference scale-free conversion: 5 price lines -> 8 causal, scale-free columns
    "ichimoku_ml": lambda d: ta.ichimoku_ml(d[H], d[L], d[C]),
    # the rest of the fork's SMC / ICT / structure work. "the SMC ports" is a FAMILY;
    # shipping five of it and calling the family done is how a demo drifts back to upstream.
    "inverse_fvg": lambda d: ta.inverse_fvg(d[H], d[L], d[C]),
    "nwog": lambda d: ta.nwog(d[O], d[C]),
    "liquidity_sweep": lambda d: ta.liquidity_sweep(d[H], d[L], d[C]),
    "liquidity_compression_box": lambda d: ta.liquidity_compression_box(d[H], d[L], d[C], d[O]),
    "rejection_blocks": lambda d: ta.rejection_blocks(d[O], d[H], d[L], d[C]),
    "equal_highs_lows": lambda d: ta.equal_highs_lows(d[H], d[L], d[C]),
    "sd_zone_pro": lambda d: ta.sd_zone_pro(d[H], d[L], d[C], d[V]),
    "sphinx_unicorn": lambda d: ta.sphinx_unicorn(d[H], d[L], d[C]),
    "swing_equilibrium": lambda d: ta.swing_equilibrium(d[H], d[L], d[C]),
    "fvg_sweep_magnet": lambda d: ta.fvg_sweep_magnet(d[O], d[H], d[L], d[C], d[V]),
    "zigzag_fib": lambda d: ta.zigzag_fib(d[H], d[L], d[C]),
    # support / resistance family
    "sr_corridor": lambda d: ta.sr_corridor(d[H], d[L], d[C]),
    "sr_decay": lambda d: ta.sr_decay(d[H], d[L], d[C]),
    "sr_force": lambda d: ta.sr_force(d[H], d[L], d[C]),
    "volume_sr_zones": lambda d: ta.volume_sr_zones(d[H], d[L], d[C], d[V]),
    "band_cross_retest": lambda d: ta.band_cross_retest(d[H], d[L], d[C]),
    # other fork originals
    "tvstop": lambda d: ta.tvstop(d[H], d[L], d[C]),
    "flag_breakout": lambda d: ta.flag_breakout(d[H], d[L], d[C]),
    "range_profile": lambda d: ta.range_profile(d[H], d[L], d[C]),
    "dtdb": lambda d: ta.dtdb(d[H], d[L], d[C]),
    "cdl_z": lambda d: ta.cdl_z(d[O], d[H], d[L], d[C]),
    "avwap_z": lambda d: ta.avwap_z(d[H], d[L], d[C], d[V]),
    "pocket_pivot": lambda d: ta.pocket_pivot(d[C], d[O], d[H], d[L], d[V]),
    "ema_align": lambda d: ta.ema_align(d[C]),
    "vol_delta": lambda d: ta.vol_delta(d[O], d[H], d[L], d[C], d[V]),
    # PINEBI-1c alternates: TradingView's arithmetic differs from upstream's for the same name,
    # so both ship. Seven were measured and kept; two were deleted.
    "ema2": lambda d: ta.ema2(d[C]),
    "rma2": lambda d: ta.rma2(d[C]),
    "dema2": lambda d: ta.dema2(d[C]),
    "tema2": lambda d: ta.tema2(d[C]),
    "t3_tv": lambda d: ta.t3_tv(d[C]),
    "atr2": lambda d: ta.atr2(d[H], d[L], d[C]),
    "supertrend2": lambda d: ta.supertrend2(d[H], d[L], d[C]),
}

# An omission with a written reason is a decision; an omission with no reason is an oversight.
# Everything registered in `Category` and NOT exercised must appear here, and section [6]
# prints anything that does not.
NOT_EXERCISED_BY_DESIGN = {
    "beta": "needs a benchmark series; out of Category and in strategy's exclusion list",
    "up_and_down_volume": "needs a lower-timeframe frame a single-frame demo cannot synthesise",
    "volume_delta": "same lower-timeframe requirement",
}

# The five MLCOL-1 ML-companion columns. Each is a scale-free companion emitted alongside a parent
# whose own output is a price level. Named here so a reader can find them in the panel, and so the
# test can assert they are actually reachable rather than merely intended.
#
# `HW-MID_DIST_PCT` is DELIBERATELY absent: it reads rho +0.9257 / +0.9213 against the two edges,
# so shipping all three would be one signal wearing three names.
ML_COMPANION_COLUMNS = (
    "HA_high_DIST_PCT",             # from ha
    "HW-UPPER_DIST_PCT",            # from hwc
    "HW-LOWER_DIST_PCT",            # from hwc
    "LINREG_LOWER_2_DIST_PCT",      # from linreg_channel
    "THERMO_20_2_0.5_RATIO_PCT",    # from thermo - a RATIO, not a distance: thermo is a
                                    # difference parent, so (close - parent)/close would sit at
                                    # ~1.0 with the signal in the fourth decimal.
)


# --------------------------------------------------------------------------------------
# Computation
# --------------------------------------------------------------------------------------
def _collect(out: Dict[str, pd.Series], result, fallback: str,
             seen: Dict[str, tuple] = None, collisions: List = None) -> List[str]:
    """Flatten a Series / DataFrame / tuple into `out`. Return the column names written.

    Returning the NAMES rather than None is deliberate, for two reasons. An indicator that
    returns a scalar, a list or a numpy array matches no branch, writes nothing, and would
    otherwise be reported as a success - the original defect wearing a different hat. And two
    indicators can emit the SAME column name, in which case the second silently replaces the
    first and the panel is one column short of what the caller thinks it has.
    """
    written = []
    if isinstance(result, pd.Series):
        key = result.name or fallback
        out[key] = result
        written.append(key)
    elif isinstance(result, pd.DataFrame):
        for col in result.columns:
            out[col] = result[col]
            written.append(col)
    elif isinstance(result, tuple):
        # ichimoku returns (history, forward projection). The forward frame is dated PAST the
        # last bar - it is the cloud projection, and concatenating it into a feature frame is a
        # look-ahead leak. Only the history half is taken.
        written.extend(_collect(out, result[0], fallback, seen, collisions))
    else:
        raise TypeError(f"unhandled result type {type(result).__name__}")
    if seen is not None:
        for key in written:
            prior_owner, prior_values = seen.get(key, (None, None))
            if prior_owner is not None and prior_owner != fallback:
                same = prior_values.equals(out[key])
                collisions.append((key, prior_owner, fallback, same))
            else:
                seen[key] = (fallback, out[key].copy())
    return written


def run_specs(frame: pd.DataFrame,
              specs: Sequence[Tuple[str, List[str], dict]] = SPECS,
              derived: Dict[str, Callable] = None,
              ) -> Tuple[pd.DataFrame, List[Tuple[str, str]]]:
    """Compute every spec. Return (panel, failures).

    Failures are RETURNED, never swallowed. The source this is derived from used
    `except: continue`, which is how 16 broken specs survived undetected.
    """
    derived = DERIVED_SPECS if derived is None else derived
    out: Dict[str, pd.Series] = {}
    failures: List[Tuple[str, str]] = []
    seen: Dict[str, tuple] = {}
    collisions: List[tuple] = []

    for name, args, kwargs in specs:
        fn = getattr(ta, name, None)
        if fn is None:
            failures.append((name, "not present in this pandas_ta build"))
            continue
        missing = [a for a in args if a not in frame.columns]
        if missing:
            failures.append((name, f"frame lacks {missing}"))
            continue
        try:
            result = fn(*[frame[a] for a in args], **kwargs)
        except Exception as exc:                # noqa: BLE001 - recorded and reported
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            continue
        if result is None:
            failures.append((name, "returned None"))
            continue
        try:
            written = _collect(out, result, name, seen, collisions)
        except TypeError as exc:
            failures.append((name, str(exc)))
            continue
        if not written:
            failures.append((name, "returned a result but contributed no column"))

    for name, builder in derived.items():
        try:
            result = builder(frame)
        except Exception as exc:                # noqa: BLE001
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            continue
        if result is None:
            failures.append((name, "returned None"))
            continue
        try:
            written = _collect(out, result, name, seen, collisions)
        except TypeError as exc:
            failures.append((name, str(exc)))
            continue
        if not written:
            failures.append((name, "returned a result but contributed no column"))

    for key, first, second, same in collisions:
        if not same:
            # Two indicators writing DIFFERENT values to one column name. The second wins and
            # the first is gone, with nothing in the output to say so.
            failures.append((second, f"emits column {key!r} with values that DIFFER from "
                                     f"{first!r}'s; one is silently lost from the panel"))
    _DUPLICATES.extend((k, a, b) for k, a, b, same in collisions if same)
    return pd.DataFrame(out, index=frame.index), failures


def run_fork_specs(frame: pd.DataFrame,
                   specs: Dict[str, Callable] = None,
                   ) -> Tuple[pd.DataFrame, List[Tuple[str, str]]]:
    """Same contract, for the indicators this fork adds."""
    specs = FORK_SPECS if specs is None else specs
    out: Dict[str, pd.Series] = {}
    failures: List[Tuple[str, str]] = []
    seen: Dict[str, tuple] = {}
    collisions: List[tuple] = []
    for name, builder in specs.items():
        try:
            result = builder(frame)
        except Exception as exc:                # noqa: BLE001
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            continue
        if result is None:
            failures.append((name, "returned None"))
            continue
        try:
            written = _collect(out, result, name, seen, collisions)
        except TypeError as exc:
            failures.append((name, str(exc)))
            continue
        if not written:
            failures.append((name, "returned a result but contributed no column"))
    for key, first, second, same in collisions:
        if not same:
            # Two indicators writing DIFFERENT values to one column name. The second wins and
            # the first is gone, with nothing in the output to say so.
            failures.append((second, f"emits column {key!r} with values that DIFFER from "
                                     f"{first!r}'s; one is silently lost from the panel"))
    _DUPLICATES.extend((k, a, b) for k, a, b, same in collisions if same)
    return pd.DataFrame(out, index=frame.index), failures


# The indicators `consolidate_multi_output` calls. Declared once so `exercised_names()` cannot
# drift from what the function actually does; `tests/test_showcase.py` spies on each to prove it.
CONSOLIDATED_SOURCES = ("psar", "supertrend", "qqe", "td_seq", "ichimoku")


def consolidate_multi_output(frame: pd.DataFrame) -> pd.DataFrame:
    """Indicators returning a long branch and a short branch, merged to level + direction."""
    out = pd.DataFrame(index=frame.index)

    psar = ta.psar(frame[H], frame[L], frame[C])
    psar_l = psar.filter(like="PSARl").iloc[:, 0]
    psar_s = psar.filter(like="PSARs").iloc[:, 0]
    out["PSAR"] = psar_l.combine_first(psar_s)
    out["PSAR_DIR"] = np.where(psar_l.notna(), 1, np.where(psar_s.notna(), -1, 0))

    st = ta.supertrend(frame[H], frame[L], frame[C], length=10, multiplier=3)
    out["SUPERT_DIR"] = st["SUPERTd_10_3.0"]

    qqe = ta.qqe(frame[C])
    out["QQE"] = qqe.filter(regex=r"^QQE_\d").iloc[:, 0]
    out["QQE_DIR"] = np.where(qqe.filter(like="QQEl").iloc[:, 0].notna(), 1,
                       np.where(qqe.filter(like="QQEs").iloc[:, 0].notna(), -1, 0))

    td = ta.td_seq(frame[C], show_all=True)
    out["TD_SEQ"] = td["TD_SEQ_UPa"].combine_first(-td["TD_SEQ_DNa"])

    ichi_hist, _ichi_forward = ta.ichimoku(frame[H], frame[L], frame[C])
    out["TENKAN"] = ichi_hist["ITS_9"]
    out["KIJUN"] = ichi_hist["IKS_26"]
    return out


# --------------------------------------------------------------------------------------
# The three feature-contract checks
# --------------------------------------------------------------------------------------
# Columns whose value at bar T legitimately depends on bars after T. Each is a DESIGN choice,
# each is bounded, and each is listed here so that anything NOT on this list failing the probe is
# an unknown leak. `tests/test_showcase.py` asserts exactly this set - no more, no less.
#
#   ICS_26            ichimoku's Chikou span: close.shift(-kijun), 26 bars.
#   DPO_*             dpo at centered=True, which is its DEFAULT. length//2 + 1 bars.
#   BOS_*, HIGHER_HIGH, LOWER_LOW
#                     bos detects swings with rolling(swing_length, center=True), so a pivot is
#                     confirmed up to (swing_length - 1) // 2 bars after it forms and is written
#                     back to the pivot bar. That is the ANALYTIC bound from the window
#                     geometry. Measured reach on a 500-bar synthetic frame across 20
#                     perturbation cuts (range(200, 460, 13)): 2 bars at swing_length=5, 2 at 7,
#                     4 at 9 - at or under the bound, never over, and not always at it, because
#                     a sweep only sees the pivots it happens to straddle. Treat the bound as
#                     the number to design against. `choch`, `zigzag` and `halftrend` were
#                     probed the same way and are clean.
#
# NOTE this list was described as "complete" at two entries until 2026-09-11, when `ssf` turned
# out to be a third - and that one was a BUG, not a design choice. Treat the list as the record
# of what has been measured, never as a substitute for measuring.
KNOWN_LOOKAHEAD = {
    ("ichimoku", "ICS_26"): "Chikou span, close.shift(-26), by design",
    ("dpo(centered=True)", "DPO_20"): "dpo's DEFAULT; reaches ~length//2 + 1 bars",
    ("bos", "BOS_BULL"): "centered swing window",
    ("bos", "BOS_BEAR"): "centered swing window",
    ("bos", "HIGHER_HIGH"): "centered swing window",
    ("bos", "LOWER_LOW"): "centered swing window",
}


def check_causality(frame: pd.DataFrame, builders: Dict[str, Callable],
                    cut: int = None) -> pd.DataFrame:
    """Perturb the tail; any earlier bar that moves means the indicator read the future.

    This probe is not decoration. It is how a genuine look-ahead was found in `ssf`: its
    recursion started at index 0, so `ssf.iloc[i - 1]` evaluated `ssf.iloc[-1]` - the LAST bar of
    the series - and propagated that forward. Perturbing only bars >= 300 of a 400-bar frame
    moved bar 0 by 31.4.
    """
    cut = cut or int(len(frame) * 0.6)
    bumped = frame.copy()
    for col in (O, H, L, C):
        bumped.iloc[cut:, bumped.columns.get_loc(col)] *= 1.4

    rows = []
    for label, builder in builders.items():
        try:
            a, b = builder(frame), builder(bumped)
        except Exception as exc:                # noqa: BLE001
            rows.append({"probe": label, "column": label, "max prefix drift": np.nan,
                         "verdict": f"ERROR: {type(exc).__name__}: {exc}"})
            continue
        a = a.to_frame() if isinstance(a, pd.Series) else a
        b = b.to_frame() if isinstance(b, pd.Series) else b
        for col in a.columns:
            if col not in b:
                continue
            x = np.asarray(a[col], dtype=float)[:cut]
            y = np.asarray(b[col], dtype=float)[:cut]
            m = np.isfinite(x) & np.isfinite(y)
            if not m.any():
                continue
            drift = float(np.abs(x[m] - y[m]).max())
            if drift == 0.0:
                verdict = "causal"
            elif (label, col) in KNOWN_LOOKAHEAD:
                verdict = "known exception"
            else:
                verdict = "UNKNOWN LEAK"
            rows.append({"probe": label, "column": col,
                         "max prefix drift": drift, "verdict": verdict})
    return pd.DataFrame(rows).sort_values("max prefix drift", ascending=False)


def check_scale_free(frame: pd.DataFrame, columns_fn: Callable,
                     k: float = 8.0, tol: float = 1e-9) -> pd.DataFrame:
    """Multiply every price by k; a feature is unmoved, a level is not.

    TWO verdicts, deliberately. `bit_identical` is the strict test. `scale_free` allows a
    floating-point tolerance, because a log return is scale-invariant in algebra yet
    log(k*a) - log(k*b) can differ from log(a) - log(b) in the final bit. Calling that a failure
    would be wrong.
    """
    scaled = frame.copy()
    for col in (O, H, L, C):
        scaled[col] *= k
    a, b = columns_fn(frame), columns_fn(scaled)
    rows = []
    for col in a.columns:
        if col not in b:
            continue
        x, y = np.asarray(a[col], float), np.asarray(b[col], float)
        m = np.isfinite(x) & np.isfinite(y)
        if not m.any():
            continue
        drift = float(np.abs(x[m] - y[m]).max())
        scale = max(float(np.abs(x[m]).max()), 1e-12)
        rows.append({"column": col, "max drift": drift,
                     "bit_identical": drift == 0.0,
                     "scale_free": drift / scale < tol})
    return pd.DataFrame(rows)


def check_redundancy(panel: pd.DataFrame, threshold: float = 0.99,
                     min_obs: int = 100) -> pd.Series:
    """Spearman rank correlation across the panel. Near 1.0 means one signal, two names.

    In this fork the rule has teeth: a candidate measured at rho ~ 0.90 against anything already
    shipped is REVERTED rather than added. Columns have been built, measured and deleted on
    exactly this test.
    """
    num = panel.select_dtypes("number")
    num = num.loc[:, num.notna().sum() > min_obs]
    corr = num.corr(method="spearman").abs()
    np.fill_diagonal(corr.values, np.nan)
    upper = corr.where(np.triu(np.ones(corr.shape), 1).astype(bool))
    return upper.stack().sort_values(ascending=False)


# --------------------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------------------
def registered_names() -> set:
    """Every indicator name `df.ta.strategy()` would sweep, read from the live package."""
    names = set()
    for group in ta.Category.values():
        names.update(group)
    return names


def exercised_names() -> set:
    """Every indicator this example calls, derived from the tables rather than retyped."""
    names = {name for name, _, _ in SPECS}
    names |= set(DERIVED_SPECS) | set(FORK_SPECS)
    names |= set(CONSOLIDATED_SOURCES)
    return names


def coverage() -> Dict[str, object]:
    """Computed, never written down. A typed-in count is a count that goes stale."""
    registered = registered_names()
    used = exercised_names()
    return {
        "registered": len(registered),
        "exercised": len(used & registered),
        "fraction": len(used & registered) / len(registered),
        "not_exercised": sorted(registered - used),
        "called_but_unregistered": sorted(used - registered),
    }


# --------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------
def build(frame: pd.DataFrame) -> Dict[str, object]:
    """Compute everything once and return the pieces. Pure; no printing, no I/O."""
    panel, panel_failures = run_specs(frame)
    fork, fork_failures = run_fork_specs(frame)
    signals = consolidate_multi_output(frame)
    return {
        "panel": panel, "fork": fork, "signals": signals,
        "failures": panel_failures + fork_failures,
        "columns": panel.shape[1] + fork.shape[1] + signals.shape[1],
    }


def report(frame: pd.DataFrame, source: str, built: Dict[str, object] = None) -> int:
    """Print the dashboard. Return a process exit status: 0 only if nothing failed."""
    built = built or build(frame)
    panel, fork, signals = built["panel"], built["fork"], built["signals"]
    failures = built["failures"]

    print("=" * 78)
    print(f"pandas_ta {ta.version}   |   {source}   |   {len(frame)} bars")
    print("=" * 78)

    print("\n[1] INDICATOR SWEEP")
    print(f"    core specs      : {len(SPECS)} + {len(DERIVED_SPECS)} derived-input")
    print(f"    fork indicators : {len(FORK_SPECS)}")
    print(f"    columns         : {panel.shape[1]} core + {fork.shape[1]} fork "
          f"+ {signals.shape[1]} consolidated = {built['columns']}")
    print(f"    FAILURES        : {len(failures)}")
    for name, why in failures:
        print(f"        {name}: {why}")
    if not failures:
        print("    every call succeeded - the assertion a bare `except: continue` cannot make")
    if _DUPLICATES:
        print(f"    duplicate column names (identical values, benign): {len(_DUPLICATES)}")
        for key, first, second in _DUPLICATES:
            print(f"        {key!r}: emitted by both {first!r} and {second!r}")

    print("\n[2] ML COMPANION COLUMNS (MLCOL-1)")
    everything = pd.concat([panel, fork], axis=1)
    for col in ML_COMPANION_COLUMNS:
        present = col in everything.columns
        print(f"    {'present' if present else 'MISSING':8s} {col}")
        if not present:
            failures.append((col, "ML companion column absent from the panel"))
    print(f"    absent by design: HW-MID_DIST_PCT (rho +0.9257 / +0.9213 vs the two edges kept)")

    print("\n[3] CAUSALITY - does any column read the future?")
    causal = check_causality(frame, {
        "ssf": lambda d: ta.ssf(d[C], length=10),
        "rsi": lambda d: ta.rsi(d[C], length=14),
        "frama": lambda d: ta.frama(d[H], d[L], d[C]),
        "ichimoku_ml": lambda d: ta.ichimoku_ml(d[H], d[L], d[C]),
        "bos": lambda d: ta.bos(d[H], d[L], d[C]),
        "ichimoku": lambda d: ta.ichimoku(d[H], d[L], d[C])[0],
        "dpo(centered=True)": lambda d: ta.dpo(d[C]),
        "dpo(centered=False)": lambda d: ta.dpo(d[C], centered=False),
    })
    known = causal[causal["verdict"] == "known exception"]
    unknown = causal[causal["verdict"] == "UNKNOWN LEAK"]
    errored = causal[causal["verdict"].str.startswith("ERROR")]
    print(f"    columns probed  : {len(causal)}")
    print(f"    clean           : {int((causal['verdict'] == 'causal').sum())}")
    print(f"    known exception : {len(known)}")
    for _, row in known.iterrows():
        print(f"        {row['column']:12s} drift {row['max prefix drift']:>9.4f}  "
              f"- {KNOWN_LOOKAHEAD[(row['probe'], row['column'])]}")
    print(f"    UNKNOWN LEAKS   : {len(unknown)}"
          f"{'  <-- investigate before using these' if len(unknown) else ''}")
    for _, row in unknown.iterrows():
        print(f"        {row['column']:12s} drift {row['max prefix drift']:.4f}")
    print(f"    PROBE ERRORS    : {len(errored)}")
    for _, row in errored.iterrows():
        print(f"        {row['probe']}: {row['verdict']}")
    # A probe that could not run, or a leak nobody has accounted for, is a failed run.
    failures.extend((r["probe"], r["verdict"]) for _, r in errored.iterrows())
    failures.extend((r["column"], f"unknown look-ahead, drift {r['max prefix drift']:.4f}")
                    for _, r in unknown.iterrows())
    print("    NOTE `dpo` ships centered=True as its DEFAULT and `bos` uses a centered swing")
    print("         window; both are in Category, so a blind df.ta.strategy() sweep hands you")
    print("         look-ahead columns and says nothing. Pass dpo(centered=False); for bos,")
    print("         a pivot is not final until (swing_length-1)//2 bars after it forms, so do")
    print("         not read the last few bars of those columns as settled.")

    print("\n[4] SCALE-FREE - does the column survive multiplying price by 8?")
    scaled = check_scale_free(frame, lambda f: run_specs(f)[0])
    free, strict, tot = int(scaled["scale_free"].sum()), int(scaled["bit_identical"].sum()), len(scaled)
    print(f"    core panel  : {free}/{tot} scale-free ({free / tot:.1%}), {strict} bit-identical")
    fork_scaled = check_scale_free(frame, lambda f: run_fork_specs(f)[0])
    ffree, ftot = int(fork_scaled["scale_free"].sum()), len(fork_scaled)
    print(f"    fork columns: {ffree}/{ftot} scale-free ({ffree / ftot:.1%})")
    print("    A price-scaled column is not a defect - it is a level. It is just not a feature.")

    print("\n[5] REDUNDANCY - is this column already in the set under another name?")
    pairs = check_redundancy(panel)
    print(f"    pairs at |rho| >= 0.99 : {int((pairs >= 0.99).sum())}")
    print(f"    pairs at |rho| >= 0.90 : {int((pairs >= 0.90).sum())}")
    print("    most redundant:")
    for (a, b), rho in pairs.head(5).items():
        print(f"        {rho:.4f}  {a} <-> {b}")

    print("\n[6] COVERAGE - computed from the live package, not retyped")
    cov = coverage()
    print(f"    registered in Category : {cov['registered']}")
    print(f"    exercised here         : {cov['exercised']} ({cov['fraction']:.0%})")
    print(f"    not exercised          : {len(cov['not_exercised'])}")
    undeclared = [n for n in cov["not_exercised"] if n not in NOT_EXERCISED_BY_DESIGN]
    print("    Out of Category ON PURPOSE, so a sweep cannot call them at all "
          "(not part of the count above):")
    for name, why in NOT_EXERCISED_BY_DESIGN.items():
        print(f"        {name} - {why}")
    if undeclared:
        print(f"    unexercised with NO stated reason ({len(undeclared)}): "
              f"{', '.join(undeclared[:12])}{' ...' if len(undeclared) > 12 else ''}")
        print("    An omission with a written reason is a decision. This list is the oversights.")

    print("\n" + "=" * 78)
    print("No score, no threshold, no verdict. This is what the library computes;")
    print("what it means is your decision. See docs/SHOWCASE_SCOPE.md.")
    print("=" * 78)
    return 1 if failures else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ticker", default="AAPL", help="symbol to fetch (default: AAPL)")
    p.add_argument("--period", default="3y", help="yfinance period (default: 3y)")
    p.add_argument("--offline", action="store_true",
                   help="never touch the network; use the synthetic frame")
    p.add_argument("--out", metavar="PATH", default=None,
                   help="write the full computed panel to this CSV path")
    p.add_argument("--version", action="store_true", help="print versions and exit")
    args = p.parse_args(argv)

    if args.version:
        print(f"pandas_ta {ta.version} (fork: github.com/TolgaUyanik/PandasTa)")
        print(f"pandas {pd.__version__} / numpy {np.__version__}")
        return 0

    frame, source = load(args.ticker, args.period, args.offline)
    built = build(frame)
    status = report(frame, source, built)

    if args.out:
        full = pd.concat([built["panel"], built["fork"], built["signals"]], axis=1)
        full.to_csv(args.out)
        print(f"\nwrote {full.shape[0]} rows x {full.shape[1]} columns to {args.out}")
    return status


if __name__ == "__main__":
    sys.exit(main())
