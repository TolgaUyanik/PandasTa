# -*- coding: utf-8 -*-
"""TTIND-0/-1: classify every indicator `trading-technical-indicators` ships.

tti is the most structurally different of the three siblings: one CLASS per
file, each subclassing `TechnicalIndicator`, computed by construction
(`Cls(input_data=df)`) and read back with `getTiData()`. It also names its
modules `_average_true_range.py` where this fork says `atr`.

⚠ That naming is why the task's "57 of 58 absent" preview is worthless: almost
nothing matches by string while most of it is already shipped. TTIND-0 asked for
a spelled-out identity map before diffing. **This resolves identity by
MEASUREMENT instead** -- every tti indicator is computed on the shared probe
frame and searched against every callable fork indicator for a numerical match.
A name map is a hypothesis; an output match is evidence. The curated map below
exists only to propose a candidate for rows the search does not resolve.

Reuses the PTCLASSIC harness (probe frame, output comparison, and the constant/
identity degeneracy guards) rather than reimplementing it -- a second copy would
drift from the one whose verdicts are already committed.

⚠ tti reads its own version through `importlib.metadata` and raises when the
package is not installed. It is NOT installed here, and installing a sibling
repo into the environment is out of scope, so `version()` is stubbed for the
name `tti` only, in-process, before the import. Nothing else is patched.

⚠ Verified 2026-09-07: tti registers NO pandas accessor, so it does not collide
with `df.ta` the way `pandas_ta_classic` does. This script is still invoked as a
subprocess by its guard, per the standing rule.

⚠ Licence: tti is MIT. Attribution required on any port; the repo must not be
committed into this one.

Usage:  python docs/gen_altrepo_tti.py [out.csv]
"""
import csv
import importlib.metadata as _md
import inspect
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
TTI = os.path.join(SIBLING, "trading-technical-indicators")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    SIBLING, "altrepo_tti.csv")

if not os.path.isdir(TTI):
    sys.exit(f"trading-technical-indicators not found at {TTI}")

# Stub BEFORE the import, for the name `tti` only.
_real_version = _md.version
_md.version = lambda name: ("0.0.0-local" if name == "tti"
                            else _real_version(name))

sys.path.insert(0, TTI)
sys.path.insert(0, FORK)
sys.path.insert(0, HERE)

import numpy as np                                          # noqa: E402
import pandas_ta as ta                                      # noqa: E402
import tti.indicators as tti_ind                            # noqa: E402
from _altrepo_resolve import (
    fork_surface_cache,                              # noqa: E402
    PINNED_LENGTH, call_fork, probe_variants,
)
from gen_altrepo_pandas_ta_classic import (                 # noqa: E402
    SURFACE, NOT_CALLABLE, _call, _def_line, _probe_frame, _rel, _same_output,
    _source_file,
)


# tti rounds every output to 4 decimals before returning it
# (`_typical_price.py:82` `return tp.round(4)`; `_average_true_range.py:88`
# `.round(4)`), so a 1e-9 comparison rejects EVERY genuine match: tti's
# `TypicalPrice` and the fork's `hlc3` are the same formula and differ by
# 4.999e-05. The first run of this scanner found 0 `have` across 57 x 231
# comparisons for exactly that reason.
#
# So both sides are rounded to tti's own precision before comparing. That is
# WEAKER evidence than the bit-level agreement used for pandas-ta-classic, and
# every row it produces says so -- a 4-decimal match cannot distinguish two
# formulas that agree to 4 decimals and diverge in the fifth.
TTI_DECIMALS = 4


def _round_like_tti(value):
    """Round to tti's precision. Recurses -- a silently unrounded side
    reintroduces the 1e-9 comparison this exists to prevent, which is what
    happened to `ichimoku` (a tuple return went in at full precision)."""
    if value is None or value is NOT_CALLABLE:
        return value
    if isinstance(value, tuple):
        return tuple(_round_like_tti(v) for v in value)
    if isinstance(value, list):
        return [_round_like_tti(v) for v in value]
    if isinstance(value, (int, float, np.integer, np.floating)):
        return value          # a scalar is already exact at any precision
    if hasattr(value, "round"):
        return value.round(TTI_DECIMALS)
    raise TypeError(
        f"_round_like_tti cannot round {type(value).__name__}; refusing to "
        f"compare an unrounded side against tti's 4-decimal output")

# Proposed identities for rows the behavioural search does not resolve. A
# CANDIDATE, never a verdict: each is still confirmed or refuted by output.
CANDIDATE = {
    # Confirmed by reading tti's module docstring against the fork's function.
    # Every entry is still confirmed or refuted by OUTPUT; a name here only
    # decides which fork function gets tried.
    "AccumulationDistributionLine": "ad",
    "AverageTrueRange": "atr",
    "BollingerBands": "bbands",
    "ChaikinMoneyFlow": "cmf",
    "ChaikinOscillator": "adosc",
    "ChandeMomentumOscillator": "cmo",
    "CommodityChannelIndex": "cci",
    "DetrendedPriceOscillator": "dpo",
    "DirectionalMovementIndex": "adx",
    "DoubleExponentialMovingAverage": "dema",
    "EaseOfMovement": "eom",
    "FibonacciRetracement": "fibonacci",
    "ForecastOscillator": "cfo",
    "IchimokuCloud": "ichimoku",
    "KlingerOscillator": "kvo",
    "LinearRegressionIndicator": "linreg",
    "LinearRegressionSlope": "slope",
    "MassIndex": "massi",
    "Momentum": "mom",
    "MovingAverage": "sma",
    "MovingAverageConvergenceDivergence": "macd",
    "NegativeVolumeIndex": "nvi",
    "OnBalanceVolume": "obv",
    "ParabolicSAR": "psar",
    "PositiveVolumeIndex": "pvi",
    "PriceAndVolumeTrend": "pvt",
    "PriceChannel": "donchian",
    "PriceOscillator": "po",
    "PriceRateOfChange": "roc",
    "RelativeStrengthIndex": "rsi",
    "StandardDeviation": "stdev",
    "StochasticOscillator": "stoch",
    "TripleExponentialMovingAverage": "tema",
    "TypicalPrice": "hlc3",
    "UltimateOscillator": "uo",
    "VerticalHorizontalFilter": "vhf",
    "VolumeOscillator": "pvo",
    "WeightedClose": "wcp",
    "WilliamsR": "willr",
    "Qstick": "qstick",
    "TimeSeriesForecast": "linreg",       # linreg(tsf=True); see CANDIDATE_KWARGS
    "VolumeRateOfChange": "roc",          # roc fed VOLUME; see CANDIDATE_INPUT
    "RelativeVolatilityIndex": "rvi",
    "StochasticMomentumIndex": "smi",
    "WildersSmoothing": "rma",            # RMA IS Wilder's smoothing
    "Performance": "percent_return",      # related; the OUTPUT decides
    # REJECTED after checking, not skipped:
    #   Envelopes -> kc/accbands   fixed-% bands vs ATR-based Keltner. Different.
    #   RangeIndicator -> range_profile
    #                              range_profile is a TVPTA volume-at-price
    #                              port, unrelated to tti's range indicator.
    # DELIBERATELY ABSENT, each for a measured or documented reason:
    #   MarketFacilitationIndex   Bill Williams (high-low)/volume. NOT the
    #                             fork's `mfi` (Money Flow Index) -- an
    #                             `_acronym()` collision that shipped as an
    #                             audited identity.
    #   ProjectionOscillator      `po` is already the Price Oscillator; the
    #                             same collision one row down.
    #   WilliamsAccumulationDistribution
    #                             a different accumulation rule from Chaikin's
    #                             `ad`, which belongs to
    #                             AccumulationDistributionLine above.
}

# Some identities need more than a name. `linreg` is the Time Series Forecast
# only under `tsf=True`, and `roc` is the Volume Rate of Change only when fed
# the volume series. Both shipped as false gap rows for want of these channels.
CANDIDATE_KWARGS = {
    "TimeSeriesForecast": {"tsf": True},
}
CANDIDATE_INPUT = {
    "VolumeRateOfChange": "volume",
}

# Classes with NO fork counterpart, each with the reason stated. A `port` row
# must be here or must show a tried-and-failed candidate --
# `test_every_gap_row_states_why_it_is_a_gap` enforces it, because five rounds
# of false absences all shipped through a suite that only ever checked `have`.
REJECTED = {
    "MarketFacilitationIndex":
        "Bill Williams (high-low)/volume. NOT the fork's `mfi` (Money Flow "
        "Index) -- an acronym collision that once shipped as an audited identity.",
    "ProjectionOscillator":
        "`po` is already the Price Oscillator; the same acronym collision.",
    "WilliamsAccumulationDistribution":
        "a different accumulation rule from Chaikin's `ad`, which belongs to "
        "AccumulationDistributionLine.",
    "Envelopes":
        "fixed-percentage bands around an MA; `kc` is ATR-based and `accbands` "
        "is a different construction. Checked and rejected, not skipped.",
    "RangeIndicator":
        "`range_profile` is a TVPTA volume-at-price port, unrelated.",
    "IntradayMomentumIndex":
        "open->close INTRABAR momentum; `rsi` is close-to-close. Corroborated "
        "absent by the TA-Lib scan (`IMI`).",
    "ProjectionBands": "no fork counterpart.",
    "RelativeMomentumIndex": "no fork counterpart (RMI is not RSI).",
    "SwingIndex": "no fork counterpart (Wilder's ASI).",
    "VolatilityChaikins": "no fork counterpart; corroborated by TA-Lib's gap.",
}

# A name map is a claim. An entry pointing at a fork function that does not
# exist silently produced a `port` row in the published gap list
# (`VolumeOscillator -> vosc`, and the fork has no `vosc`), and an entry naming
# a tti class that does not exist is dead weight nobody notices
# (`RateOfChange`). Both are fatal now, exactly as in the reference scanner.
_missing_fork = sorted(v for v in CANDIDATE.values() if v not in SURFACE)
if _missing_fork:
    raise SystemExit(
        f"CANDIDATE points at fork names that do not exist: {_missing_fork}. "
        f"An unresolvable candidate silently became a `port` row in the "
        f"published gap list once already."
    )

# tti's signal layer is deliberately OUT OF SCOPE, not missing (TTIND-1).
SIGNAL_METHOD = "getTiSignal"


def _validate_candidate_keys():
    """Every CANDIDATE key must name a real tti class."""
    classes = {n for n in dir(tti_ind)
               if n[0].isupper() and inspect.isclass(getattr(tti_ind, n))}
    stale = sorted(set(CANDIDATE) - classes)
    if stale:
        raise SystemExit(
            f"CANDIDATE names tti classes that do not exist: {stale}")


def _tti_frame(frame):
    """tti wants lowercase OHLCV on a DatetimeIndex, which the probe already is."""
    return frame[["open", "high", "low", "close", "volume"]].copy()


# tti takes `period` where the fork takes `length` (32 of 57 classes). Comparing
# each side at its OWN default is the PTCLASSIC-1 trap: it reports a default
# mismatch as different behaviour. The first run of this scanner did exactly
# that -- only the three parameter-FREE price transforms matched, and all 32
# length-taking indicators were filed `port - alternate impl`.
PINNED_PERIOD = PINNED_LENGTH   # ONE constant, from the resolver


def _compute_tti(cls, frame, period=None):
    """Construct and read back. NOT_CALLABLE when tti refuses the frame."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            np.seterr(all="ignore")
            kwargs = {}
            if period is not None:
                params = inspect.signature(cls.__init__).parameters
                if "period" in params:
                    kwargs["period"] = period
            instance = cls(input_data=_tti_frame(frame), **kwargs)
            return instance.getTiData()
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE


def _call_candidate(fork_name, frame, class_name, length=None):
    """Call the fork side through the SHARED resolver.

    This used to be a private reimplementation with its own series map -- one of
    three, which is how the scanners came to disagree about the same fork
    function.
    """
    return call_fork(getattr(ta, fork_name, None), frame,
                     kwargs=CANDIDATE_KWARGS.get(class_name),
                     length=length,
                     input_override=CANDIDATE_INPUT.get(class_name))


def _fork_outputs(frame, length=None):
    """Delegates to the ONE shared surface cache (`_altrepo_resolve`).

    This was a private reimplementation -- one of three, each with its own
    series map and its own idea of which parameter is the window.
    """
    return fork_surface_cache(frame, SURFACE, ta)


def _first_column(value):
    """tti always returns a DataFrame; compare its FIRST column.

    Stated rather than hidden: a multi-column tti indicator whose first column
    matches is recorded as a partial match in the note, not as full equivalence.
    """
    if value is None or value is NOT_CALLABLE:
        return value, None
    try:
        if hasattr(value, "columns"):
            cols = list(value.columns)
            return value[cols[0]], cols
    except Exception:                                       # noqa: BLE001
        pass
    return value, None


def classify(class_name, cls, frame, fork_cache, pinned_cache):
    """-> dict of CSV fields. Identity by measurement, candidate name second."""
    raw = _compute_tti(cls, frame)
    if raw is NOT_CALLABLE:
        return dict(verdict="unknown - not comparable", equivalent="",
                    audited="no", evidence="", match="not-computed",
                    note="tti refused the probe frame (its own validation or "
                         "NotEnoughInputData); NOT recorded as `have`",
                    columns="")
    series, columns = _first_column(raw)
    column_note = (f"tti returns {len(columns)} column(s) {columns}; compared on "
                   f"the first" if columns and len(columns) > 1 else "")

    rounded = _round_like_tti(series)

    # The MAPPED candidate is tried FIRST. The whole-surface search returns the
    # first match in sorted() order, which is an alphabetical accident: it gave
    # `accbands` to both BollingerBands and MovingAverage because both agree
    # with it at 4 decimals. A hypothesis checked beats a coincidence found.
    preferred = CANDIDATE.get(class_name)
    def _flat(value):
        # The shared cache stores a LIST of probed variants per name.
        return value if isinstance(value, list) else [value]

    ordered = ([(preferred, v) for v in _flat(fork_cache[preferred])]
               if preferred and preferred in fork_cache else [])
    # If this class HAS a mapped identity, only that identity may produce a
    # `have`. Searching the whole surface for a multi-column output finds
    # coincidences: `accbands` agreed at 4dp with both tti's BollingerBands and
    # its MovingAverage, and both were recorded as `have` on the same fork
    # function. A mapped class that does not match its map is an alternate
    # implementation, not a match to something else.
    if preferred is None:
        ordered += [(k, v) for k, vs in fork_cache.items()
                    for v in _flat(vs)]

    for fork_name, theirs in ordered:
        outcome, detail = _same_output(rounded, _round_like_tti(theirs),
                                       frame)
        if outcome in ("identical", "warmup-offset"):
            fork_file = _source_file(ta, fork_name)
            evidence = (f"{_rel(fork_file, FORK)}:{_def_line(fork_file, fork_name)}"
                        if fork_file else "")
            return dict(verdict="have", equivalent=fork_name, audited="yes",
                        evidence=evidence, match="identical",
                        note=(f"resolved by {'MAP' if fork_name == preferred else 'SEARCH'} "
                              f"at tti's own {TTI_DECIMALS}-decimal precision "
                              f"(it rounds): {detail}. {column_note}").strip(),
                        columns=str(columns or ""))

    # `_acronym()` is GONE as a source of identity. It guessed `adl` for
    # AccumulationDistributionLine and `co` for ChaikinOscillator, both of which
    # the fork ships under other names, and those rows were then published as
    # measured absences. An unmapped class is now honestly unmapped.
    candidate = CANDIDATE.get(class_name)
    if candidate is not None and candidate in SURFACE:
        fork_fn = getattr(ta, candidate, None)
        theirs = _call_candidate(candidate, frame, class_name)
        if theirs is NOT_CALLABLE:
            theirs = fork_cache.get(candidate)
        if theirs is not None and theirs is not NOT_CALLABLE:
            outcome, detail = _same_output(rounded,
                                           _round_like_tti(theirs), frame)
            if outcome in ("not-callable", "unknown", "degenerate"):
                # Previously fell through into `port - alternate impl`, so
                # `test_identity_is_resolved_for_every_class` could never fail:
                # classify() emitted `unknown` on exactly one path.
                return dict(verdict="unknown - not comparable",
                            equivalent=candidate, audited="no", evidence="",
                            match=outcome,
                            note=f"mapped to `{candidate}` but the pair could "
                                 f"not be compared: {detail}. NOT an absence "
                                 f"and NOT a `have`.", columns=str(columns or ""))
            # Retry with BOTH sides pinned to the same window before calling it
            # a behavioural difference.
            if outcome != "identical":
                pinned_raw = _compute_tti(cls, frame, period=PINNED_PERIOD)
                pinned_series, _ = _first_column(pinned_raw)
                pinned_theirs = _call_candidate(candidate, frame, class_name,
                                                length=PINNED_PERIOD)
                if pinned_theirs is NOT_CALLABLE:
                    pinned_theirs = pinned_cache.get(candidate)
                if pinned_theirs is NOT_CALLABLE:
                    pinned_theirs = None
                if pinned_theirs is None:
                    # `donchian`, `macd`, `stoch`, `kvo`, `smi`, `ichimoku` and
                    # `psar` expose no `length`, so the matched-window retry
                    # cannot run for them. Asserting "different output" without
                    # it is comparing tti at period 14 against donchian at 20.
                    return dict(verdict="unknown - not comparable",
                                equivalent=candidate, audited="no", evidence="",
                                match="window-not-matched",
                                note=f"`{candidate}` exposes no `length`, so the "
                                     f"matched-window retry could not run; the "
                                     f"default-window difference is NOT evidence "
                                     f"of different behaviour. {column_note}".strip(),
                                columns=str(columns or ""))
                if (pinned_series is not NOT_CALLABLE
                        and pinned_series is not None
                        and pinned_theirs is not None):
                    p_out, p_detail = _same_output(
                        _round_like_tti(pinned_series),
                        _round_like_tti(pinned_theirs), frame)
                    if p_out in ("identical", "warmup-offset"):
                        fork_file = _source_file(ta, candidate)
                        evidence = (f"{_rel(fork_file, FORK)}:"
                                    f"{_def_line(fork_file, candidate)}"
                                    if fork_file else "")
                        return dict(
                            verdict="have", equivalent=candidate,
                            audited="yes", evidence=evidence,
                            match="identical-when-pinned",
                            note=f"identical at tti's {TTI_DECIMALS}-decimal "
                                 f"precision once BOTH sides use period="
                                 f"{PINNED_PERIOD} ({p_detail}). Differed at "
                                 f"defaults only -- tti's default window "
                                 f"differs from the fork's. {column_note}".strip(),
                            columns=str(columns or ""))
            fork_file = _source_file(ta, candidate)
            evidence = (f"{_rel(fork_file, FORK)}:{_def_line(fork_file, candidate)}"
                        if fork_file else "")
            return dict(verdict="port - alternate impl", equivalent=candidate,
                        audited="yes", evidence=evidence, match="divergent",
                        note=f"same indicator by name ({class_name} -> "
                             f"{candidate}) but different output: {detail}. "
                             f"{column_note}".strip(),
                        columns=str(columns or ""))
        if fork_fn is not None:
            return dict(verdict="unknown - not comparable", equivalent=candidate,
                        audited="no", evidence="", match="not-compared",
                        note=f"candidate `{candidate}` exists on the fork but "
                             f"was not callable on the probe frame, so the pair "
                             f"was never compared. NOT an alternate impl.",
                        columns=str(columns or ""))

    reason = REJECTED.get(class_name)
    return dict(verdict="port", equivalent="", audited="n/a", evidence="",
                match="no-match" if reason else "no-match-unexplained",
                note=((f"REJECTED after checking: {reason}" if reason else
                       "no fork indicator reproduces this output on the probe "
                       "frame, and no counterpart is mapped -- UNEXPLAINED, see "
                       "test_every_gap_row_states_why_it_is_a_gap")
                      if candidate is None else
                      f"mapped candidate `{candidate}` was tried and did not "
                      f"reproduce this output") + f". {column_note}".rstrip(),
                columns=str(columns or ""))


def _environment_stamp():
    try:
        import talib
        have = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        have = "talib ABSENT"
    import pandas
    return f"{have}; pandas {pandas.__version__}"


def main():
    classes = {n: getattr(tti_ind, n) for n in dir(tti_ind)
               if n[0].isupper() and inspect.isclass(getattr(tti_ind, n))}
    _validate_candidate_keys()
    frame = _probe_frame()
    fork_cache = _fork_outputs(frame)
    pinned_cache = _fork_outputs(frame, length=PINNED_PERIOD)
    print(f"tti classes: {len(classes)} | fork probe cache: {len(fork_cache)}",
          flush=True)

    env = _environment_stamp()
    rows = []
    for class_name in sorted(classes):
        cls = classes[class_name]
        result = classify(class_name, cls, frame, fork_cache,
                          pinned_cache)
        params = dict(CANDIDATE_KWARGS.get(class_name, {}))
        if class_name in CANDIDATE_INPUT:
            params["input"] = CANDIDATE_INPUT[class_name]
        rows.append({
            "class_name": class_name,
            "equivalent_params": ";".join(f"{k}={v}" for k, v in
                                          sorted(params.items())),
            "module": getattr(inspect.getmodule(cls), "__name__", ""),
            "verdict": result["verdict"],
            "pandas_ta_equivalent": result["equivalent"],
            "audited": result["audited"],
            "audit_evidence": result["evidence"],
            "match": result["match"],
            "has_signal_layer": str(hasattr(cls, SIGNAL_METHOD)),
            "note": result["note"],
            "probe_env": env,
        })

    fields = ["class_name", "module", "verdict", "pandas_ta_equivalent",
              "equivalent_params",
              "audited", "audit_evidence", "match", "has_signal_layer", "note",
              "probe_env"]
    with open(OUT, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    split = Counter(r["verdict"] for r in rows)
    print(f"wrote {OUT}  ({len(rows)} rows)")
    for verdict, n in split.most_common():
        print(f"  {verdict:34} {n:3}")
    signal = sum(1 for r in rows if r["has_signal_layer"] == "True")
    print(f"\ncarry a {SIGNAL_METHOD}() buy/sell layer: {signal}/{len(rows)} "
          f"-- OUT OF SCOPE by TTIND-1, not counted as a gap")
    resolved = sum(1 for r in rows if r["verdict"] != "unknown - not comparable")
    print(f"identity resolved for {resolved}/{len(rows)}")


if __name__ == "__main__":
    main()
