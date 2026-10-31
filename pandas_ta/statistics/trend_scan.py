# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from pandas_ta.utils import get_offset, verify_series

#: Owner's decision was not given in the issue text ("The horizon set" was
#: left as a TODO for the port); this is the port's own choice -- five
#: trailing windows spanning short to medium daily-bar lookbacks, the same
#: order of magnitude as this repo's other multi-week params (ADX 14,
#: KPSS/CUSUM 100). See docs/TrendScanMeasured.md.
DEFAULT_HORIZONS = (5, 10, 20, 40, 60)


def _rolling_trend_t(z, valid, length):
    """The signed t-stat of the OLS slope of `z` on consecutive-integer time,
    over every trailing window of `length` bars, in O(n) via rolling sums
    kept at LOCAL (window-relative) scale -- not O(n * length) via a
    materialised window, and not a global running sum weighted by the bar's
    absolute position either: that alternative was tried first and measured,
    against a plain definitional-OLS oracle on a 4,000-bar walk (length 3),
    to reach |diff| 5.1e-8 by bar 2,500 and 1.4e-6 by bar 3,999, from
    subtracting two ~n**2-scale cumulative sums to recover an
    O(length)-scale window total -- vs 1.6e-9 / 7.2e-8 for the recurrence
    actually shipped below, which keeps `S1`/`S2`/`S3` bounded by the
    window instead (true incremental rolling sums, updated by dropping the
    leaving bar and adding the entering one each step). Both measured
    side by side in docs/measure_trend_scan_proxy.py's "rolling-sum
    precision" block.

    `out[length - 1] = ...` and `out[t] = ...` are the only two lines that
    place a result at the bar the window ENDS at (trailing). Writing at the
    bar the window STARTS at instead reproduces the source's own
    forward-looking (label) form exactly -- same window, same regression,
    visible `length - 1` bars earlier than its last input bar -- which is
    the Gate B mutant in tests/test_trend_scan.py.
    """
    n = len(z)
    out = np.full(n, np.nan)
    if length > n:
        return out

    zf = np.where(valid, z, 0.0)
    ibar = (length - 1) / 2.0
    Sxx = length * (length * length - 1) / 12.0  # var(0..length-1) * length
    df = length - 2

    def _t(S1, S2, S3, cnt):
        if cnt != length:
            return np.nan
        Sxy = S2 - ibar * S1
        Syy = S3 - S1 * S1 / length
        slope = Sxy / Sxx
        SSR = Syy - slope * Sxy
        if not (SSR > 0):  # a degenerate (near-perfectly-flat residual) fit
            return np.nan
        return slope * (Sxx * df / SSR) ** 0.5

    window = zf[:length]
    S1 = float(window.sum())
    S2 = float(np.dot(np.arange(length, dtype=float), window))
    S3 = float(np.dot(window, window))
    cnt = int(valid[:length].sum())
    out[length - 1] = _t(S1, S2, S3, cnt)

    for t in range(length, n):
        leaving, entering = zf[t - length], zf[t]
        S2 = S2 - S1 + leaving + (length - 1) * entering
        S1 = S1 - leaving + entering
        S3 = S3 - leaving * leaving + entering * entering
        cnt = cnt - int(valid[t - length]) + int(valid[t])
        out[t] = _t(S1, S2, S3, cnt)
    return out


def trend_scan(close, horizons=None, offset=None, **kwargs):
    """Indicator: Trailing Trend Scan (TSCAN)"""
    # Validate Arguments
    horizons = DEFAULT_HORIZONS if horizons is None else horizons
    horizons = sorted(set(int(h) for h in horizons))
    if not horizons or horizons[0] < 3:
        raise ValueError(f"trend_scan: need at least one horizon >= 3; got {horizons}")
    max_h = horizons[-1]
    close = verify_series(close, max_h)
    offset = get_offset(offset)

    if close is None: return

    # Calculate Result. z = log(close / first finite positive close): a
    # ratio of two closes, so under a power-of-two price rescale the
    # division cancels the exact common factor BEFORE log is ever called,
    # making z bit-identical to the unscaled run (see docs/TrendScanMeasured.md,
    # Gate D -- log(close) directly does NOT have this property). The
    # regression's slope, its standard error and the t-stat are invariant
    # to ANY additive shift of z, so one series-wide anchor gives the
    # identical (slope, t) a window-local anchor would, without redoing the
    # ratio per window -- which is what keeps each horizon's cost at O(n)
    # rather than O(n * length), the budget the issue asked for.
    vals = close.to_numpy(dtype=float)
    valid = np.isfinite(vals) & (vals > 0)
    usable = vals[valid]
    if len(usable) <= max_h: return
    anchor = usable[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.log(vals / anchor)
    z[~valid] = np.nan

    n = len(z)
    best_t = np.full(n, np.nan)
    best_L = np.full(n, np.nan)
    for length in horizons:
        t_L = _rolling_trend_t(z, valid, length)
        better = np.isfinite(t_L) & (np.isnan(best_t) | (np.abs(t_L) > np.abs(best_t)))
        best_t = np.where(better, t_L, best_t)
        best_L = np.where(better, float(length), best_L)

    tag = "-".join(str(h) for h in horizons)
    df = DataFrame({f"TSCAN_T_{tag}": best_t, f"TSCAN_L_{tag}": best_L}, index=close.index)

    # Offset
    if offset != 0:
        df = df.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)

    # Name and Categorize it
    df.name = f"TSCAN_{tag}"
    df.category = "statistics"

    return df


trend_scan.__doc__ = \
"""Trailing Trend Scan (TSCAN)

For each horizon `L` in a set, the t-statistic of the slope of an OLS
regression of log price on time over the trailing `L` bars -- how
statistically significant the local linear trend is, not how big it is.
Emits the signed t-stat of the horizon with the largest `|t|`, and that
horizon itself, so one column answers "is there a trend on ANY of these
scales" without the caller picking a single lookback up front.

Source: Lopez de Prado, *Machine Learning for Asset Managers* (2020), ch. 5
"Financial Labels" -- trend scanning. The book labels bars FORWARD-looking,
for supervised-learning targets; this port keeps only the trailing,
feature-side half (the task's decision), which the book does not itself
describe, so there is no line-by-line source to cite the way a Pine port
would. PandasTa issue #20.

Two things the task flagged, and this port's answers:

1.  **At a single horizon this restates `linreg`'s `r`** --
    `t = r * sqrt((n - 2) / (1 - r**2))` is monotone in `r` -- so only the
    MAX-over-horizons here is a new column; the task's own reasoning, not
    re-derived. `tests/test_trend_scan.py` still checks the single-horizon
    case against this formula, as a second Gate A oracle.
2.  **Gate D: `log(8 * P)` is not bit-identical to `log(P) + log(8)`.**
    This port regresses on `z = log(close / anchor)`, `anchor` the
    series' first finite positive close (the device `ffd` and
    `kalman_trend` use) -- a ratio, computed by FLOAT DIVISION before log
    is called, so it is bit-identical under a power-of-two rescale by
    construction. Measured directly in `docs/measure_trend_scan_proxy.py`'s
    "Gate D defect" block: regressing on `log(close)` directly instead (the
    naive reading of the task) moves the max-|t| output by a small but
    NONZERO amount under x8/x64; the ratio form moves it by exactly 0.0.
    The task's own phrasing anchors `P_ref` "inside the window" (re-picked
    per window); this port uses ONE anchor for the whole series instead,
    because slope/SE/t are invariant to ANY additive shift of `z` -- so a
    window-local anchor and a series-wide anchor give the IDENTICAL
    (slope, t) in exact arithmetic (measured max |diff| 2.1e-14, a fresh
    per-window price ratio vs this module's output, over 3 window
    positions on a 4,000-bar walk), and the series-wide anchor is what
    keeps the cost at O(n) per horizon (one running `z`, reused by every
    window) instead of O(n * L) (a fresh ratio per window). Measured
    equivalence: see `docs/measure_trend_scan_proxy.py`'s "anchor choice" block.

Causal: bar `T`'s output for horizon `L` reads bars `T - L + 1 .. T` only.
The forward-looking (label) version the book actually describes would read
`T .. T + L - 1`; `tests/test_trend_scan.py` mutates the module into
exactly that form and shows it leaks the future where the real module does
not -- the task's explicitly-requested Gate B mutant.

Scale-free: bit-identical under x8/x64, within tolerance under x10/x3.7.
A window with a NaN, zero or negative close is NaN for that horizon, and so
is a degenerate (near-perfectly-flat residual) fit; ties between horizons
keep the smaller `L`.

Cost: O(n * |horizons|) -- each horizon keeps three running sums (not a
rolling window materialised and refit per bar), updated by dropping the
bar that leaves the window and adding the one that enters, each step.
Kept at window scale rather than a global running sum weighted by the
bar's absolute position, which loses precision at long series lengths --
measured 5.1e-8 by bar 2,500 and 1.4e-6 by bar 3,999 of a 4,000-bar walk
(length 3) vs a plain-OLS oracle, against 1.6e-9 / 7.2e-8 for the
recurrence actually shipped (docs/measure_trend_scan_proxy.py,
"rolling-sum precision").

Calculation:
    Default Inputs:
        horizons=(5, 10, 20, 40, 60)
    z = log(close / first finite positive close)
    for each L: S1 = sum(z), S2 = sum(i*z) (i local, 0..L-1), S3 = sum(z^2)
        over the trailing L-bar window, updated incrementally;
        Sxy = S2 - (L-1)/2*S1; Sxx = L*(L^2-1)/12; Syy = S3 - S1^2/L;
        slope = Sxy / Sxx; t = slope * sqrt(Sxx * (L-2) / (Syy - slope*Sxy))
    TSCAN_T = signed t of the L with the largest |t|
    TSCAN_L = that L

Args:
    close (pd.Series): Series of 'close's
    horizons (Sequence[int]): Trailing windows to scan, each >= 3.
        Default: (5, 10, 20, 40, 60)
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)

Returns:
    pd.DataFrame: TSCAN_T_<horizons>, TSCAN_L_<horizons> columns.
"""
