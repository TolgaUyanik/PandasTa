# FVGDEAD-1 — every `IN_FVG_*` reference, and which of them is suspect

Scope: find where the two repaired columns are consumed in `../Backtesting/`, and
name any mined rule keyed on them. Completed 2026-09-07.

## 🔴 The headline finding: the engine did NOT use `pandas_ta.fvg`

Repairing `PandasTa/pandas_ta/trend/fvg.py` changed **nothing** in the engine, because there were
**three independent re-implementations** of the same zone loop in `Backtesting/`, none of which
called pandas_ta, and all three carried the identical defect — a zone appended and then, in the
same iteration, retained only while `close <= zone_high` (bull) / `close >= zone_low` (bear).

| # | file | role | live? | state after this run |
|---|---|---|---|---|
| 1 | `backtesting_engine/indicator_engine.py` (`_calculate_fvg`) | research / mining feature set | no | ✅ delegates to `ta.fvg` |
| 2 | `backtesting_engine/speedy_indicators.py` | dashboards, hourly refresh | no | ✅ delegates to `ta.fvg` |
| 3 | `deploy/app/paper_trading/paper_trading.py:804-825` | **live container** (`ENTRIES_FROZEN`, exits only) | yes | ⏸ unchanged — owner-gated (FVGENG-2) |

## ⚠ Correction to FVGDEAD's own premise

The task says the columns are "constant zero by construction". **Measured on real data,
that is false**, and the error was mine: it was measured on synthetic continuous-float
frames, where a close never exactly equals a bar extreme.

| logic | IN_FVG_BULL | IN_FVG_BEAR | basis |
|---|---|---|---|
| pre-repair, synthetic | 0 | 0 | 12,000 bars, 6 seeds |
| **pre-repair, real BIST daily** | **18,895 (4.63%)** | **14,320 (3.51%)** | 89 frames, 408,253 bars |
| repaired, real BIST daily | 90,506 (22.17%) | 81,021 (19.85%) | same |

Why it fires at all on real data: **86,415 of those 408,253 bars (21.17%) close exactly at
their high or low** (tick-rounded prices tie; continuous floats do not). Reproduce with Gate 0 of
`measure_fvg_overlap_full.py` → `backtest_results/tvpta6/fvg_prerepair_counts.csv`. A zone survived its own
formation bar precisely when that tie occurred.

**So the defect is not a dead column — it is worse to model on than a dead one.** Which
zones survived was decided by whether a close happened to tie the bar's extreme, i.e. by
tick rounding and price level, not by the structure the column claims to measure. A dead
column is inert; this one carried a plausible-looking signal that encodes lot-size effects.
The engine's own copy confirmed the rate before it was fixed: `AKBNK.IS` gave 248 / 107 fires
over 5,748 bars, against 1,389 / 1,334 once it delegates to the repaired library.

## Consumers, and the verdict on each

| reference | what it is | suspect? |
|---|---|---|
| `scripts/mining/run_bist_daily_canonical_mining.py:108` and `run_contract_grid.py:24` — `BIST_DAILY_PRIORS` | 🔴 **`IN_FVG_BULL` is one of the 17 hand-curated MLF-5 economic-priors features.** With `--priors`, the tree sees ONLY these 17. A tick-rounding artifact was hand-picked into the shortest feature list in the project. | **YES — the most material one** |
| `backtesting_engine/rdbt/category_columns.py:56` | `IN_FVG_BULL` listed under the `Structure` category | yes, same artifact |
| `backtesting_engine/mining_runner.py:154` | both columns in the **Pass 2 exclude** list (forces oscillator strategies) | no — an exclusion |
| `scripts/mining/run_daily_{6pct,ctc_3pct,ctc_4pct,ctc_5pct,ctc_6pct}_mining.py:~91-99` | both columns in exclude lists | no — exclusions |
| `scripts/utils/gen_indicator_register.py:579-580` (and the FVG passage at `indicator_engine.py:1707-1710`) | uses `IN_FVG_BULL` as a same-polarity duplication comparator — **live code, not an artifact**; the comparator's semantics changed with the repair | yes — re-run the register (done 2026-09-07) |
| `backtesting_engine/indicator_engine.py:1707-1710` | names the columns in a docstring about same-polarity duplication | doc only, now accurate |
| `datastore/source/pine_candidates_families.csv` | pine-candidate family mapping listing the column | stale mapping, no runtime effect |
| `backtest_results/indicator_snapshot_bist_1d_*.csv`, `rdbt_audit/percentile_grid_two_sided_20260830.csv` | snapshot / percentile artifacts containing the column | stale, regenerate on any repair |

## Mined rules: none

- `datastore/source/StrategyMaster.csv` — **0 matches** for `IN_FVG`. No deployed or mined
  strategy is keyed on either column.
- No rule text in `backtest_results/` (`*.csv`, `discovered_strategies*.py`) references
  them: the columns were **available to the miner and never selected**, which is what a
  tie-driven artifact should look like — it produces no stable split.

**So no live strategy is at risk, and no mined rule needs re-validation.** The exposure is
forward-looking: `IN_FVG_BULL` sits in the 17-feature priors list that future BIST-daily
mining runs use.

## What was done about the three copies — and what the freeze actually covers

⚠ **Correction (review round 1).** The first version of this report deferred all three copies on
TRADING FREEZE grounds. That was right for copy 3 and wrong for copies 1 and 2: neither is deploy
code, neither is in the container, and the freeze suspends strategy changes and rebuilds — not
research-side bug fixes. The SHIP-WITH-THE-CHANGE trio is a cost, not a prohibition, and leaving
them meant the feature the miner actually consumes stayed the artifact while the fork's docs read
as fixed.

**Copies 1 and 2 are now fixed** (2026-09-07): both delegate to `pandas_ta.fvg`, the private loops
are deleted (−45 lines), and the fix lands in one place from here on — the ARCH-7 argument that
deleted the vendored `deps/pandas_ta/`.

- parity test: `Backtesting/tests/test_fvg_engine_parity.py` (**6 tests**) pins engine output equal
  to `ta.fvg`, the fire rate away from the old ~4% artifact band, the no-membership-on-the-formation-
  bar rule, **copy 2 exercised directly** (`compute_all` never calls it), the int32 dtype of the two
  formation flags, and short-frame degradation to a warning.
- suite: 746 passed. The 3 failures and 2 collection errors are pre-existing and reproduce with the
  change stashed (`fcntl` is Unix-only; the other three fail on missing fixtures).
- SHIP-WITH-THE-CHANGE: `docs/indicators/family-structure-smc.md` updated,
  `scripts/utils/gen_indicator_register.py` re-run after the dtype cast (492 cols, 0 newly
  classified),
  `verify_claude_md.py` all checks PASS.

**Copy 3 is deliberately untouched.** `deploy/app/paper_trading/paper_trading.py:804-825` is inside
the live container; changing a live feature's semantics is a decision-basis change even with
`ENTRIES_FROZEN`, and Mode C puts deployment out of auto scope. It stays as **FVGENG-2** for the
owner. Until it lands, **research and live compute different `IN_FVG_*` columns** — worth knowing
before any live-vs-backtest feature comparison.
