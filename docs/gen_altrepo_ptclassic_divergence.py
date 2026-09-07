# -*- coding: utf-8 -*-
"""PTCLASSIC-1: name the divergence for every same-name-different-behaviour row.

PTCLASSIC-0 established WHICH rows differ (53 of them). It compared each side at
its OWN defaults, which cannot distinguish "these compute different things" from
"these default to a different window". Shared ancestry makes that distinction
the whole point: a name present in both may have been fixed on one side only,
and the fix is invisible if the two are never run on the same parameters.

⚠ Signature introspection does NOT answer this. Both packages use the pandas_ta
idiom `length=None`, resolved inside the body (`length = int(length) if length
and length > 0 else 14`), so the effective default is not in the signature.
Measured: only 1 of 53 pairs shows a numeric default difference at signature
level. So this probes BEHAVIOUR twice -- once at each side's own defaults (that
is PTCLASSIC-0's result) and once with every shared parameter pinned to the same
explicit value -- and classifies the pair on the difference between those runs.

Classes, in the order they are tested:

  default-only  agrees once shared parameters are pinned -> the maths is the
                same and the DEFAULT differs. Cheapest class: nothing to port,
                but a caller who assumes the other package's default gets a
                different column under the same name.
  shape         different column sets, arity or return type -> not comparable
                elementwise; one side returns more (or less) than the other.
  warmup        identical after the first k bars -> the two differ only in how
                many bars they emit before their window fills. Same maths,
                different warm-up contract.
  seeding       converges to agreement -- a recursive indicator (EMA/RMA and
                anything built on them) seeded differently. Same recurrence,
                different start; differs on early bars only.
  scaling       one output is a constant multiple of the other (0/100 vs 0/1,
                percent vs fraction). A real difference, but a knowable one.
  offset        one output is the other shifted by k bars -> a lag/causality
                difference, which is the class that matters most for an ML
                feature and the one worth reading by hand.
  maths         still differs with parameters pinned, not a scale or a shift.
                The genuine "one of these may carry a fix" bucket.
  unresolved    the pinned-parameter probe could not run.

Writes `../AlternativeRepos/altrepo_ptclassic_divergence.csv`.
Guard: `tests/test_altrepo_ptclassic_divergence_csv.py`.
"""
import csv
import inspect
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
SIBLING = os.path.join(os.path.dirname(FORK), "AlternativeRepos")
CLASSIC = os.path.join(SIBLING, "pandas-ta-classic")
SOURCE_CSV = os.path.join(SIBLING, "altrepo_pandas_ta_classic.csv")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    SIBLING, "altrepo_ptclassic_divergence.csv")

if not os.path.isdir(CLASSIC):
    sys.exit(f"pandas-ta-classic not found at {CLASSIC}")
if not os.path.exists(SOURCE_CSV):
    sys.exit(f"run gen_altrepo_pandas_ta_classic.py first: {SOURCE_CSV} absent")

sys.path.insert(0, CLASSIC)
sys.path.insert(0, FORK)
import numpy as np                                         # noqa: E402
import pandas_ta as ta                                     # noqa: E402
import pandas_ta_classic as tac                            # noqa: E402
from pandas import DataFrame, Series                       # noqa: E402

# Reuse PTCLASSIC-0's harness rather than reimplementing it -- a second copy of
# the probe would drift from the one that produced the verdicts being explained.
sys.path.insert(0, HERE)
from gen_altrepo_pandas_ta_classic import (                # noqa: E402
    NOT_CALLABLE, _call, _probe_frame, _rel, _source_file, _def_line,
)

# Values pinned on BOTH sides when the parameter exists. Chosen as the common
# pandas_ta defaults so the pinned run stays near each package's normal regime;
# the point is that both see the SAME number, not which number it is.
PINNED = {
    "length": 14, "fast": 12, "slow": 26, "signal": 9, "window": 14,
    "period": 14, "k": 14, "d": 3, "smooth_k": 3, "scalar": 100,
    "drift": 1, "offset": 0, "ddof": 0, "std": 2.0, "mamode": "sma",
}
SERIES_PARAMS = {"open", "open_", "high", "low", "close", "volume", "source",
                 "series", "trend"}


def _call_pinned(fn, frame, fn_name):
    """Call `fn` with the probe series AND every shared parameter pinned."""
    base = _call(fn, frame, fn_name)
    if base is NOT_CALLABLE:
        return NOT_CALLABLE
    kwargs = {}
    for pname, param in inspect.signature(fn).parameters.items():
        if pname in SERIES_PARAMS or pname == "kwargs":
            continue
        if pname in PINNED:
            kwargs[pname] = PINNED[pname]
    if not kwargs:
        return base  # nothing to pin; the default run IS the pinned run
    series_kwargs = {}
    for pname in inspect.signature(fn).parameters:
        if pname in SERIES_PARAMS:
            column = {"open_": "open", "open": "open", "high": "high",
                      "low": "low", "close": "close", "volume": "volume",
                      "source": "close", "series": "close",
                      "trend": "close"}[pname]
            series_kwargs[pname] = frame[column]
    if not series_kwargs:
        return NOT_CALLABLE
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        np.seterr(all="ignore")
        try:
            return fn(**series_kwargs, **kwargs)
        except Exception:                                   # noqa: BLE001
            # A pinned value the function rejects (an unsupported mamode, say)
            # is not a finding about the pair -- fall back to its own defaults.
            return base


def _as_array(value):
    if isinstance(value, DataFrame):
        return value.to_numpy(dtype="float64"), list(value.columns)
    if isinstance(value, Series):
        return value.to_numpy(dtype="float64").reshape(-1, 1), [value.name]
    if isinstance(value, tuple):
        parts = [_as_array(v)[0] for v in value if v is not None]
        parts = [p for p in parts if p is not None]
        if not parts:
            return None, []
        return np.hstack(parts), [f"t{i}" for i in range(len(parts))]
    return None, []


def _scaling_factor(a, b):
    """If b == k*a for a single constant k, return k. Else None."""
    mask = ~(np.isnan(a) | np.isnan(b)) & (np.abs(a) > 1e-12)
    if mask.sum() < 10:
        return None
    ratios = b[mask] / a[mask]
    if np.allclose(ratios, ratios[0], rtol=1e-6, atol=1e-9):
        return float(ratios[0])
    return None


def _warmup_bars(a, b, limit=90):
    """Smallest k such that a[k:] and b[k:] agree. None if they never do.

    The first version of this script had no such class and filed 33 pairs as
    `maths`. Most of them showed Pearson r = 1.0000 with a NaN gap -- one side
    emits values through its warm-up window where the other emits NaN, and they
    agree from there on. Calling that "different mathematics" would send someone
    to read two identical formulas.
    """
    n = min(len(a), len(b))
    for k in range(1, min(limit, n - 10)):
        x, y = a[k:n], b[k:n]
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 30:
            continue
        if (np.allclose(x[mask], y[mask], rtol=1e-9, atol=1e-12)
                and not np.isnan(x).any() and not np.isnan(y).any()):
            return k
    return None


def _converges(a, b, tol=1e-6):
    """Do the two agree asymptotically while differing early?

    Recursive indicators (EMA, RMA, and everything built on them) depend on how
    the recursion is SEEDED -- an SMA seed and a first-value seed produce series
    that converge geometrically but never become bit-equal. The strict warm-up
    test cannot see that, so 20+ pairs showing Pearson r = 1.0000 were filed as
    `maths`, which would send a reader to compare two identical formulas.

    Returns the relative error in the final quarter, or None if it never settles.
    """
    mask = ~(np.isnan(a) | np.isnan(b))
    if mask.sum() < 40:
        return None
    x, y = a[mask], b[mask]
    scale = np.maximum(np.abs(x), np.abs(y))
    scale[scale < 1e-12] = 1.0
    rel = np.abs(x - y) / scale
    cut = int(len(rel) * 0.75)
    tail, head = rel[cut:], rel[:cut]
    if tail.size < 10:
        return None
    if tail.max() < tol <= head.max():
        return float(tail.max())
    return None


def _offset_bars(a, b, limit=6):
    """If b is a shifted by k bars (|k| <= limit), return k. Else None."""
    for k in range(1, limit + 1):
        for shifted, sign in ((a[:-k], -k), (a[k:], k)):
            other = b[k:] if sign == -k else b[:-k]
            mask = ~(np.isnan(shifted) | np.isnan(other))
            if mask.sum() >= 30 and np.allclose(shifted[mask], other[mask],
                                                rtol=1e-9, atol=1e-12):
                return sign
    return None


def classify_divergence(name, fork_name, frame):
    """-> (klass, detail). Ordered cheapest-explanation-first."""
    cls_fn, fork_fn = getattr(tac, name, None), getattr(ta, fork_name, None)
    if cls_fn is None or fork_fn is None:
        return "unresolved", "one side is not a module-level function"

    try:
        pinned_cls = _call_pinned(cls_fn, frame, name)
        pinned_fork = _call_pinned(fork_fn, frame, fork_name)
    except Exception as exc:                                # noqa: BLE001
        return "unresolved", f"pinned probe raised {type(exc).__name__}"
    if pinned_cls is NOT_CALLABLE or pinned_fork is NOT_CALLABLE:
        return "unresolved", "pinned probe could not construct a call"
    if pinned_cls is None or pinned_fork is None:
        return "unresolved", "pinned probe returned None on one side"

    a, cols_a = _as_array(pinned_cls)
    b, cols_b = _as_array(pinned_fork)
    if a is None or b is None:
        return "unresolved", "pinned output not array-convertible"

    if a.shape != b.shape:
        return ("shape",
                f"pinned output shape {a.shape} (classic) vs {b.shape} (fork); "
                f"columns {cols_a} vs {cols_b}")

    if np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True):
        return ("default-only",
                "identical once shared parameters are pinned -- same maths, "
                "different DEFAULT. Nothing to port; a caller who assumes the "
                "other package's default gets a different column under the "
                "same name.")

    flat_a, flat_b = a.ravel(), b.ravel()
    factor = _scaling_factor(flat_a, flat_b)
    if factor is not None:
        return ("scaling",
                f"fork output is exactly {factor:.6g}x classic's, elementwise "
                f"-- a units difference (e.g. 0/100 vs 0/1), not a maths one")

    warmup = _warmup_bars(flat_a, flat_b)
    if warmup is not None:
        return ("warmup",
                f"identical from bar {warmup} onward; the two differ only "
                f"through the warm-up window (seeding / how many bars each "
                f"emits before the window fills). Same maths, different "
                f"warm-up contract -- matters for the first {warmup} bars of "
                f"every ticker, and nowhere else.")

    settled = _converges(flat_a, flat_b)
    if settled is not None:
        return ("seeding",
                f"converges: relative error falls to {settled:.2e} in the final "
                f"quarter while differing earlier. A recursive indicator seeded "
                f"differently (SMA seed vs first-value seed) -- same recurrence, "
                f"different start. Affects early bars of every ticker; "
                f"asymptotically identical.")

    shift = _offset_bars(flat_a, flat_b)
    if shift is not None:
        return ("offset",
                f"fork output equals classic's shifted by {shift:+d} bars -- a "
                f"LAG difference. For an ML feature this is the class that "
                f"matters most: one of the two reads a bar the other does not.")

    mask = ~(np.isnan(flat_a) | np.isnan(flat_b))
    if not mask.any():
        return "unresolved", "no overlapping non-NaN values when pinned"
    worst = float(np.nanmax(np.abs(flat_a[mask] - flat_b[mask])))
    corr = (float(np.corrcoef(flat_a[mask], flat_b[mask])[0, 1])
            if mask.sum() > 2 else float("nan"))
    nan_gap = int((np.isnan(flat_a) ^ np.isnan(flat_b)).sum())
    return ("maths",
            f"still differs with parameters pinned: max abs diff {worst:.6g}, "
            f"Pearson r {corr:.4f} over {int(mask.sum())} values, {nan_gap} "
            f"bars NaN on one side only. One of the two may carry a fix the "
            f"other lacks -- READ BOTH BODIES.")


def _environment_stamp():
    """What the verdicts below are conditional on.

    Installing TA-Lib moved `dm` from `port - alternate impl` to `have`: both
    packages defer to TA-Lib when it is importable, so their outputs converge.
    A verdict column is therefore a statement about THIS environment, and a
    regeneration elsewhere can legitimately differ. Recording it turns a silent
    reclassification into a visible one.
    """
    try:
        import talib
        have_talib = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        have_talib = "talib ABSENT"
    import pandas
    return f"{have_talib}; pandas {pandas.__version__}"


def main():
    with open(SOURCE_CSV, encoding="utf8") as fh:
        source = [r for r in csv.DictReader(fh)
                  if r["verdict"] == "port - alternate impl"]
    if not source:
        sys.exit("no `port - alternate impl` rows to explain")

    frame = _probe_frame()
    rows = []
    for row in source:
        name, fork_name = row["name"], row["pandas_ta_equivalent"]
        klass, detail = classify_divergence(name, fork_name, frame)
        fork_file = _source_file(ta, fork_name)
        rows.append({
            "name": name,
            "category": row["category"],
            "pandas_ta_equivalent": fork_name,
            "divergence_class": klass,
            "detail": detail,
            "classic_source": _rel(_source_file(tac, name) or "", CLASSIC),
            "fork_source": (f"{_rel(fork_file, FORK)}:"
                            f"{_def_line(fork_file, fork_name)}"
                            if fork_file else ""),
            "default_run_note": row["note"],
        })

    env = _environment_stamp()
    for r in rows:
        r["probe_env"] = env
    fields = ["name", "category", "pandas_ta_equivalent", "divergence_class",
              "detail", "classic_source", "fork_source", "default_run_note",
              "probe_env"]
    with open(OUT, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    split = Counter(r["divergence_class"] for r in rows)
    print(f"wrote {OUT}  ({len(rows)} rows)")
    for klass, n in split.most_common():
        print(f"  {klass:14} {n:3}")
    hot = [r["name"] for r in rows
           if r["divergence_class"] in ("maths", "offset")]
    print(f"\nneed a human body-read ({len(hot)}): {', '.join(sorted(hot))}")


if __name__ == "__main__":
    main()
