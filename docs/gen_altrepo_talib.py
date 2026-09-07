# -*- coding: utf-8 -*-
"""TALIB-2 (and TALIB-0, merged into it): classify every TA-Lib function.

TALIB-0 asked for a coverage diff against "TA-Lib's ~158 functions" and a CSV in
`docs/`. TALIB-2 asked for the same diff as a section of the shared
`IndicatorList.md`. Owner decision 2026-09-07: **merge into TALIB-2's shape** --
one scanner, one CSV beside `IndicatorList.md`, matching the ALTREPO contract
the other two repos follow. TALIB-0's "~158" is superseded by the measured
**161**, confirmed against the installed library.

The TA-Lib C library was NOT installed when this task was written, which would
have forced a name-and-docs audit -- the exact method that produced four false
verdicts in the pandas-ta-classic scan. Owner authorised installing it, so every
function here is CALLED and compared, the same standard as PTCLASSIC.

Two routing rules come from the task itself, not from this scanner's judgement:

* **Pattern Recognition (61 `CDL*` functions) routes to CANDLE-2**, not counted
  as a gap here. `pandas_ta.cdl_pattern` already wraps the whole set when TA-Lib
  is importable -- which it now is -- so counting them as absent would
  double-book work CANDLE-2 owns.
* **Math Operators + Math Transform (26) are arithmetic helpers**, not features:
  `ADD`, `SIN`, `FLOOR`. Same call as classic's `math/` group.

⚠ Licence: ta-lib-python is BSD-2-Clause. Attribution required on any port; the
repo must not be committed into this one.

Usage:  python docs/gen_altrepo_talib.py [out.csv]
"""
import csv
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    SIBLING, "altrepo_talib.csv")

sys.path.insert(0, FORK)
sys.path.insert(0, HERE)

try:
    import talib
    from talib import abstract
except ImportError:                                         # pragma: no cover
    sys.exit("TA-Lib is not installed; this scan requires it (see TALIB-2)")

import numpy as np                                          # noqa: E402
import pandas_ta as ta                                      # noqa: E402
from pandas import Series                                   # noqa: E402
from gen_altrepo_pandas_ta_classic import (                 # noqa: E402
    SURFACE, NOT_CALLABLE, _call, _def_line, _probe_frame, _rel, _same_output,
    _source_file,
)

# TA-Lib's name for a thing the fork spells differently. A CANDIDATE only:
# each is still confirmed or refuted by output, never accepted on the name.
# Without this the gap read 34 and listed SAR, STDDEV, VAR, ULTOSC and
# LINEARREG -- all of which the fork ships.
CANDIDATE = {
    "SAR": "psar", "STDDEV": "stdev", "VAR": "variance", "ULTOSC": "uo",
    "LINEARREG": "linreg", "LINEARREG_SLOPE": "linreg",
    "LINEARREG_ANGLE": "linreg", "LINEARREG_INTERCEPT": "linreg", "AVGDEV": "mad",
    "ROCP": "roc", "ROCR": "roc", "ROCR100": "roc", "STOCHF": "stoch",
    "MINUS_DI": "adx", "PLUS_DI": "adx", "MINUS_DM": "dm", "PLUS_DM": "dm",
    "DX": "adx", "ADXR": "adx", "AROONOSC": "aroon", "MACDEXT": "macd",
    "MACDFIX": "macd", "CORREL": "correlation", "TSF": "linreg",
    # DELIBERATELY ABSENT:
    #   BETA  pointed at a fork `beta` that DOES NOT EXIST -- a dangling
    #         candidate, the defect the reference scanner made fatal.
    #   IMI   Intraday Momentum Index is open->close INTRABAR; `rsi` is
    #         close-to-close. Mapping it dressed a genuinely absent indicator
    #         as a variant of a shipped one.
}

# Restored from the reference scanner, which made this fatal after a dangling
# alias fabricated a `have`. `BETA -> beta` was exactly that hole reopened.
_missing_fork = sorted(v for v in CANDIDATE.values() if v not in SURFACE)
if _missing_fork:
    raise SystemExit(
        f"CANDIDATE points at fork names that do not exist: {_missing_fork}"
    )

# One fork function can expose several TA-Lib outputs behind boolean kwargs.
# `linreg` alone covers LINEARREG, _ANGLE, _SLOPE, _INTERCEPT and TSF. Calling
# it only at defaults made four of those look absent; two of them shipped in the
# published gap. Measured 2026-09-07: angle 1.799e-12, slope 3.197e-14 (the same
# function), intercept/tsf 0.853 (one x-origin step -- alternate, not absent).
CANDIDATE_KWARGS = {
    "LINEARREG_ANGLE": {"angle": True, "degrees": True},
    "LINEARREG_SLOPE": {"slope": True},
    "LINEARREG_INTERCEPT": {"intercept": True},
    "TSF": {"tsf": True},
}

# Pin both sides to the same window before calling a difference behavioural --
# the lesson PTCLASSIC-1 and TTIND-0 each had to learn separately.
PINNED_PERIOD = 14

CANDLE_GROUP = "Pattern Recognition"
MATH_GROUPS = {"Math Operators", "Math Transform"}


def _environment_stamp():
    import pandas
    return f"talib {talib.__version__}; pandas {pandas.__version__}"


def _talib_inputs(frame):
    return {
        "open": frame["open"].to_numpy(dtype="float64"),
        "high": frame["high"].to_numpy(dtype="float64"),
        "low": frame["low"].to_numpy(dtype="float64"),
        "close": frame["close"].to_numpy(dtype="float64"),
        "volume": frame["volume"].to_numpy(dtype="float64"),
    }


def _call_talib(name, inputs, index):
    """Call through the abstract API. Returns NOT_CALLABLE on refusal."""
    try:
        fn = abstract.Function(name)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            np.seterr(all="ignore")
            out = fn(inputs)
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE
    if isinstance(out, list):
        if not out:
            return NOT_CALLABLE
        out = out[0]
    try:
        return Series(np.asarray(out, dtype="float64"), index=index)
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE


def _call_talib_pinned(name, inputs, index):
    try:
        fn = abstract.Function(name)
        params = fn.parameters
        if "timeperiod" in params:
            fn.set_parameters(timeperiod=PINNED_PERIOD)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            np.seterr(all="ignore")
            out = fn(inputs)
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE
    if isinstance(out, list):
        if not out:
            return NOT_CALLABLE
        out = out[0]
    try:
        return Series(np.asarray(out, dtype="float64"), index=index)
    except Exception:                                       # noqa: BLE001
        return NOT_CALLABLE


def _fork_pinned(fork_name, frame, talib_name=None):
    import inspect

    fn = getattr(ta, fork_name, None)
    if fn is None:
        return None
    try:
        params = inspect.signature(fn).parameters
        series_kwargs = {
            p: frame[{"open_": "open", "open": "open", "high": "high",
                      "low": "low", "close": "close", "volume": "volume",
                      "source": "close"}[p]]
            for p in params
            if p in ("open", "open_", "high", "low", "close", "volume",
                     "source")}
        if not series_kwargs:
            return None
        extra = dict(CANDIDATE_KWARGS.get(talib_name or "", {}))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            np.seterr(all="ignore")
            if "length" in params:
                return fn(**series_kwargs, length=PINNED_PERIOD, **extra)
            return fn(**series_kwargs, **extra)
    except Exception:                                       # noqa: BLE001
        return None


def _fork_outputs(frame):
    out = {}
    for name in sorted(SURFACE):
        fn = getattr(ta, name, None)
        if fn is None or not callable(fn):
            continue
        try:
            value = _call(fn, frame, name)
        except Exception:                                   # noqa: BLE001
            continue
        if value is NOT_CALLABLE or value is None:
            continue
        out[name] = value
    return out


def _tail_diff(a, b):
    """Max relative diff over the final quarter, or None.

    Max-abs-diff over the WHOLE overlap is dominated by warm-up transients, so a
    Wilder-seeding difference reads as a different implementation.
    """
    if a is None or b is None or a is NOT_CALLABLE:
        return None
    try:
        x = np.asarray(a, dtype="float64").ravel()
        y = np.asarray(b, dtype="float64").ravel()
    except Exception:                                       # noqa: BLE001
        return None
    if x.shape != y.shape:
        return None
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 40:
        return None
    xs, ys = x[mask], y[mask]
    scale = np.maximum(np.abs(xs), np.abs(ys))
    scale[scale < 1e-12] = 1.0
    rel = np.abs(xs - ys) / scale
    return float(rel[int(len(rel) * 0.75):].max())


def classify(name, group, frame, inputs, fork_cache):
    if group == CANDLE_GROUP:
        return dict(verdict="n/a - routed to CANDLE-2", equivalent="cdl_pattern",
                    audited="n/a", evidence="", match="",
                    note="TA-Lib's CDL* set; `pandas_ta.cdl_pattern` wraps the "
                         "whole family when TA-Lib is importable. Counting it "
                         "here would double-book work CANDLE-2 owns.")
    if group in MATH_GROUPS:
        return dict(verdict="n/a - arithmetic helper, not a feature",
                    equivalent="", audited="n/a", evidence="", match="",
                    note=f"{group}: scalar/vector maths (ADD, SIN, FLOOR), not "
                         f"an indicator.")

    mine = _call_talib(name, inputs, frame.index)
    if mine is NOT_CALLABLE:
        return dict(verdict="unknown - not comparable", equivalent="",
                    audited="no", evidence="", match="not-computed",
                    note="TA-Lib refused the probe frame; NOT recorded as `have`")

    # LIKE-FOR-LIKE FIRST. The surface search used to run ahead of this and
    # took the first alphabetical hit, which is how TA-Lib `EMA` was published
    # as equivalent to `mmar` (the Madrid Moving Average Ribbon, whose MMAR_30
    # column is ema(close,30)), `AVGPRICE` to `ha` instead of `ohlc4`, and
    # `MACDEXT` to `apo` instead of `macd`. A named candidate beats an
    # alphabetical coincidence.
    preferred = CANDIDATE.get(name, name.lower())
    if preferred in SURFACE:
        for pinned in (False, True):
            theirs = (_fork_pinned(preferred, frame, name) if pinned
                      else fork_cache.get(preferred))
            mine_side = (_call_talib_pinned(name, inputs, frame.index) if pinned
                         else mine)
            if theirs is None or mine_side is NOT_CALLABLE:
                continue
            outcome, detail = _same_output(mine_side, theirs, frame)
            if outcome in ("identical", "warmup-offset"):
                fork_file = _source_file(ta, preferred)
                evidence = (f"{_rel(fork_file, FORK)}:"
                            f"{_def_line(fork_file, preferred)}"
                            if fork_file else "")
                kw = CANDIDATE_KWARGS.get(name)
                return dict(verdict="have", equivalent=preferred, audited="yes",
                            evidence=evidence, match=outcome,
                            note=(f"resolved by MAP"
                                  + (f" with {kw}" if kw else "")
                                  + (" at matched window" if pinned else "")
                                  + f": {detail}"))

    # Surface search, AFTER like-for-like. My round-3 edit deleted this loop
    # outright and five price transforms (AVGPRICE, MEDPRICE, TYPPRICE,
    # WCLPRICE, TRANGE) immediately reappeared in the gap while the fork ships
    # ohlc4/hl2/hlc3/wcp/true_range. Restored, and it now records that the
    # match came from a search rather than a name.
    for fork_name, theirs in fork_cache.items():
        if fork_name == preferred:
            continue
        outcome, detail = _same_output(mine, theirs, frame)
        if outcome in ("identical", "warmup-offset"):
            fork_file = _source_file(ta, fork_name)
            evidence = (f"{_rel(fork_file, FORK)}:{_def_line(fork_file, fork_name)}"
                        if fork_file else "")
            return dict(verdict="have", equivalent=fork_name, audited="yes",
                        evidence=evidence, match=outcome,
                        note=f"resolved by SEARCH (no mapped candidate matched): "
                             f"{detail}")

    lower = preferred
    if lower in SURFACE:
        theirs = fork_cache.get(lower)
        if theirs is not None:
            outcome, _ = _same_output(mine, theirs, frame)
            if outcome != "identical":
                # Retry with both sides on the same window.
                pinned_mine = _call_talib_pinned(name, inputs, frame.index)
                pinned_theirs = _fork_pinned(lower, frame)
                if (pinned_mine is not NOT_CALLABLE
                        and pinned_theirs is not None):
                    p_out, p_detail = _same_output(pinned_mine, pinned_theirs,
                                                   frame)
                    if p_out in ("identical", "warmup-offset"):
                        fork_file = _source_file(ta, lower)
                        evidence = (f"{_rel(fork_file, FORK)}:"
                                    f"{_def_line(fork_file, lower)}"
                                    if fork_file else "")
                        return dict(
                            verdict="have", equivalent=lower, audited="yes",
                            evidence=evidence, match="identical-when-pinned",
                            note=f"identical once BOTH sides use "
                                 f"timeperiod/length={PINNED_PERIOD} "
                                 f"({p_detail}); differed at defaults only")
            _, detail = _same_output(mine, theirs, frame)
            fork_file = _source_file(ta, lower)
            evidence = (f"{_rel(fork_file, FORK)}:{_def_line(fork_file, lower)}"
                        if fork_file else "")
            tail = _tail_diff(mine, fork_cache.get(lower))
            if tail is not None and tail < 1e-6:
                # Converges: same recurrence, different seed. Filing this as a
                # porting candidate sends a reader to compare identical
                # formulas -- RSI's tail diff is 2.7e-06, ATR's 6.4e-08.
                return dict(verdict="have", equivalent=lower, audited="yes",
                            evidence=evidence, match="seeding",
                            note=f"same indicator, different SEEDING: diverges "
                                 f"early ({detail}) but the last quarter agrees "
                                 f"to {tail:.2e}")
            return dict(verdict="port - alternate impl", equivalent=lower,
                        audited="yes", evidence=evidence, match="divergent",
                        note=f"same name ({name} -> {lower}) but different "
                             f"output: {detail}"
                             + (f"; tail diff {tail:.2e}" if tail is not None
                                else ""))
    if lower in SURFACE:
        # The name maps but the probe harness could not build a call for the
        # fork side (two-series signatures like `correlation`). That is a
        # limitation of THIS SCANNER, not an absence. `CORREL` shipped as a
        # `port` row asserting "no fork name matches" while `ta.correlation`
        # sat on the surface, mapped, uncalled.
        return dict(verdict="unknown - not comparable", equivalent=lower,
                    audited="no", evidence="", match="not-computed",
                    note=f"`{lower}` exists on the fork and is mapped, but the "
                         f"probe harness has no call for its signature, so the "
                         f"pair was never compared. NOT an absence.")
    return dict(verdict="port", equivalent="", audited="n/a", evidence="",
                match="no-match",
                note="no fork indicator reproduces this output on the probe "
                     "frame and no counterpart is mapped")


def main():
    groups = talib.get_function_groups()
    group_of = {fn: g for g, fns in groups.items() for fn in fns}
    frame = _probe_frame()
    inputs = _talib_inputs(frame)
    fork_cache = _fork_outputs(frame)
    env = _environment_stamp()
    print(f"TA-Lib functions: {len(group_of)} | fork probe cache: "
          f"{len(fork_cache)}", flush=True)

    rows = []
    for name in sorted(group_of):
        group = group_of[name]
        result = classify(name, group, frame, inputs, fork_cache)
        rows.append({
            "name": name, "group": group, "verdict": result["verdict"],
            "pandas_ta_equivalent": result["equivalent"],
            "audited": result["audited"],
            "audit_evidence": result["evidence"], "match": result["match"],
            "note": result["note"], "probe_env": env,
        })

    fields = ["name", "group", "verdict", "pandas_ta_equivalent", "audited",
              "audit_evidence", "match", "note", "probe_env"]
    with open(OUT, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    split = Counter(r["verdict"] for r in rows)
    print(f"wrote {OUT}  ({len(rows)} rows)")
    for verdict, n in split.most_common():
        print(f"  {verdict:40} {n:4}")
    gap = sorted(r["name"] for r in rows if r["verdict"] == "port")
    print(f"\nthe gap ({len(gap)}): {', '.join(gap)}")


if __name__ == "__main__":
    main()
