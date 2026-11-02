# Alpha158 gaps — measured (`rank`, `wvma`, `vsumd`)

Three qlib Alpha158 features the fork and the engine did not have, each shipped as a
five-window family (`d` in 5, 10, 20, 30, 60): `RANK$d` (percentile rank of close),
`WVMA$d` (coefficient of variation of the volume-weighted absolute return), `VSUMD$d`
(an RSI-style balance of volume increases vs decreases). Found by reading qlib's
`qlib/contrib/data/loader.py`, `Alpha158DL.get_feature_config` (fetched read-only from
GitHub `main` on 2026-10-24, per the issue). Nothing in the issue was measured; this
document is that measurement. PandasTa issue #34 (A158GAPS), parent #31 ALPHASETS.

**Status: Gates A, B, D cleared (synthetic); Gate C synthetic only (real-data counts
owed); Gate E OWED; verdict pending. Do not merge to `main` before Gate E**: all three
are in `Category`, so any `df.ta.strategy()` sweep in the parent repo picks them up.

**License.** qlib (`microsoft/qlib`) is released under the MIT License — public
knowledge of the project's licensing, not re-verified by a live fetch in this session
(web access was unavailable here). Attributed in each module's docstring. This port is
an independent implementation from the three published formulas quoted in the issue,
not a copy of qlib's source.

Shipped:
- `pandas_ta/statistics/rank.py` — `RANK_5`, `RANK_10`, `RANK_20`, `RANK_30`, `RANK_60`,
  each in (0, 1]. Tests: `tests/test_rank.py` (13).
- `pandas_ta/volatility/wvma.py` — `WVMA_5` .. `WVMA_60`, each >= 0, unbounded above.
  Tests: `tests/test_wvma.py` (18).
- `pandas_ta/volume/vsumd.py` — `VSUMD_5` .. `VSUMD_60`, each in [-1, 1]. Tests:
  `tests/test_vsumd.py` (14).

Environment: pandas 2.x, numpy 1.26.4 (per `pyproject`/CI pins), Python 3.12. Measured
2026-11-02, on synthetic frames generated inside each test module (`_walk`/`_ohlcv`
fixtures) — no real market data is read by this document.

## Design decisions made explicitly (not in the issue)

1. **One Category entry, five columns.** The issue's "each over the Alpha158 windows"
   is read as one indicator call producing all five window columns in one `DataFrame`,
   not five separate calls at five different `length` values — the `trend_scan`/`mmar`
   precedent in this repo (`pandas_ta/statistics/trend_scan.py`,
   `pandas_ta/overlap/mmar.py`). This keeps the "at most 3 new modules" constraint
   satisfiable and matches `df.ta.strategy()`'s behaviour of calling each indicator
   once, at its defaults — a single-`length` design would only ever contribute ONE of
   the five windows to a sweep.
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

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | each module's docstring quotes the issue's qlib expression verbatim; each test module's `test_matches_an_independent_loop` re-derives the formula in a fresh per-bar Python loop (not reusing the module's own vectorised code) and a hand-computed window, both agreeing to the modules' output. |
| B Causality | pass | `tests/test_{rank,wvma,vsumd}.py`: future-perturbation over 31 offsets, two future replacements per offset, plus an `importlib`-read/`exec`'d mutant for each causal path (shift the window one bar forward). `rank`: real module 0/31 leaks, mutant 30/31 (not 31/31 — RANK is a discrete count statistic, only `length`+1 possible values, so a single swapped element can coincidentally leave all 5 columns' counts unchanged at one offset even with two different future replacements tried; a continuous sum/mean/std does not have this coincidence). `wvma` (2 mutants: std, mean) and `vsumd` (1 mutant): both 0/31 real, 31/31 mutant. |
| C Reachability | synthetic only | On a 1,200-bar synthetic walk (each test module's own fixture), warm-up is the only non-firing stretch, but its length differs by module: `rank` reads `close` directly with no shift/diff, so its warm-up is `d - 1` bars (fires = 1200 - (d-1)) — `RANK_5`=1196, `RANK_10`=1191, `RANK_20`=1181, `RANK_30`=1171, `RANK_60`=1141. `wvma`/`vsumd` each burn one extra bar on an internal `close.shift(1)`/`volume.diff()` before any rolling window starts, so their warm-up is `d` bars (fires = 1200 - d) — `wvma`: `WVMA_5`=1195, `WVMA_10`=1190, `WVMA_20`=1180, `WVMA_30`=1170, `WVMA_60`=1140; `vsumd`: `VSUMD_5`=1195, `VSUMD_10`=1190, `VSUMD_20`=1180, `VSUMD_30`=1170, `VSUMD_60`=1140. (The numbers were always right; an earlier revision of this row stated one `d - 1` rule for all three, which contradicted its own `wvma`/`vsumd` figures — caught by `/brutally-honest-review`, fixed here.) All non-constant (`nunique() > 1` for `rank`, `> 100` for `wvma`/`vsumd`). **Real-data counts owed** — Gate E's run supplies them. |
| D Scale-free | pass | `rank`: an order statistic, so invariant to ANY positive rescale of `close`, not merely a power of two — measured bit-identical at x8, x64, x10 AND x3.7 (no ties hit on the test walk). `wvma`: price axis bit-identical at x8/x64 (the `close/close.shift(1)` ratio cancels any common factor exactly before the rest of the formula runs), within 1e-9 at x10/x3.7; volume axis NOT bit-identical even at x8/x64 — measured max\|diff\| 6.66e-16 / 4.44e-16, because the `+1e-12` floor does not commute exactly with a volume rescale (`k*mean + 1e-12` vs `k*(mean + 1e-12/k)`) — within the same 1e-9 bound for all four factors. `vsumd`: volume-only (no price axis); same `+1e-12`-floor non-commutation as `wvma`, measured max\|diff\| ~1.1e-16 at x8/x64, within 1e-9 for all four factors. `0 < fires < n` holds per column for all three (Gate C numbers above). |
| E Attribution | **OWED** | `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module pandas_ta.<category>.<name> --name <name>`, three runs (`rank`, `wvma`, `vsumd`), against `compute_all` ∪ the `ml_features` manifest `1d`, over the 89 frozen ALTPORT-1 BIST frames. **Gate E: pending, run by issue-solver after this session.** Bands (`r3-perframe-0.90`): STRUCK >= 0.90, DISCLOSE_GAP 0.80-0.90, DISCLOSE 0.76-0.80, SHIP < 0.76. The issue's own guess — `RANK` close to `stoch` %K / `Range_Pos_*`, `VSUMD` possibly restating `Volume_Ratio_20` changes, `WVMA` no obvious analogue — is unmeasured and not assumed here. |
| F Suites | this repo only | `python -m pytest -q`: 3 failed, 3968 passed, 83 skipped. All three failures pre-date this change: the documented known break (`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, `CLAUDE.md` "Known breaks"), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout this worktree does not have — the exact test `CLAUDE.md`'s CI section says is deselected by name for that reason), and the expected owed-row failure in `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` for `['rank', 'vsumd', 'wvma']`. None caused by this port. Parent repo's suite is run by the launcher. |

## To close

1. Run Gate E (`gate_e_overlap.py run --module pandas_ta.statistics.rank --name rank`,
   `... .volatility.wvma --name wvma`, `... .volume.vsumd --name vsumd`) and record each
   with `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.
2. Fill Gate C from the same real frames the Gate E run touches.
3. Apply `CLAUDE.md`'s bands per column. A column at or above `STRUCK` is reverted (its
   module, Category entry, accessor, export and tests deleted) unless waived; the
   `DISCLOSE`/`DISCLOSE_GAP`/`SHIP` columns ship as-is. This file's verdict line and the
   receipt session's ledger row carry the result.
4. Regenerate `docs/IndicatorDictionary.md` if any column is reverted (it already
   reflects the as-shipped 15-column state as of this session).
5. Run both repos' suites.
