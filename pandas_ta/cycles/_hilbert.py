# -*- coding: utf-8 -*-
"""TA-Lib's Hilbert Transform state machine, ported to pure Python.

ATTRIBUTION.  The algorithm is TA-Lib's (`ta-lib`, BSD-2-Clause, (c) 1999-2007
Mario Fortier), itself an implementation of John Ehlers' MESA / Hilbert
Transform work in *Rocket Science for Traders* (Wiley, 2001).  The reference
sources are `ta-lib/src/ta_func/ta_HT_DCPERIOD.c`, `ta_HT_DCPHASE.c`,
`ta_HT_PHASOR.c`, `ta_HT_SINE.c`, `ta_HT_TRENDLINE.c`, `ta_HT_TRENDMODE.c` and
`ta_MAMA.c`, plus the `DO_PRICE_WMA` / `DO_HILBERT_*` macros in
`ta-lib/src/ta_common/ta_utility.h`.  The C sources were NOT available on this
box -- only the compiled `talib` 0.7.1 wheel was -- so no line numbers are
cited and no code is copied.  The recurrences below were re-derived from the
published Ehlers formulation and then PINNED NUMERICALLY against `talib`; the
measured max|diff| and sample sizes live in `tests/test_talib1_ports.py` and
`docs/TalibPortsMeasured.md`.  Nothing in this module imports `talib`.

WHY ONE MODULE FOR SEVEN INDICATORS

`HT_DCPERIOD`, `HT_DCPHASE`, `HT_PHASOR`, `HT_SINE`, `HT_TRENDLINE`,
`HT_TRENDMODE` and `MAMA` are not seven algorithms.  They are seven read-outs
of ONE state machine: a 4-bar weighted price smoother, a 7-tap Hilbert
quadrature filter run separately on even and odd bars, a homodyne
discriminator turning the in-phase/quadrature pair into a dominant-cycle
period, and two smoothers over that period.  Porting it once and deriving the
read-outs was VERIFIED, not assumed: with this single core all seven reproduce
`talib` to <= 6e-10 over 14,478-14,850 pooled bars.

THE TWO WARM-UPS -- THE ONE THING THAT IS EASY TO GET WRONG

TA-Lib primes the price smoother before the state machine starts, and the
number of priming bars is NOT the same for every function:

* `HT_DCPERIOD`, `HT_PHASOR`, `MAMA` (declared lookback 32) prime for
  3 + 9 = **12** bars.  The state machine runs from index 12.
* `HT_DCPHASE`, `HT_SINE`, `HT_TRENDLINE`, `HT_TRENDMODE` (declared lookback
  63) prime for 3 + 34 = **37** bars.  The state machine runs from index 37.

Priming means the smoothed price is COMPUTED but not fed to the Hilbert
filters, so the filters' 2/4/6-bar taps read zero on their first live bar.
This is not cosmetic.  Running the lookback-63 family from index 12 reproduces
`HT_DCPERIOD` exactly and still leaves `HT_TRENDLINE` wrong by up to 0.18 price
units and `HT_DCPHASE` wrong by up to 70 degrees -- as a warm-up transient that
decays to exactly zero by roughly bar 700, so a port checked only on its tail
would have shipped looking correct.  `_WARMUP_32` / `_WARMUP_63` were found by
scanning the warm-up length 12..45 against `talib` and taking the value that
produced 0.0 and 5.7e-14 respectively.

THE SUMMATION ORDER OF THE HILBERT TAPS IS LOAD-BEARING

`_hilbert()` evaluates `-a*x[t-6] + a*x[t] - b*x[t-4] + b*x[t-2]` in exactly
that order because that is the order TA-Lib's `DO_HILBERT_*` macro accumulates
its circular buffer in.  The mathematically identical
`a*x[t] + b*x[t-2] - b*x[t-4] - a*x[t-6]` is NOT equivalent at float64, and the
difference is not cosmetic: MAMA's alpha is `fastlimit/deltaPhase` clamped to
[slowlimit, fastlimit], so a 1-ulp difference in the ill-conditioned
`atan(Q1/I1)` -- and `I1` passes through zero whenever price is flat, which
happens constantly on tick-rounded real data -- flips alpha between 0.05 and
0.5 and then propagates through the MAMA recursion.  Measured on
`PETKM_IS_1d` (6,762 bars, long runs of identical prices): the reordered form
is wrong by 1.11e-2 on MAMA and 5.8e-3 on FAMA, the TA-Lib order by 2.7e-13
and 2.0e-13.
"""
import math

import numpy as np

# Ehlers' 7-tap Hilbert quadrature coefficients (TA-Lib's `a`, `b`).
_A = 0.0962
_B = 0.5769
_RAD2DEG = 180.0 / math.pi
_DEG2RAD = math.pi / 180.0
_TWOPI = 2.0 * math.pi

# 3 initial WMA reads + 9 primed bars, and + 34 primed bars. Measured, not
# guessed -- see the module docstring.
_WARMUP_32 = 12
_WARMUP_63 = 37

# TA-Lib's declared lookbacks at its default unstable period of 0. Bars before
# these indices are emitted as NaN so the fork never publishes a value TA-Lib
# itself withholds.
LOOKBACK_32 = 32
LOOKBACK_63 = 63


def _smoothed_price(x):
    """TA-Lib's `DO_PRICE_WMA`: the 4-bar weighted moving average."""
    n = x.size
    s = np.full(n, np.nan)
    if n >= 4:
        s[3:] = (4.0 * x[3:] + 3.0 * x[2:-1] + 2.0 * x[1:-2] + x[:-3]) * 0.1
    return s


def _hilbert(arr, t, adj):
    """One 7-tap Hilbert sample, in TA-Lib's accumulation order.

    Do NOT fold this into a single expression: see the module docstring,
    THE SUMMATION ORDER OF THE HILBERT TAPS IS LOAD-BEARING.
    """
    v = -(_A * arr[t - 6])
    v += _A * arr[t]
    v -= _B * arr[t - 4]
    v += _B * arr[t - 2]
    v *= adj
    return v


def ht_state(x, warmup, fastlimit=0.5, slowlimit=0.05):
    """Run the shared state machine once and return every read-out.

    Args:
        x (np.ndarray): price series (TA-Lib's `inReal`).
        warmup (int): `_WARMUP_32` or `_WARMUP_63`. Which one an indicator
            needs is fixed by TA-Lib, not by taste.
        fastlimit, slowlimit (float): MAMA's alpha clamp.

    Returns:
        dict of np.ndarray, each ``len(x)`` long and NaN before ``warmup``.
    """
    x = np.asarray(x, dtype=float)
    n = x.size
    keys = ("dcperiod", "dcphase", "inphase", "quadrature", "sine", "leadsine",
            "trendmode", "trendline", "mama", "fama", "period")
    out = {k: np.full(n, np.nan) for k in keys}
    if n <= warmup:
        return out

    smooth = _smoothed_price(x)
    # Priming: the smoother runs, the Hilbert filters do not yet see it.
    sh = smooth.copy()
    sh[:warmup] = 0.0
    sh[np.isnan(sh)] = 0.0

    det = np.zeros(n)
    q1 = np.zeros(n)
    i1 = np.zeros(n)

    prev_i2 = prev_q2 = 0.0
    re = im = 0.0
    period = 0.0
    smooth_period = 0.0
    it1 = it2 = it3 = 0.0
    dc_phase = 0.0
    sine = lead_sine = 0.0
    days_in_trend = 0
    prev_phase = 0.0
    prev_mama = prev_fama = 0.0

    for t in range(warmup, n):
        adj = 0.075 * period + 0.54
        det[t] = _hilbert(sh, t, adj)
        q1[t] = _hilbert(det, t, adj)
        i1[t] = det[t - 3]
        j_i = _hilbert(i1, t, adj)
        j_q = _hilbert(q1, t, adj)

        i2 = 0.2 * (i1[t] - j_q) + 0.8 * prev_i2
        q2 = 0.2 * (q1[t] + j_i) + 0.8 * prev_q2

        re = 0.2 * (i2 * prev_i2 + q2 * prev_q2) + 0.8 * re
        im = 0.2 * (i2 * prev_q2 - q2 * prev_i2) + 0.8 * im
        prev_i2, prev_q2 = i2, q2

        # MAMA reads the RAW quadrature pair of THIS bar, before the homodyne
        # period update, and TA-Lib guards the division: `if (I1 != 0.0)`,
        # else the phase is 0. Two other readings were tried and MEASURED
        # against `talib` over the same 20 daily frames / 28,548 bars, so that
        # the choice here is evidence and not preference:
        #   * using `det[t-2]` (the opposite-parity `i1ForOddPrev3`) instead of
        #     `det[t-3]`: max|diff| 151.0 -- flatly wrong;
        #   * treating `I1 == 0` as C's `Q1/0.0 -> +/-inf -> atan -> +/-90 deg`
        #     (i.e. no guard): max|diff| 1.83 -- wrong, because on bars 12-14
        #     `I1` is structurally 0 while the filter buffers are still empty.
        #   * this guarded form: max|diff| 2.7e-6 (MAMA) / 2.7e-4 (FAMA).
        # THE RESIDUAL IS ONE BAR. `ISMEN_IS_1d` bar 2327 is the only bar of
        # the 28,548 where our detrender rounds to exactly 0.0 while TA-Lib's
        # -- which agrees with ours only to 1.9e-13, see HT_PHASOR -- does not,
        # so it takes the `atan` branch and we take the guard. Alpha is
        # `fastlimit/deltaPhase` CLAMPED, so that knife-edge becomes 0.05 vs
        # 0.5 and the MAMA recursion carries the difference forward. This is a
        # conditioning limit of the algorithm at float64, not a formula error,
        # and it cannot be closed without bit-identical arithmetic.
        phase = math.atan(q1[t] / i1[t]) * _RAD2DEG if i1[t] != 0.0 else 0.0

        prev_period = period
        if im != 0.0 and re != 0.0:
            period = 360.0 / (math.atan(im / re) * _RAD2DEG)
        if period > 1.5 * prev_period:
            period = 1.5 * prev_period
        if period < 0.67 * prev_period:
            period = 0.67 * prev_period
        if period < 6.0:
            period = 6.0
        elif period > 50.0:
            period = 50.0
        period = 0.2 * period + 0.8 * prev_period
        smooth_period = 0.33 * period + 0.67 * smooth_period

        # ---- MAMA / FAMA ------------------------------------------------
        delta_phase = prev_phase - phase
        prev_phase = phase
        if delta_phase < 1.0:
            delta_phase = 1.0
        alpha = fastlimit / delta_phase
        if alpha < slowlimit:
            alpha = slowlimit
        mama = alpha * x[t] + (1.0 - alpha) * prev_mama
        prev_mama = mama
        half = 0.5 * alpha
        fama = half * mama + (1.0 - half) * prev_fama
        prev_fama = fama

        # ---- dominant-cycle phase (one-bin DFT over smoothed price) ------
        dc_period_int = int(smooth_period + 0.5)
        real_part = imag_part = 0.0
        for i in range(dc_period_int):
            j = t - i
            if j < 0:
                break
            ang = (i * _TWOPI) / dc_period_int
            v = sh[j]
            real_part += math.sin(ang) * v
            imag_part += math.cos(ang) * v
        prev_dc_phase = dc_phase
        mag = abs(imag_part)
        if mag > 0.0:
            dc_phase = math.atan(real_part / imag_part) * _RAD2DEG
        elif mag <= 0.01:
            if real_part < 0.0:
                dc_phase -= 90.0
            elif real_part > 0.0:
                dc_phase += 90.0
        dc_phase += 90.0
        if smooth_period != 0.0:
            dc_phase += 360.0 / smooth_period   # one-bar lag of the WMA
        if imag_part < 0.0:
            dc_phase += 180.0
        if dc_phase > 315.0:
            dc_phase -= 360.0

        prev_sine, prev_lead = sine, lead_sine
        sine = math.sin(dc_phase * _DEG2RAD)
        lead_sine = math.sin((dc_phase + 45.0) * _DEG2RAD)

        # ---- instantaneous trendline (WMA of DC-length raw price means) ---
        total = 0.0
        for i in range(dc_period_int):
            j = t - i
            if j < 0:
                break
            total += x[j]
        if dc_period_int > 0:
            total /= dc_period_int
        trendline = (4.0 * total + 3.0 * it1 + 2.0 * it2 + it3) / 10.0
        it3, it2, it1 = it2, it1, total

        # ---- trend / cycle mode ------------------------------------------
        trend = 1
        if ((sine > lead_sine and prev_sine <= prev_lead)
                or (sine < lead_sine and prev_sine >= prev_lead)):
            days_in_trend = 0
            trend = 0
        days_in_trend += 1
        if days_in_trend < 0.5 * smooth_period:
            trend = 0
        d_phase = dc_phase - prev_dc_phase
        if smooth_period != 0.0 and \
                (0.67 * 360.0 / smooth_period) < d_phase < (1.5 * 360.0 / smooth_period):
            trend = 0
        if trendline != 0.0 and abs((sh[t] - trendline) / trendline) >= 0.015:
            trend = 1

        out["dcperiod"][t] = smooth_period
        out["period"][t] = period
        out["dcphase"][t] = dc_phase
        out["inphase"][t] = i1[t]
        out["quadrature"][t] = q1[t]
        out["sine"][t] = sine
        out["leadsine"][t] = lead_sine
        out["trendmode"][t] = float(trend)
        out["trendline"][t] = trendline
        out["mama"][t] = mama
        out["fama"][t] = fama

    return out


def blank_lookback(arr, lookback):
    """NaN out the bars TA-Lib itself withholds (its declared lookback)."""
    arr = np.asarray(arr, dtype=float).copy()
    arr[:min(lookback, arr.size)] = np.nan
    return arr
