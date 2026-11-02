# lot_zeroret_60 — measured (issue #39)

> **Status: Gates A-E cleared. Gate E: SHIP (max |ρ| 0.7108 vs ZIGZAG).** Gate F (both
> repos' suites) is run by the launcher in clean worktrees; `python -m pytest -q` in this
> worktree is reported below for the record.

Share of zero-return days (60), per issue #39: Lesmond, Ogden & Trzcinka (1999, RFS) use
the proportion of zero daily returns over a trailing window as a published liquidity
proxy; OSAP's `zerotrade` (zero-*volume* days, US t-stat 4.40 at 12 months) is the issue's
named volume-side analogue, used here as zero *returns* instead because this fork's
harness drops zero-volume bars as flat bars before any indicator sees them. Module
`pandas_ta/statistics/lot_zeroret_60.py`, column `LOT_ZERORET_60`. Tests:
`tests/test_lot_zeroret_60.py` (16, all passing). Numbers below: `python
docs/measure_lot_zeroret_60.py`. Environment: this worktree's pinned pandas/numpy
(pandas 2.3.3). Measured 2026-11-02.

## Gate A: the issue states the formula itself — no derivation needed, only one masking detail

Unlike `osap_mrrev` #37 or `osap_voltrend_60` #38, where the issue gave only a
plain-language description that had to be turned into a formula, issue #39 states the
formula verbatim: `count(r == 0, 60)/60`. Neither the Lesmond-Ogden-Trzcinka (1999) paper
nor OSAP's GPL-2.0 `zerotrade` replication code is consulted or available in this
worktree (`docs/pine/` and web access are unavailable); this is ported from the issue's
own stated formula, not from either paper's or OSAP's code. Implemented literally:

1. **`r`** — the plain daily simple return, `close.pct_change()`. This is the same
   return definition already shipped by this repo's own `osap_retskew_21` #36 and
   `osap_mrrev` #37.
2. **`count(r == 0, 60)`** — a rolling 60-bar sum of the boolean `r == 0`. The prototype
   (`docs/issues/screen/ind_screen.py:54`, `count(cond, n) = cond.astype(float).rolling(n).sum()`)
   was read for one thing only — confirming this is a plain rolling sum of the boolean,
   not some other windowed-count operator — not as the source of the formula itself,
   which the issue already states directly.
3. **Masking the undefined-return bar.** `r == 0` evaluates to `False`, not `NaN`, at
   the series' first bar (`close.shift(1)` is `NaN` there, so the comparison is simply
   false) — a plain rolling sum would therefore silently count that undefined bar as
   "not a zero return" instead of excluding the window entirely. The prototype masks
   this with `.where(r.shift(59).notna())`
   (`docs/issues/screen/ind_screen.py:810`); this port generalises the same mask to
   `r.shift(length - 1).notna()`. Without it, the column's first non-NaN bar would be
   one bar too early and would rest on an undefined return being miscounted as a real
   non-zero one.

```
LOT_ZERORET_60 = count(r == 0, 60) / 60, r = close.pct_change()
```

Hand-derived example (`length=3`, the smallest window the mask allows): closes
`[100, 100, 100, 103, 103]` → returns `[NaN, 0, 0, 0.03, 0]`.
- bar 2 (window `r[0:3]` = `[NaN, 0, 0]`): the window's earliest return (`r[0]`) is
  `NaN`, so masked to `NaN` even though the raw rolling sum would read `2/3` (both
  `False`-or-`True` zero bars — `r[0]==0` reads `False`, `r[1]==0` and `r[2]==0` read
  `True` — giving a raw, unmasked `2/3`).
- bar 3 (window `r[1:4]` = `[0, 0, 0.03]`): earliest return `r[1]=0` is defined, so
  the bar fires: `count = 2` (two zeros), `LOT_ZERORET = 2/3`.
- bar 4 (window `r[2:5]` = `[0, 0.03, 0]`): earliest return `r[2]=0` is defined, fires:
  `count = 2`, `LOT_ZERORET = 2/3`.

Matched by `docs/measure_lot_zeroret_60.py` and `tests/test_lot_zeroret_60.py::test_hand_derived_value`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (issue's own stated formula, `count(r==0,60)/60`; primary paper and OSAP code unavailable — see above) | Hand-derived 5-bar example at `length=3` (closes `[100,100,100,103,103]`): bars read `NaN, 2/3, 2/3` exactly, including the masked bar that a plain rolling sum would have mis-fired. Independent per-bar loop (written from the formula, not from the module) at 4 spot-checked bars on a 1,600-bar synthetic walk with forced exact-tie bars, matched exactly |
| B Causality | pass | Future-perturbation sweep, 28 offsets, on a deterministic series with a forced tie every 4th bar (`_ticky`) spliced with a tie-free tail (`_tickless`) past each offset — dense enough that a window reaching into the future reliably changes its own zero-count: real module **0 of 28** leaks. One look-ahead mutant (`importlib` source read, the rolling sum's window switched from trailing to `center=True` — reads future bars — `exec`'d in memory) shown live (differs from the real module), then caught at **28 of 28**. (A first attempt using a plain sparse random walk caught only 3 of 28, pinned by `tests/test_lot_zeroret_60.py::test_a_sparse_random_walk_is_too_weak_a_causality_check` — zero-return events are rare by chance, so most perturbed windows carried the same zero-count in both arms by luck, not by causality; the dense `_ticky`/`_tickless` pair fixes that, see the comment in `docs/measure_lot_zeroret_60.py`.) |
| C Reachability | 1,540 of 1,600 bars non-NaN (96.25%), exactly `n - length` — the 60-bar warm-up and nothing wider. 3 distinct values among the 1,540 (`0`, `1/60`, `2/60`) on this synthetic walk with 6 forced ties; range [0, 0.033333], median 0, 242 bars with a positive share. The small distinct-value count is a structural property of a bounded count statistic (at most `length + 1` possible values exist at all, system-wide), not evidence of a near-constant column — real-data reachability and variety come from Gate E's pooled measurement, not re-derived here | `python docs/measure_lot_zeroret_60.py` |
| D Scale-free | pass | `r == 0` reduces to `close[t] == close[t-1]` (dividing an equal nonzero float by itself is always exactly `1.0` under IEEE-754, so the subtraction gives exactly `0.0`), and multiplying two equal float values by the same scalar yields bit-identical results regardless of the scalar — so this column is bit-identical under **any** uniform positive close rescale, not only powers of two. Measured: x8/x64/x10/x3.7 close all **bit-identical, 0.0 max\|diff\|**, matching NaN masks. `0 < 1,540 fires < 1,600` and 3 distinct values (not 1) rule out a constant column |
| E Attribution | SHIP — max \|ρ\| 0.7108 vs `ZIGZAG` (`compute_all`, n = 33,246); per-frame max median 0.7243 (84 frames); below the 0.76 ship line | Run `is39-lot_zeroret_60-f8975998`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). `gate_e_overlap.py run --module pandas_ta.statistics.lot_zeroret_60` |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4151 passed, 83 skipped** — the three failures are the known break (`test_pine_coverage_csv.py`, untracked `docs/pine/` corpus), the sibling-repo dependency (`test_altrepo_talib_csv.py`, needs `../AlternativeRepos`), and `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (resolved by a future receipt session's ledger record); all three are documented pre-existing/expected failures per `CLAUDE.md`, none caused by this port |

## Wiring

`Category` statistics list gains `lot_zeroret_60` (alphabetically between `kurtosis` and
`mad`); `df.ta.lot_zeroret_60()` accessor added. Touch points:
`pandas_ta/statistics/lot_zeroret_60.py` (module), `pandas_ta/statistics/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["statistics"]` (discovery),
`pandas_ta/core.py` → `AnalysisIndicators.lot_zeroret_60` (accessor),
`tests/test_lot_zeroret_60.py` (tests). `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated **271 → 272**. `README.md`'s headline and `statistics` category
row, and `docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tagged-column
count updated and checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.

## Receipt

Gate E: SHIP. Max |ρ| 0.7108 vs `ZIGZAG` (`compute_all`, n = 33,246); per-frame max
median 0.7243 across 84 frames, 0.0% of frames at |ρ| ≥ 0.90; against the `ml_features`
manifest, max |ρ| 0.5301 vs `Pct_Up_Days_63` (n = 393,509). Run id
`is39-lot_zeroret_60-f8975998`, 89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators
(329 `compute_all` + 358 manifest), canary bit-equal on AKBNK.IS, BIENY.IS, AGHOL.IS,
SASA.IS. Under the 0.76 SHIP line (`r3-perframe-0.90` bands) — column ships, nothing
reverted. Recorded in `docs/gate_e_ledger.csv` on 2026-11-02.
