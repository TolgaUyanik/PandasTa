# ovn_split — measured

> **Status: Gates A, B, D pass; C synthetic only; E PENDING, run by issue-solver after this
> session.** `ovn_split` is in `Category`, so any `df.ta.strategy()` sweep picks it up; merging
> before Gate E lands is the owner's call, per the `pfe` / `kalman_trend` precedent.

Columns `OVNSUM_21`, `INTSUM_21`, `OVNINTDIFF_21`: rolling sums, over a trailing 21-bar window,
of the two legs each bar's move splits into -- the OVERNIGHT leg (yesterday's close to today's
open) and the INTRADAY leg (today's open to today's close) -- plus their difference. Module
`pandas_ta/momentum/ovn_split.py`, tests `tests/test_ovn_split.py`, branch `issue-14-ovn`.

## The risk the issue asked to check first -- NOT checked

The issue's own words: "Quantpedia's warning is that the **open** in free OHLC data is often
wrong. Measure how trustworthy the yfinance BIST open is (e.g. how often `open == prev close`)
before building." **This was not measured.** This headless worktree has no network access (no
yfinance), no BIST OHLC fixture (`data/SPY_D.csv`, the one real-data fixture this repo's tests
reference, is itself gitignored and absent here per `CLAUDE.md`'s "Commands" section), and
`docs/pine/` / web access are unavailable per this session's rules. There is nothing real to
check the risk against in this environment.

`docs/measure_ovn_split_proxy.py` includes a synthetic stand-in (forcing a fraction of bars to
open exactly at the prior close and measuring the resulting tie rate) purely to show the module
reacts sensibly to the failure mode the risk describes -- it is NOT a measurement of yfinance or
BIST data and must not be read as one:

| forced tie probability | measured tie fraction (synthetic, seed 23, 1200 bars) |
|---|---|
| 0.0 | 0.0092 |
| 0.3 | 0.2892 |
| 0.7 | 0.7300 |
| 0.9 | 0.9117 |

If the real yfinance BIST `open` repeats the prior `close` often (the Quantpedia-cited failure
mode), the OVERNIGHT leg collapses toward zero on those bars and the real signal is pushed
entirely into the INTRADAY leg and the difference column -- a distortion, not a crash: no NaN,
no exception, just an overnight-leg value of exactly 0 on the affected bar. **This needs
re-measuring on real BIST frames before the owner relies on `OVNSUM_21` specifically.** The
launcher's Gate E run has the real data; it is asked, in "To close" below, to also report the
real `open == prev close` tie rate, not just the overlap numbers.

## Decisions the issue left open

The issue describes the feature ("rolling sums of the close->open and open->close returns, as
two columns; optionally their difference") but not these choices. No human was available to ask
(headless session), so each took the most conservative, smallest-scope reading:

1. **Log returns, not simple (arithmetic) returns.** `SUM(LOG(a/b), length)` equals the log of
   the bar-by-bar COMPOUNDED ratio over the window -- the identity "rolling sum of returns"
   invokes in the cited momentum literature (and the one a tree-based model should see, since a
   sum of log returns is a monotone transform of total compounded return; a sum of simple
   returns is not). ASSUMPTION, not measured against the simple-return form.
2. **Window length 21** (one trading month), matching the monthly formation horizon the cited
   Alpha Architect sources use repeatedly when sorting on this split. Not tuned as a standalone
   per-bar feature window, and not cross-checked against another length. ASSUMPTION.
3. **The difference column is shipped**, not held back as optional: the issue offers it as
   optional ("optionally their difference"), but the cited sources frame "overnight minus
   intraday" as the anomaly signal itself, so withholding it would ship the two legs without the
   one combination the literature actually tests. ASSUMPTION.
4. **Category: `momentum`**, not `performance` (which already holds `log_return` /
   `percent_return` / `trend_return`, the closest existing building blocks) or `statistics`. The
   two Alpha Architect sources are literally titled "Overnight Momentum vs. Intraday Momentum",
   and the closest existing analog already shipped, `gapm` (also a close/open-derived rolling
   sum), is in `momentum`. ASSUMPTION.
5. **Bar 0's intraday leg is blanked to match the overnight leg's structural NaN** (there is no
   prior close before bar 0, so the overnight leg cannot be defined there). Without this, the
   two rolling sums would warm up one bar apart from each other, which would make the pair
   confusing to read together. Measured consequence pinned by `tests/test_ovn_split.py`'s edge
   tests.

## What it is, and what it is not

`overnight[t] = LOG(open[t] / close[t-1])`; `intraday[t] = LOG(close[t] / open[t])`.
`OVNSUM_21 = SUM(overnight, 21)`, `INTSUM_21 = SUM(intraday, 21)`,
`OVNINTDIFF_21 = OVNSUM_21 - INTSUM_21`.

**Not the engine's one-day `GAP_PCT` / `OPEN_GAP_PCT`** (per the issue's own overlap note,
`indicator_engine._calculate_gap_indicators`): those are single-bar gap measures with no rolling
window. This is a 21-bar rolling SUM of the overnight leg alone, plus the matching intraday leg
and their difference -- a different statistic, not a renamed copy.

**Is it already shipped?** A grep of the repo (excluding the untracked `docs/pine/`) for
`overnight`, `intraday`, `OVNSUM`, `INTSUM` finds nothing before this port. `gapm` is the closest
existing relative (also close/open-derived) but sums signed PRICE gaps in a ratio, not LOG
RETURNS summed directly; the pre-screen below measures the two are not close substitutes
(max |rho| 0.70, under the disclosure band).

## Gates

Environment: this worktree's Python/pandas/numpy (`docs/IndicatorDictionary.md` header: pandas
2.3.3). `tests/test_ovn_split.py`: 16 of 16 passing.

| Gate | Result |
|---|---|
| A | **Against an independent reference loop**: per-bar overnight/intraday legs computed by a plain Python loop from the formula, then summed over the trailing window, on a 1,200-bar overnight/intraday walk (seed 14). Max\|diff\| at length 21 / 9 / 2: OVNSUM **1.39e-17 / 2.08e-17 / 8.67e-18**, INTSUM **4.16e-17 / 4.16e-17 / 1.39e-17** (n 1,179 / 1,191 / 1,198) -- floating-point noise, not a formula mismatch. **Hand-computed closed forms**: a frame where `open == close` every bar (zero intraday leg, only the overnight leg moves) reads `INTSUM` exactly 0 on every valid bar and `OVNSUM` equal to the independently-summed overnight series; the symmetric case (`open == prior close` every bar) reads `OVNSUM` exactly 0. A flat-price frame (open == close == constant) reads both sums exactly 0, not NaN. |
| B | Future-perturbation: replace the open/close tail from offset J onward with an unrelated walk, assert bars `< J` are bit-identical with matching NaN masks, over 32 offsets (J = 60..1145, step 35). The real module leaks at **0 of 32**. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) -- the overnight leg reading tomorrow's open, and the rolling-sum window reading one bar ahead -- are each shown to change the output live, then caught at **32 of 32** offsets each. |
| C | **Synthetic only; real-data counts owed to Gate E's run.** 1,200-bar overnight/intraday walk (seed 14, sigma_overnight 0.4%, sigma_intraday 1.1%, tick 0.01), length 21: **OVNSUM_21** 1,179 non-NaN, 1,179 distinct, range [-0.05423, 0.05490]; **INTSUM_21** 1,179 non-NaN, 1,179 distinct, range [-0.14785, 0.16189]; **OVNINTDIFF_21** 1,179 non-NaN, 1,179 distinct, range [-0.17637, 0.14936]. A composite-frame test (50 bars overnight-only move, then 50 bars intraday-only move, length 10) demonstrates `0 < fires < n` for all three columns and that `OVNINTDIFF_10` changes sign between the two regimes (`tests/test_ovn_split.py::test_column_is_not_constant_on_a_composite_frame`). |
| D | Each leg is `LOG(price ratio)`, so a positive rescale of `open`/`close` cancels before the log. Measured, not assumed: **x8 and x64 (powers of two) are bit-identical** on all three columns with matching NaN masks. **x10 and x3.7 are within 2.33e-15 absolute** (floating-point multiplication roundoff before the log, not a real difference) with matching NaN masks -- well under the 1e-10 tolerance the test asserts. `0 < fires < n`: see Gate C's distinct-value counts (all three columns vary; none is constant). |
| E | **PENDING.** Run by issue-solver (`gate_e_overlap.py run --module pandas_ta.momentum.ovn_split`) after this session; recorded in `docs/gate_e_ledger.csv` by the receipt session. Pre-screen below is informal, NOT Gate E. |
| F | **This repo only**, CI's two `--deselect`s (`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, the known break; `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, needs `../AlternativeRepos`): the only failure in this worktree's full run is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, naming exactly `{'ovn_split'}` -- expected, and it clears once the Gate E row is recorded. Parent repo (`Backtesting`) not run from this worktree; the launcher runs both suites in clean worktrees separately. |

## Pre-screen (NOT Gate E)

Spearman rho of each new column against in-package candidates, same 1,200-bar synthetic walk
used above (informal; Gate E uses the production engine's 687-comparator set over 89 real BIST
frames, not this):

| comparator | vs OVNSUM_21 | vs INTSUM_21 | vs OVNINTDIFF_21 |
|---|---|---|---|
| `GAPM_40_20` | 0.6034 | -0.0976 | 0.2757 |
| `TRIX_30_9` | 0.2985 | 0.2591 | -0.1713 |
| `ROC_10` | 0.2590 | 0.6891 | -0.5952 |
| `MOM_10` | 0.2462 | 0.6942 | -0.6044 |
| `LOGRET_1` | 0.0741 | 0.2159 | -0.1939 |
| `PCTRET_1` | 0.0741 | 0.2159 | -0.1939 |
| `CUSUM_100` | 0.4426 | 0.6555 | -0.5117 |
| `PFE_10_5` | 0.3340 | 0.7343 | -0.6147 |

All magnitudes are under the disclosure band (0.76); the closest, `INTSUM_21` vs `PFE_10_5` at
0.7343, is still below it. This is a proxy on one synthetic walk, not a prediction of the Gate E
result.

## Reproduce

    python docs/measure_ovn_split_proxy.py

## To close

1. Run Gate E (`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
   pandas_ta.momentum.ovn_split --name ovn_split`), then `python docs/gate_e_ledger.py record
   <run dir> --measured YYYY-MM-DD [--waiver "#14"]`.
2. Apply CLAUDE.md's bands (`r3-perframe-0.90`: STRUCK >= 0.90, DISCLOSE_GAP 0.80-0.90, DISCLOSE
   0.76-0.80, SHIP < 0.76) **per column** -- `OVNSUM_21`, `INTSUM_21` and `OVNINTDIFF_21` can land
   in different bands. On any STRUCK, delete that column (or the whole module if all three
   strike); on all three STRUCK, delete the module, export, `Category` entry, accessor and
   tests, and keep this file as the receipt (a measured revert closes issue #14 exactly as well
   as a ship).
3. Fill Gate C's real-data counts from the same Gate E run.
4. **Measure the real yfinance BIST `open == prev close` tie rate** on the 89-frame universe --
   the issue's "Risk, check first", not done here (see the section above). If it is material
   (the synthetic probe above suggests it becomes so above roughly 70% of bars), flag it to the
   owner even if Gate E itself ships: a high tie rate means `OVNSUM_21` is measuring data
   staleness as much as any real overnight return.
5. Both repos' suites (the launcher runs these in clean worktrees).
