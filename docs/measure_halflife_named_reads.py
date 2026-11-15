# -*- coding: utf-8 -*-
"""HLIFE-3's pre-registered reads (docs/HalfLifeMeasured.md): pooled Spearman of HLIFE_100
against the comparators issue #4 names, on the Gate E comparator cache.

Those columns are outside the Gate E run's top 25, so the run's outputs do not hold them.
This uses the harness's own `assemble_frame`, `_pool` and `pair_rho`, so the pairing and
NaN handling are the run's. `ADX` is printed first as a check: the run measured it at
0.420861, n = 359,496.

Needs the owner's Backtesting checkout with a built cache. Run from its `Backtesting/`
folder, with this repo on PYTHONPATH:

    PYTHONPATH=<this repo> python <this repo>/docs/measure_halflife_named_reads.py [BACKTESTING_DIR]
"""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
BT = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
sys.path.insert(0, str(BT / 'scripts' / 'analysis'))
sys.path.insert(0, str(BT))
import pandas as pd                                    # noqa: E402
import gate_e_overlap as G                             # noqa: E402
from backtesting_engine import gate_e as GE            # noqa: E402

NAMED = ['natr', 'natr_percentile', 'ZSCORE_20', 'BB_BWidth', 'LINREG_SLOPE', 'LINREG_VALUE',
         'LINREG_DEV', 'LINREG_UPPER_1', 'LINREG_LOWER_1', 'LINREG_UPPER_2', 'LINREG_LOWER_2']


def main() -> None:
    func = G._resolve('pandas_ta.statistics.halflife')
    frames = {}
    for t in G.UNIVERSE:
        f, cols = G.assemble_frame(pd.read_parquet(G.WORK / f'{G._safe(t)}.parquet'), func, {})
        frames[t] = f[cols + ['ADX'] + NAMED]
    cand = cols[0]
    pooled = GE._pool(frames, [cand, 'ADX'] + NAMED)
    print(f"candidate {cand}, frames {len(frames)}, pooled bars {len(pooled[cand]):,}")
    for c in ['ADX'] + NAMED:
        rho, n, why = GE.pair_rho(pooled[cand].astype('float64'), pooled[c].astype('float64'))
        print(f"{c:16s} rho {rho:+.6f}  |rho| {abs(rho):.4f}  n {n:,} {why}")


if __name__ == '__main__':
    main()
