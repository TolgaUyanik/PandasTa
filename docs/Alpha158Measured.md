# Alpha158 gaps — measured (`rank`, `wvma`, `vsumd`)

Three qlib Alpha158 features the fork and the engine did not have, each originally shipped
as a five-window family (`d` in 5, 10, 20, 30, 60): `RANK$d` (percentile rank of close),
`WVMA$d` (coefficient of variation of the volume-weighted absolute return), `VSUMD$d`
(an RSI-style balance of volume increases vs decreases). Found by reading qlib's
`qlib/contrib/data/loader.py`, `Alpha158DL.get_feature_config` (fetched read-only from
GitHub `main` on 2026-10-24, per the issue). Nothing in the issue was measured; this
document is that measurement. PandasTa issue #34 (A158GAPS), parent #31 ALPHASETS.

**Status: measured revert on `rank`; `wvma` and `vsumd` ship unchanged.** Gate E (89
frozen ALTPORT-1 BIST frames, `compute_all` ∪ `ml_features` manifest `1d`, 687
comparators, `r3-perframe-0.90` bands) STRUCK three of `rank`'s five columns
(`RANK_20`, `RANK_30`, `RANK_60`); they are removed. `RANK_5`/`RANK_10` ship at
DISCLOSE_GAP. All ten `wvma`/`vsumd` columns SHIP. `rank`, `wvma` and `vsumd` all stay
in `Category`.

**License.** qlib (`microsoft/qlib`) is released under the MIT License — public
knowledge of the project's licensing, not re-verified by a live fetch in this session
(web access was unavailable here). Attributed in each module's docstring. This port is
an independent implementation from the three published formulas quoted in the issue,
not a copy of qlib's source.

Shipped:
- `pandas_ta/statistics/rank.py` — `RANK_5`, `RANK_10`, each in (0, 1]. `RANK_20`,
  `RANK_30`, `RANK_60` were ported, Gate E STRUCK, and removed (see below); calling
  `rank(close, lengths=[20])` etc. now raises `ValueError`. Tests: `tests/test_rank.py`
  (16, up from 13 before the revert: +3 from the struck-lengths-are-refused
  parametrize).
- `pandas_ta/volatility/wvma.py` — `WVMA_5` .. `WVMA_60`, each >= 0, unbounded above,
  all five SHIP. Tests: `tests/test_wvma.py` (18).
- `pandas_ta/volume/vsumd.py` — `VSUMD_5` .. `VSUMD_60`, each in [-1, 1], all five SHIP.
  Tests: `tests/test_vsumd.py` (14).

Environment: pandas 2.3.3, numpy 1.26.4, Python 3.12 (per the Gate E run's `meta.json`
`stamp.versions`). Gates A/B/D/C-synthetic measured 2026-11-02 on synthetic frames
generated inside each test module (`_walk`/`_ohlcv` fixtures). Gate E measured
2026-11-02 by the launcher (`gate_e_overlap.py`), runs `is34-rank-c103a309`,
`is34-wvma-c103a309`, `is34-vsumd-c103a309`, recorded in `docs/gate_e_ledger.csv`.

## Design decisions made explicitly (not in the issue)

1. **One Category entry per indicator, one column per surviving window.** The issue's
   "each over the Alpha158 windows" is read as one indicator call producing all window
   columns in one `DataFrame`, not one call per `length` — the `trend_scan`/`mmar`
   precedent in this repo (`pandas_ta/statistics/trend_scan.py`,
   `pandas_ta/overlap/mmar.py`). This keeps the "at most 3 new modules" constraint
   satisfiable and matches `df.ta.strategy()`'s behaviour of calling each indicator
   once, at its defaults.
2. **Categories: `rank` → statistics, `wvma` → volatility, `vsumd` → volume.** `RANK`
   is a rolling order statistic of `close` alone, the same shape as
   `pandas_ta/statistics/quantile.py`. `VSUMD` reads only `volume`, the same shape as
   `pandas_ta/volume/volcv.py`. `WVMA` reads both; it is categorised with the
   dispersion-ratio indicators (`volvol`) rather than with volume, a judgment call
   documented in the module's own docstring (precedent for either exists in this fork:
   `amihud`/`cmf`/`mfi` are volume+price in `volume`, `volvol`/`cvi` are price-based
   dispersion ratios in `volatility`).
3. **`VSUMD` implemented from qlib's two-sum form, not the telescoped identity.**
   `Sum(Greater(dv,0),d) - Sum(Greater(-dv,0),d)` telescopes algebraically to
   `Sum(dv,d) = volume[t] - volume[t-d]`, but the module computes the two rolling sums
   directly so it stays line-by-line checkable against the published expression;
   `tests/test_vsumd.py::test_telescoping_identity` checks the two forms agree.
4. **A STRUCK length is refused, not merely dropped from the default.** `rank.py`'s
   `STRUCK_LENGTHS = (20, 30, 60)` makes `rank(close, lengths=[20])` raise `ValueError`
   rather than silently reproducing a column Gate E already measured as redundant —
   the same reasoning as `ewmac`'s hardcoded `PAIRS` after its own partial revert
   (issue #29, `docs/EwmacMeasured.md`), adapted to `rank`'s user-configurable
   `lengths` parameter.

## Gate E — measured, bands applied

Harness: `gate_e_overlap.py run --module pandas_ta.<category>.<name>`, `compute_all`
(329 cols) ∪ `ml_features` manifest `1d` (358 cols) = 687 comparators, 89 frozen
ALTPORT-1 BIST frames, bands `r3-perframe-0.90`. Three runs, recorded 2026-11-02.

### `rank` (run `is34-rank-c103a309`)

| column | pooled max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `RANK_5` | 0.8895 | `Dist_to_FWMA_pct` | 397,692 | 0.8940 | DISCLOSE_GAP |
| `RANK_10` | 0.8786 | `Dist_to_FWMA_pct` | 397,692 | 0.8807 | DISCLOSE_GAP |
| `RANK_20` | 0.9767 | `BB_%B` | 397,158 | 0.9770 | **STRUCK** |
| `RANK_30` | 0.9788 | `zscore` | 396,268 | 0.9789 | **STRUCK** |
| `RANK_60` | 0.9403 | `Range_Pos_60` | 393,598 | 0.9459 | **STRUCK** |

**Decision: revert `RANK_20`, `RANK_30`, `RANK_60`; ship `RANK_5` and `RANK_10` only.**
No waiver exists or was requested (`ALLOWED_WAIVERS` in `tests/test_gate_e_ledger.py`
covers only `pfe` and `kalman_trend`'s pre-ledger columns) — a STRUCK column without a
waiver is reverted per CLAUDE.md's Gate E row and
`tests/test_gate_e_ledger.py::test_struck_rows_carry_the_waiver_for_this_exact_measurement`.
The issue's own guess — `RANK` close to `stoch` %K / `Range_Pos_*` — was right in
direction for `RANK_60` (`Range_Pos_60`, STRUCK) but the two surviving columns'
nearest comparator turned out to be `Dist_to_FWMA_pct`, not `stoch`.

`docs/gate_e_ledger.csv`'s three STRUCK `rank` rows were dropped and the two surviving
rows' `module_sha1` resynced by `docs/measure_rank_ledger_fix.py` (the same pattern as
`docs/measure_ewmac_ledger_fix.py` for issue #29): `RANK_5`/`RANK_10`'s measured numbers
stay valid because reverting the other three lengths does not change either surviving
column's computed values (each length is independent in the `lengths`-keyed dict
comprehension) — only the file's unrelated bytes (comments, `DEFAULT_LENGTHS`,
`STRUCK_LENGTHS`, the length-rejection check) changed underneath the already-recorded
sha1. A future Gate E re-run on this post-revert tree would record a fresh row; until
then the two surviving rows describe the current file correctly by direct recomputation,
not by a new harness run.

### `wvma` (run `is34-wvma-c103a309`)

| column | pooled max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `WVMA_5` | 0.2007 | `mad` | 396,268 | 0.1722 | SHIP |
| `WVMA_10` | 0.2470 | `efi_norm` | 397,771 | 0.2403 | SHIP |
| `WVMA_20` | 0.2976 | `ZIGZAG` | 33,594 | 0.2954 | SHIP |
| `WVMA_30` | 0.3135 | `ZIGZAG` | 33,514 | 0.2955 | SHIP |
| `WVMA_60` | 0.3619 | `ZIGZAG` | 33,246 | 0.3517 | SHIP |

**Decision: all five ship unchanged.** The issue's guess ("no obvious shipped
analogue") holds — nothing approaches DISCLOSE (0.76), let alone STRUCK.

### `vsumd` (run `is34-vsumd-c103a309`)

| column | pooled max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `VSUMD_5` | 0.6708 | `Volume_Ratio_20_Pctl` | 392,787 | 0.6723 | SHIP |
| `VSUMD_10` | 0.7256 | `Volume_Ratio_20_Pctl` | 392,787 | 0.7278 | SHIP |
| `VSUMD_20` | 0.6436 | `Volume_Ratio_20_Pctl` | 392,787 | 0.6472 | SHIP |
| `VSUMD_30` | 0.6064 | `pvo_PVO_12_26_9_Pctl` | 391,373 | 0.6218 | SHIP |
| `VSUMD_60` | 0.6704 | `Volume_Pctl` | 393,509 | 0.6737 | SHIP |

**Decision: all five ship unchanged.** The issue's guess ("may restate
`Volume_Ratio_20` changes") is directionally right — `Volume_Ratio_20_Pctl` is the
nearest comparator for 3 of 5 columns — but none clears even DISCLOSE (0.76).

## Gate C — real-data reachability (from the Gate E runs)

Not synthetic-only anymore: each run's own `non_nan` / `non_zero` fields (pooled over
the 89 BIST frames, `pooled_bars` = 398,849 per frame-set) give real counts.

| column | non_nan | non_zero | column | non_nan | non_zero | column | non_nan | non_zero |
|---|---|---|---|---|---|---|---|---|
| `RANK_5` | 398,493 | 398,493 | `WVMA_5` | 398,404 | 386,843 | `VSUMD_5` | 398,404 | 398,132 |
| `RANK_10` | 398,048 | 398,048 | `WVMA_10` | 397,959 | 381,775 | `VSUMD_10` | 397,959 | 397,822 |
| `RANK_20`\* | 397,158 | 397,158 | `WVMA_20` | 397,069 | 396,834 | `VSUMD_20` | 397,069 | 396,964 |
| `RANK_30`\* | 396,268 | 396,268 | `WVMA_30` | 396,179 | 385,672 | `VSUMD_30` | 396,179 | 396,085 |
| `RANK_60`\* | 393,598 | 393,598 | `WVMA_60` | 393,509 | 378,150 | `VSUMD_60` | 393,509 | 393,416 |

\* `RANK_20`/`RANK_30`/`RANK_60` fired on real data too (non-zero on every non-NaN bar,
since RANK is a count statistic that is zero only if every window value exceeds the
current close, vanishingly rare) — Gate C never objected to them; Gate E's redundancy
finding is why they were removed, not a reachability failure.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | each module's docstring quotes the issue's qlib expression verbatim; each test module's `test_matches_an_independent_loop` re-derives the formula in a fresh per-bar Python loop (not reusing the module's own vectorised code) and a hand-computed window, both agreeing to the modules' output. |
| B Causality | pass | `tests/test_{rank,wvma,vsumd}.py`: future-perturbation over 31 offsets, two future replacements per offset, plus an `importlib`-read/`exec`'d mutant for each causal path (shift the window one bar forward). `rank`: real module 0/31 leaks, mutant 28/31 post-revert (measured 30/31 pre-revert with 5 columns; 28/31 with the 2 surviving columns — RANK is a discrete count statistic, only `length`+1 possible values, so a single swapped element can coincidentally leave all surviving columns' counts unchanged at one offset even with two different future replacements tried; fewer columns makes this slightly more likely, which is why the number moved). `wvma` (2 mutants: std, mean) and `vsumd` (1 mutant): both 0/31 real, 31/31 mutant, unaffected by `rank`'s revert. |
| C Reachability | real data (from the Gate E runs) | See table above. All columns non-zero on a large majority of pooled bars; `0 < fires < n` per column holds on real data for all surviving and even all reverted columns. |
| D Scale-free | pass | `rank`: an order statistic, so invariant to ANY positive rescale of `close`, not merely a power of two — measured bit-identical at x8, x64, x10 AND x3.7 (no ties hit on the test walk); unaffected by the revert (`RANK_5`/`RANK_10`'s code did not change). `wvma`: price axis bit-identical at x8/x64 (the `close/close.shift(1)` ratio cancels any common factor exactly before the rest of the formula runs), within 1e-9 at x10/x3.7; volume axis NOT bit-identical even at x8/x64 — measured max\|diff\| 6.66e-16 / 4.44e-16, because the `+1e-12` floor does not commute exactly with a volume rescale (`k*mean + 1e-12` vs `k*(mean + 1e-12/k)`) — within the same 1e-9 bound for all four factors. `vsumd`: volume-only (no price axis); same `+1e-12`-floor non-commutation as `wvma`, measured max\|diff\| ~1.1e-16 at x8/x64, within 1e-9 for all four factors. `0 < fires < n` holds per column for all three (Gate C numbers above). |
| E Attribution | **measured, three `rank` columns STRUCK and reverted, all `wvma`/`vsumd` SHIP** | see the Gate E tables above; `is34-rank-c103a309`, `is34-wvma-c103a309`, `is34-vsumd-c103a309`, recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only | `python -m pytest -q`: 2 failed, 4047 passed, 83 skipped. Both failures pre-date this change and are named in `CLAUDE.md`'s *Known breaks*: `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (`docs/pine/` untracked) and `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout this worktree does not have). `tests/test_gate_e_ledger.py` is fully green: all 12 surviving ledger rows (`RANK_5`, `RANK_10`, five `WVMA_*`, five `VSUMD_*`) correctly describe the current tree -- `rank`'s two rows were resynced to the post-revert file, `wvma`/`vsumd`'s five each are untouched by the revert. Parent repo's suite is run by the launcher. |

## Closed

1. ~~Run Gate E~~ — done by the launcher, three runs, recorded above.
2. ~~Fill Gate C from the same real frames~~ — done, table above.
3. ~~Apply `CLAUDE.md`'s bands per column~~ — done: `RANK_20`/`RANK_30`/`RANK_60`
   reverted (code, tests, ledger rows); `RANK_5`/`RANK_10`/all `wvma`/all `vsumd` ship.
4. ~~Regenerate `docs/IndicatorDictionary.md`~~ — done, reflects the as-shipped
   12-column state (`RANK_5`, `RANK_10`, `WVMA_5..60`, `VSUMD_5..60`).
5. Both repos' suites: this repo's `python -m pytest -q` is run and reported above;
   the parent repo's suite is run by the launcher, not this session.
