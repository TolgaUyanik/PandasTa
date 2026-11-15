# -*- coding: utf-8 -*-
"""Reproduce the numbers in docs/EdgeMeasured.md.

    python docs/measure_edge.py [REF_DIR]

Run from the repo root. REF_DIR, if given, holds eguidotti/bidask's
`pseudocode/ohlc.csv` and `ohlc-miss.csv` (commit 1caba55; 0.6 MB each, not
committed here); without it the Gate A section is skipped. The CSVs are read
as data. The reference's code is not run: the comparison uses
tests/test_edge.py's own transcription `_oracle`.
"""
import os
import sys
import time
import tracemalloc

import numpy as np
import pandas as pd

sys.path.insert(0, os.getcwd())
import tests.test_edge as T  # noqa: E402

E = T._REAL


def signed_s2(o, h, l, c, length):
    """The module's own s2, before the unsigned fold (same arithmetic as
    `_edge_rows`, returning s2)."""
    cols = E._pairs(E._prices(o), E._prices(h), E._prices(l), E._prices(c))
    r1, r2, r3, r4, r5, tau, po1, po2, pc1, pc2 = (
        np.lib.stride_tricks.sliding_window_view(x, length - 1) for x in cols)
    with np.errstate(all="ignore"):
        pt = tau.mean(1)
        po = po1.mean(1) + po2.mean(1)
        pc = pc1.mean(1) + pc2.mean(1)
        d1 = r1 - (r1.mean(1) / pt)[:, None] * tau
        d3 = r3 - (r3.mean(1) / pt)[:, None] * tau
        d5 = r5 - (r5.mean(1) / pt)[:, None] * tau
        a1, a2 = (-4 / po)[:, None], (-4 / pc)[:, None]
        x1 = a1 * d1 * r2 + a2 * d3 * r4
        x2 = a1 * d1 * r5 + a2 * d5 * r4
        e1, e2 = x1.mean(1), x2.mean(1)
        v1, v2 = (x1 ** 2).mean(1) - e1 ** 2, (x2 ** 2).mean(1) - e2 ** 2
        vt = v1 + v2
        return np.where(vt > 0, (v2 * e1 + v1 * e2) / vt, (e1 + e2) / 2)


def gate_a(ref_dir):
    print("== Gate A: reference data ==")
    df = pd.read_csv(os.path.join(ref_dir, "ohlc.csv"))
    dm = pd.read_csv(os.path.join(ref_dir, "ohlc-miss.csv"))
    full = T.edge(df.Open, df.High, df.Low, df.Close, length=len(df)).iloc[-1]
    print(f"ohlc.csv, all rows: {full!r}; published 0.0101849034905478; rel {abs(full / 0.0101849034905478 - 1):.2e}")
    for w in (3, 21, 252):
        for name, d in (("ohlc", df), ("ohlc-miss", dm)):
            ours = T.edge(d.Open, d.High, d.Low, d.Close, length=w).to_numpy()
            cols = [d[k].to_numpy() for k in ("Open", "High", "Low", "Close")]
            ref = np.full(len(d), np.nan)
            for t in range(w - 1, len(d)):
                win = [x[t - w + 1:t + 1] for x in cols]
                used = np.concatenate([win[0][1:], win[1], win[2], win[3][:-1]])
                if not np.isnan(used).any():
                    ref[t] = T._oracle(*win)
            m = ~np.isnan(ours) & ~np.isnan(ref)
            rel = np.max(np.abs(ours[m] / ref[m] - 1)) if m.any() else float("nan")
            print(f"  length {w} {name}: NaN {np.isnan(ours).sum()} (oracle {np.isnan(ref).sum()}), "
                  f"max rel {rel:.2e} over {m.sum()} bars")
    for a, b in (("Open", "High"), ("Open", "Low"), ("High", "Low")):
        x, y = df[a].to_numpy(), df[b].to_numpy()
        near = np.abs(x - y) <= E.TIE_RTOL * np.maximum(np.abs(x), np.abs(y))
        print(f"  ties {a}={b}: exact {int((x == y).sum())}, rtol {int(near.sum())}")


def semantics():
    print("== semantics: tests/test_edge.py::_sim, 1000 days, seed 7 ==")
    print("| true spread | sigma | length | EDGE median | share s2 < 0 | signed median |")
    rows = [(0.0, s, L) for s in (0.01, 0.02, 0.04) for L in (21, 63, 252)]
    rows += [(sp, 0.02, 21) for sp in (0.002, 0.005, 0.01, 0.02, 0.05)] + [(0.01, 0.02, 63), (0.01, 0.02, 252)]
    for spread, sigma, L in rows:
        o, h, l, c = T._sim(n=1000, spread=spread, sigma=sigma, seed=7)
        s2 = signed_s2(o, h, l, c, L)
        print(f"| {spread} | {sigma} | {L} | {T.edge(o, h, l, c, length=L).median():.5f} | "
              f"{np.mean(s2 < 0):.3f} | {np.median(np.sign(s2) * np.sqrt(np.abs(s2))):+.5f} |")
    rng = np.random.default_rng(9)
    for spread, seed0 in ((0.0, 200), (0.01, 300)):
        parts = [T._sim(n=250, spread=spread, sigma=float(sg), seed=seed0 + k)
                 for k, sg in enumerate(rng.uniform(0.01, 0.04, 8))]
        o, h, l, c = (pd.concat([p[i] for p in parts], ignore_index=True) for i in range(4))
        rv = np.log(c).diff().rolling(21).std()
        rho = T.edge(o, h, l, c).corr(rv, method="spearman")
        print(f"Spearman(EDGE_21, 21-bar realised vol), spread {spread}, 8 regimes x 250 days: {rho:.4f}")


def cost():
    print("== cost ==")
    for n, seed in ((20000, 5), (200000, 6)):
        o, h, l, c = T._sim(n=n, seed=seed)
        for L in (21, 252):
            tracemalloc.start()
            t0 = time.perf_counter()
            T.edge(o, h, l, c, length=L)
            dt = time.perf_counter() - t0
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            print(f"n={n} length={L}: {dt:.3f} s, peak {peak / 2 ** 20:.0f} MiB (tracemalloc)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        gate_a(sys.argv[1])
    semantics()
    cost()
    print("python", sys.version.split()[0], "pandas", pd.__version__, "numpy", np.__version__)
