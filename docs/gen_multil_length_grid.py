# -*- coding: utf-8 -*-
"""MULTIL-0: which second lookback length actually earns a column?

> **Goal (user):** *"We need different time spans for same indicators. RSI 14
> RSI 28, EMA150, EMA50, etc"*

Adding a length is cheap to compute and expensive to justify. `RSI_14` vs
`RSI_28` is a candidate rho ~ 0.9 pair, which is the fork's REVERT band (Gate E:
rho ~ 0.9 revert, 0.76-0.80 ship with disclosure, below 0.76 ship). A length
variant is not exempt from that gate just because it reuses a shipped formula --
the miner double-weights one signal either way.

**Measured on REAL BIST daily data, not the synthetic probe frame.** A
random-walk probe would give a rho between two smoothings of noise, which says
nothing about whether the pair is redundant on the series the engine actually
feeds.

⚠ **The first version of this script claimed Grid A and was not Grid A.** It
`os.listdir`-ed the whole cache (578 files) and took the first 40 in ASCII
order; only 12 of those 40 were BIST_100 constituents and the sample stopped at
the letters "AN". Every rho and every verdict in that CSV was measured on an
alphabetically truncated small-cap cohort under a header claiming otherwise --
a claim written before it was measured, which CLAUDE.md names as this repo's
dominant defect. The universe is now `BIST_100` imported from
`backtesting_engine.config`, iterated exactly as `measure_fvg_overlap_full.py`
does, and the realised ticker list is written into the output.

**Correlations are pooled with Fisher z, not averaged.** Arithmetic means of
Spearman coefficients are biased downward near 1, and it changed verdicts here:
`sma 10/50` 0.8907 -> 0.9338 (REVERT, was "ship with disclosure") and
`ema 50/200` 0.8609 -> 0.9206 (REVERT). Two false all-clears in the first CSV.

**A kept SET, not a list of surviving pairs.** Pairwise verdicts are not
transitive: `rsi` 7/28 and 7/50 both clear while 28/50 reverts at 0.9559, so
`{7,28,50}` looks kept and is not. The kept set is the largest length subset
whose EVERY pairwise pooled rho clears the revert band.

Spearman, not Pearson: these are monotone-but-not-linear relationships, and the
fork's own Gate E precedent (`measure_*_overlap_full.py`) uses Spearman.

Output: `docs/multil_length_grid.csv` -- one row per (indicator, length_a,
length_b) with the pooled rho and the per-frame spread, plus a `verdict` column
applying the Gate E bands.

Usage:  python docs/gen_multil_length_grid.py [out.csv]
"""
import csv
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
CACHE = os.path.join(os.path.dirname(FORK), "Backtesting", "datastore", "cache")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "multil_length_grid.csv")

sys.path.insert(0, FORK)

import numpy as np                                          # noqa: E402
import pandas as pd                                         # noqa: E402
import pandas_ta as ta                                      # noqa: E402
from scipy.stats import spearmanr                           # noqa: E402

# The user named RSI and EMA explicitly; the rest are the shipped scale-free
# families where a second window is plausible. Price-level outputs (EMA, SMA)
# are included because the USER asked for them, and are flagged: a raw MA is a
# dead feature by the fork's own ML contract, so a second one is two dead
# features. The distance form is what would earn a column.
GRID = {
    "rsi": [7, 14, 28, 50],
    "ema": [10, 20, 50, 150, 200],
    "sma": [10, 20, 50, 200],
    "natr": [7, 14, 28],
    "willr": [7, 14, 28],
    "cci": [10, 20, 40],
    "roc": [5, 10, 20],
    "stdev": [10, 20, 40],
    "zscore": [10, 20, 50],
}
PRICE_LEVEL = {"ema", "sma"}          # scale with price: dead as raw features

# `cmo` was in this grid and its three rows came out digit-identical to `rsi`'s.
# That is not coincidence: MEASURED 2026-09-07, this fork's
# `cmo == 2 * rsi - 100` to 2.8e-14, i.e. Spearman 1.0. It is an affine
# reparameterisation of RSI, so the two families must never both be retained --
# and the grid could not see it, because it only ever compares lengths WITHIN
# one indicator while the task says "no retained PAIR". Dropped from the grid;
# the cross-family point is recorded here so it is not re-added.

REVERT = 0.90
DISCLOSE = 0.76

# ⚠ CLAUDE.md's Gate E reads "rho ~ 0.9 revert; 0.76-0.80 ship with disclosure;
# below 0.76 ship" -- it leaves 0.80-0.90 UNALLOCATED. This grid treats
# everything below REVERT as shippable-with-disclosure, i.e. it widens the
# disclosure band by 2.8x. That is a DECISION, stated here rather than buried:
# a length pair at 0.86 is not "fine", it is inside a region the fork's own gate
# never ruled on. `GATE_E_DISCLOSE_MAX` records where the documented band
# actually stops so the CSV can flag the difference.
GATE_E_DISCLOSE_MAX = 0.80


def _frames():
    """The Grid A universe: BIST_100 constituents with >= 400 cached rows.

    Imported from `backtesting_engine.config`, exactly as
    `measure_fvg_overlap_full.py` does, so "Grid A" means the same thing in both
    measurements. Every skip is COUNTED and reported -- the previous version had
    three silent `except: continue` paths and a reader could not tell a dropped
    frame from a missing one.
    """
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(FORK), "Backtesting"))
    from backtesting_engine.config import BIST_100

    skips = {"no_cache_file": [], "unreadable": [], "too_short": [],
             "missing_ohlc": []}
    out = []
    for ticker in BIST_100:
        path = os.path.join(CACHE, ticker.replace(".", "_") + "_1d.parquet")
        if not os.path.exists(path):
            skips["no_cache_file"].append(ticker)
            continue
        try:
            frame = pd.read_parquet(path)
        except (OSError, ValueError):
            skips["unreadable"].append(ticker)
            continue
        if len(frame) < 400:
            skips["too_short"].append(ticker)
            continue
        frame.columns = [c.lower() for c in frame.columns]
        if not {"high", "low", "close"} <= set(frame.columns):
            skips["missing_ohlc"].append(ticker)
            continue
        out.append((ticker, frame))
    return out, skips


def _compute(name, frame, length):
    fn = getattr(ta, name, None)
    if fn is None:
        return None
    import inspect
    params = inspect.signature(fn).parameters
    kwargs = {}
    for pname in params:
        if pname in ("high", "low", "close", "open", "open_", "volume"):
            column = "open" if pname in ("open", "open_") else pname
            if column not in frame.columns:
                return None
            kwargs[pname] = frame[column]
    if not kwargs:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            value = fn(**kwargs, length=length)
    except Exception:                                       # noqa: BLE001
        return None
    if value is None:
        return None
    if hasattr(value, "columns"):
        value = value.iloc[:, 0]
    return pd.Series(np.asarray(value, dtype="float64"), index=frame.index)


def _pool(rhos):
    """Fisher-z pooled Spearman. `np.mean` of correlations is biased near 1."""
    z = np.arctanh(np.clip(np.asarray(rhos, dtype="float64"), -0.999999, 0.999999))
    return float(np.tanh(np.mean(z)))


def _band(rho):
    return ("revert - redundant" if abs(rho) >= REVERT
            else "ship with disclosure" if abs(rho) >= DISCLOSE else "ship")


def _beyond_documented_band(rho):
    """True where this grid is more permissive than CLAUDE.md's Gate E."""
    return GATE_E_DISCLOSE_MAX <= abs(rho) < REVERT


def _kept_set(lengths, pooled, blocked):
    """Largest subset of `lengths` with EVERY pairwise rho under the band.

    A list of surviving PAIRS is not a set: `rsi` 7/28 (0.777) and 7/50 (0.638)
    both clear while 28/50 (0.956) reverts, so {7,28,50} reads as kept and is
    redundant. Brute force -- the candidate sets are at most 5 elements.
    """
    from itertools import combinations

    for size in range(len(lengths), 0, -1):
        # `blocked` carries every pair whose VERDICT reverts, which includes the
        # majority-of-frames rule. Filtering on pooled rho alone reinstated the
        # estimator round 1 called insufficient.
        clean = [subset for subset in combinations(lengths, size)
                 if not any((a, b) in blocked for a, b in combinations(subset, 2))]
        if not clean:
            continue
        # Tie-break on the LEAST redundant surviving set. The first version took
        # `combinations` order and shipped rsi {7,28} (0.777) over {7,50}
        # (0.632) -- equally maximal, materially more redundant.
        scored = sorted(
            (max((abs(pooled.get((a, b), 0.0))
                  for a, b in combinations(subset, 2)), default=0.0), subset)
            for subset in clean)
        best = scored[0]
        ties = [list(sub) for score, sub in scored[1:] if score - best[0] < 1e-9]
        return list(best[1]), ties
    return list(lengths[:1]), []


def main():
    frames, skips = _frames()
    total_skipped = sum(len(v) for v in skips.values())
    print(f"universe: BIST_100 -> {len(frames)} usable frames "
          f"({total_skipped} skipped)", flush=True)
    for reason, names in skips.items():
        if names:
            print(f"    skipped [{reason}] {len(names)}: "
                  f"{', '.join(names[:8])}{' ...' if len(names) > 8 else ''}",
                  flush=True)
    if not frames:
        sys.exit("no usable frames")

    universe_path = os.path.join(HERE, "multil_universe.csv")
    with open(universe_path, "w", encoding="utf8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ticker", "rows", "status"],
                           lineterminator="\n")
        w.writeheader()
        for ticker, frame in frames:
            w.writerow({"ticker": ticker, "rows": len(frame), "status": "used"})
        for reason, names in skips.items():
            for ticker in names:
                w.writerow({"ticker": ticker, "rows": "", "status": reason})
    print(f"wrote {universe_path} -- the realised ticker list", flush=True)

    rows, pooled_by_ind = [], {}
    for name, lengths in GRID.items():
        pooled_by_ind[name] = {}
        for i, a in enumerate(lengths):
            for b in lengths[i + 1:]:
                rhos, dropped = [], 0
                for _, frame in frames:
                    sa, sb = _compute(name, frame, a), _compute(name, frame, b)
                    if sa is None or sb is None:
                        dropped += 1
                        continue
                    mask = ~(sa.isna() | sb.isna())
                    if mask.sum() < 100:
                        dropped += 1
                        continue
                    rho = spearmanr(sa[mask], sb[mask]).statistic
                    if np.isnan(rho):
                        dropped += 1
                        continue
                    rhos.append(rho)
                if not rhos:
                    print(f"  !! {name} {a}/{b}: no usable frames "
                          f"({dropped} dropped)", flush=True)
                    continue
                pooled = _pool(rhos)
                pooled_by_ind[name][(a, b)] = pooled
                arr = np.asarray(rhos)
                above = int((np.abs(arr) >= REVERT).sum())
                verdict = _band(pooled)
                # A pair redundant on most of the universe is redundant, whatever
                # the pooled number says. The first CSV labelled `sma 20/50`
                # shippable while it breached the band on 31 of 40 frames.
                if verdict != "revert - redundant" and above > len(arr) / 2:
                    verdict = "revert - redundant (majority of frames)"
                rows.append({
                    "indicator": name, "length_a": a, "length_b": b,
                    "ratio": round(b / a, 2),
                    "spearman_z_pooled": round(pooled, 4),
                    "spearman_mean_arith": round(float(np.mean(arr)), 4),
                    "spearman_p25": round(float(np.percentile(arr, 25)), 4),
                    "spearman_p75": round(float(np.percentile(arr, 75)), 4),
                    "frames": len(arr), "frames_dropped": dropped,
                    "frames_above_revert": above,
                    "pct_above_revert": round(100.0 * above / len(arr), 1),
                    "verdict": verdict,
                    "price_level": str(name in PRICE_LEVEL),
                    "beyond_documented_gate_e": str(_beyond_documented_band(pooled)),
                    "note": ("raw output scales with price -- a dead ML feature "
                             "by the fork's contract, so a second length is a "
                             "second dead feature; the distance form is what "
                             "would earn a column"
                             if name in PRICE_LEVEL else ""),
                })
                print(f"  {name:8} {a:>3}/{b:<3} z={pooled:+.4f} "
                      f"arith={np.mean(arr):+.4f} above={above}/{len(arr)} "
                      f"-> {verdict}", flush=True)

    fields = ["indicator", "length_a", "length_b", "ratio",
              "spearman_z_pooled", "spearman_mean_arith", "spearman_p25",
              "spearman_p75", "frames", "frames_dropped",
              "frames_above_revert", "pct_above_revert", "verdict",
              "price_level", "beyond_documented_gate_e", "note"]
    with open(OUT, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    # ---- the kept set, which is the half of the deliverable that was missing
    kept_path = os.path.join(HERE, "multil_kept_set.csv")
    kept_rows = []
    for name, lengths in GRID.items():
        pooled = pooled_by_ind.get(name, {})
        if not pooled:
            continue
        blocked = {(int(r["length_a"]), int(r["length_b"]))
                   for r in rows
                   if r["indicator"] == name and r["verdict"].startswith("revert")}
        kept, ties = _kept_set(lengths, pooled, blocked)
        rejected = [l for l in lengths if l not in kept]
        binding = {}
        for l in rejected:
            worst = max(((abs(v), k) for k, v in pooled.items() if l in k),
                        default=(0, None))
            binding[l] = worst
        kept_rows.append({
            "indicator": name, "candidates": " ".join(map(str, lengths)),
            "kept": " ".join(map(str, kept)),
            "rejected": " ".join(map(str, rejected)),
            "binding_pair": "; ".join(
                f"{l}: {b[1][0]}/{b[1][1]} rho={b[0]:.4f}"
                for l, b in binding.items() if b[1]),
            "price_level": str(name in PRICE_LEVEL),
            "equally_maximal_alternatives": " | ".join(
                " ".join(map(str, t)) for t in ties),
        })
    with open(kept_path, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["indicator", "candidates", "kept", "rejected",
                            "binding_pair", "price_level",
                            "equally_maximal_alternatives"],
            lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept_rows)

    from collections import Counter
    print(f"\nwrote {OUT} ({len(rows)} pairs)")
    for verdict, n in Counter(r["verdict"] for r in rows).most_common():
        print(f"  {verdict:38} {n:3}")
    print(f"\nwrote {kept_path} -- the KEPT SET (every pairwise rho clears "
          f"{REVERT}):")
    for r in kept_rows:
        print(f"  {r['indicator']:8} candidates [{r['candidates']}] -> keep "
              f"[{r['kept']}]" + (f"  (dropped {r['rejected']})"
                                  if r['rejected'] else ""))


if __name__ == "__main__":
    main()
