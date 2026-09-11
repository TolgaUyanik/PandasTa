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
from _altrepo_resolve import (
    fork_surface_cache,                              # noqa: E402
    PINNED_LENGTH, call_fork, probe_variants,
)
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
    # DELIBERATELY ABSENT, and still absent after TALIB-1:
    #   BETA  once pointed at a fork `beta` that DID NOT EXIST -- a dangling
    #         candidate, the defect the reference scanner made fatal. TALIB-1
    #         ported one, so the name now resolves through the lower-case
    #         path; it does not need, and must not get, a hand alias.
    #   IMI   Intraday Momentum Index is open->close INTRABAR; `rsi` is
    #         close-to-close. Mapping it to `rsi` dressed a genuinely absent
    #         indicator as a variant of a shipped one. TALIB-1 ported `imi`
    #         itself, which is what closed the row -- again by name, not here.
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
PINNED_PERIOD = PINNED_LENGTH   # ONE constant, from the resolver

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
        # By ROLE, not by the single literal name. `STOCHF` exposes
        # `fastk_period`, so pinning only `timeperiod` moved neither side and
        # the row shipped as a 59.1 "divergence" while the classic scan called
        # the same thing `have` -- the cross-scanner contradiction again.
        for window in ("timeperiod", "fastk_period", "fast_period", "period",
                       "slowk_period"):
            if window in params:
                fn.set_parameters(**{window: PINNED_PERIOD})
                break
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
    """Call the fork side through the SHARED resolver.

    The private version had no two-series path, which is why TA-Lib `CORREL`
    shipped `unknown - not comparable` while `ta.correlation` reproduces it to
    1.289e-11.
    """
    return call_fork(getattr(ta, fork_name, None), frame,
                     kwargs=CANDIDATE_KWARGS.get(talib_name or ""),
                     length=PINNED_PERIOD)


def _fork_outputs(frame):
    """Delegates to the ONE shared surface cache (`_altrepo_resolve`).

    This was a private reimplementation -- one of three, each with its own
    series map and its own idea of which parameter is the window.
    """
    return fork_surface_cache(frame, SURFACE, ta)


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
    # Single-column only. `ravel()` on two multi-column frames interleaves them
    # row-major, so the "comparison" would be between two meaningless
    # interleavings whenever both sides happen to share a shape.
    for side in (a, b):
        if getattr(side, "ndim", 1) > 1 or (
                hasattr(side, "columns") and len(side.columns) > 1):
            return None
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 40:
        return None
    xs, ys = x[mask], y[mask]
    cut = int(len(xs) * 0.75)
    tail_x, tail_y = xs[cut:], ys[cut:]
    if tail_x.size < 10:
        return None
    # Degeneracy: two unrelated series that both sit near zero, or both
    # saturate at the same bound over the final quarter, give rel ~ 0 and would
    # be promoted to `have` on nothing.
    if np.ptp(tail_x) == 0 or np.ptp(tail_y) == 0:
        return None
    scale = np.maximum(np.abs(xs), np.abs(ys))
    scale[scale < 1e-12] = 1.0
    rel = np.abs(xs - ys) / scale
    return float(rel[cut:].max())


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
        # Every cached variant, plus the pinned call. Passing the cache's LIST
        # straight into `_same_output` made this block silently unable to
        # compare anything -- and the search loop below skips `preferred`, so
        # `stoch` was never compared at all. That is how `STOCHF` stayed a
        # "divergence" against a fork function the classic scan calls `have`.
        cached_variants = fork_cache.get(preferred) or []
        if not isinstance(cached_variants, list):
            cached_variants = [cached_variants]
        candidates = [(False, v) for v in cached_variants]
        candidates.append((True, _fork_pinned(preferred, frame, name)))
        for pinned, theirs in candidates:
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
    for fork_name, variants in fork_cache.items():
        if fork_name == preferred:
            continue
        # The shared cache holds a LIST of probed variants per name, not one
        # output. Treating it as a single value silently un-found the five
        # price transforms.
        outcome = detail = None
        for theirs in variants:
            outcome, detail = _same_output(mine, theirs, frame)
            if outcome in ("identical", "warmup-offset"):
                break
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
        # The default cache is built close-only, so a two-series fork function
        # (`correlation`) is simply absent from it. Guarding the whole block on
        # its presence skipped straight past the shared resolver -- which is
        # exactly why `CORREL` stayed `unknown` after ALTFIX-0 supposedly fixed
        # it. Fall through to the pinned path either way.
        aligned_frame = None
        # ALL cached variants, not just the first. Taking `cached[0]` meant the
        # preferred-candidate branch saw one parameterisation while the search
        # branch saw every one -- which is why `STOCHF` stayed a "divergence"
        # against `stoch` that the classic scan calls `have`.
        cached = fork_cache.get(lower)
        variants = cached if isinstance(cached, list) else (
            [cached] if cached is not None else [])
        theirs = None
        for candidate_out in variants:
            if _same_output(mine, candidate_out, frame)[0] in (
                    "identical", "warmup-offset"):
                theirs = candidate_out
                break
        if theirs is None and variants:
            theirs = variants[0]
        if theirs is None:
            # TA-Lib's abstract API feeds its two-input functions (high, low);
            # the resolver's generic second series is `open`. Comparing those is
            # comparing two different questions, and it read as a 1.99
            # divergence. Feed the fork the SAME pair TA-Lib used.
            fn = getattr(ta, lower, None)
            # NOT `frame.rename` -- the frame already HAS close/open, so
            # renaming high->close produced DUPLICATE columns and
            # `frame["close"]` came back as a 2-column DataFrame.
            aligned = frame.copy()
            aligned["close"] = frame["high"]
            aligned["open"] = frame["low"]
            aligned_frame = aligned
            theirs = call_fork(fn, aligned) if fn is not None else None
            if theirs is None:
                theirs = call_fork(fn, frame)
        if theirs is not None:
            outcome, _ = _same_output(mine, theirs, frame)
            if outcome != "identical":
                # Retry with both sides on the same window.
                pinned_mine = _call_talib_pinned(name, inputs, frame.index)
                # Same aligned inputs as above, or the pinned retry compares
                # (high, low) against (close, open) and reports a 1.99
                # "divergence" between two identical implementations.
                pinned_theirs = _fork_pinned(lower,
                                             frame if aligned_frame is None
                                             else aligned_frame,
                                             name)
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
