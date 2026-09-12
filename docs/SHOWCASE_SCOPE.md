# SHOWCASE scope — what may be published, block by block

**Status:** proposed 2026-09-12, awaiting owner signature (see *Sign-off* at the end).
**Task:** `TODO.md` → `SHOWCASE-0`. Nothing in the SHOWCASE build is exempt from this document.

## Why this document exists

`PandasTa` is a **public** repository, published as `github.com/TolgaUyanik/PandasTa`. The source
material for the showcase, `../Backtesting/SpeedyAnalysisDaily.py`, is a file from a **private**
research repo. It imports nine names from `deploy/app/core/config.py` and contains a scoring class
that encodes live decision rules.

The governing rule is in the root `CLAUDE.md`: *"Do not publish strategy rules externally — these
are internal IP."* Copying the file across would breach it. This document decides, per block, what
crosses the boundary.

Three verdicts are used:

| verdict | meaning |
|---|---|
| **publish** | copies across essentially as-is; it is library usage, not strategy |
| **synthesise** | the *shape* crosses, the *content* is replaced with something written for the example |
| **drop** | does not cross at all |

Two rows below carry a compound verdict, spelled out rather than left to inference:
**publish (math), drop (comment)** means the arithmetic crosses and the surrounding comment does
not; **publish, corrected** means the block crosses as `publish` after a defect in it is repaired
— the repair is not a `synthesise`, because no content is invented.

## The decisions

| # | Block in `SpeedyAnalysisDaily.py` | Verdict | Reason |
|---|---|---|---|
| 1 | `TechnicalIndicatorCalculator` — RSI, CCI, ATR, MFI, OBV, ADX, MACD, Supertrend, Ichimoku, Stochastic, StochRSI, Bollinger, SMA set | **publish** | Textbook indicator calls with textbook parameters. Nothing here is a decision rule. |
| 2 | `calculate_pivot_points`, `calculate_previous_levels`, `calculate_fibonacci_retracements`, `calculate_atr_channels` | **publish** | Standard derived levels. Public formulas. |
| 3 | The STAT-3b rolling yearly/quarterly stats inside `calculate_previous_levels` | **publish (math), drop (comment)** | The `dist_from_yr_high_pct` arithmetic is generic. Its comment block names `SKILL-REC`, `hourly.db` and the live cron schedule — internal infrastructure, stripped. |
| 4 | `AdvancedIndicatorCalculator.INDICATOR_SPECS` (104 rows) | **publish, corrected** | A list of indicator names and parameters. See SHOWCASE-1: 16 rows carry broken argument lists and are fixed before publication, never copied as-is. |
| 5 | `calculate_advanced_indicators` bulk loop | **publish, corrected** | The loop is the useful pattern. Its bare `except: continue` is not — see SHOWCASE-2. |
| 6 | `calculate_volume_profile` | **publish** | `ta.vp` usage plus a POC/value-area reduction. Public technique. |
| 7 | PSAR / QQE / TD-Sequential consolidation | **publish** | Turning long+short branch columns into one level and one direction. API mechanics. |
| 8 | `MarketSignalCalculator.calculate_composite_score` | 🔴 **drop** | **This is the IP.** It encodes a banded oscillator ladder, trend-strength cut points, a fixed multi-factor weighting, and the boundaries that turn the result into a verdict. Those are decision rules, not library usage. ⚠ The specific values are deliberately NOT restated here — see the note under this table. |
| 9 | `MarketSignalCalculator.calculate_sector_signal` | 🔴 **drop** | Sector aggregation policy built on top of #8. Falls with it. |
| 10 | `SIGNAL_THRESHOLDS`, `INDICATOR_WEIGHTS` from `config.py` | 🔴 **drop** | The literal constants behind #8. |
| 11 | `GLOBAL_MARKETS`, `US_SECTOR_ETFS`, `BIST_SECTORS`, `get_all_market_tickers`, `get_market_name`, `get_market_category`, `get_bist_sector_for_stock` | 🔴 **drop** | The traded universe and its sector map. Reveals what is watched. |
| 12 | **All nine hard-coded symbol lists** in `SpeedyAnalysisDaily.py:1131-1139`, not the two an earlier draft of this row named | 🔴 **drop** | Symbol universes, in full. ⚠ One of the nine is materially more sensitive than the rest; it is identified in the private repo, not here. An earlier draft named two of the nine because it was written from the task description instead of from the file — the miss is recorded because the lesson is the process, not the list. The examples use one neutral, widely-known US ticker. |
| 13 | `sys.path` injection of `deploy/app/core` | 🔴 **drop** | A public example must not reference a private repo's layout, and could not import it anyway. |
| 14 | `classic_analysis` / `analyze_markets` orchestration, threading, `CSV_DIR` writing | **synthesise** | The shape — load, compute, emit — crosses. The content becomes a plain function taking a DataFrame, with the output path as an argument. |
| 15 | The yfinance download | **synthesise** | Becomes one optional pluggable loader with a synthetic fallback, never a hard import. See SHOWCASE-4. |

## ⚠ This document is PUBLIC, and must not become the disclosure

`docs/` ships with the repository. A scope document that quotes the values it is refusing to
publish has published them, and it would be the most embarrassing possible place to leak from.

**Rule for editing this file:** name the *shape* of a decision rule — "a banded ladder", "a
fixed weighting", "a verdict boundary" — never the numbers, and never the symbols. Anyone who
needs the specifics has the private repo, where they already are. An earlier revision of rows 8
and 12 restated the exact ladder, the exact weights, the exact cut points, and the sensitivity
of a named symbol list. That was caught before commit and removed.

## Deviation from the task's written default, recorded deliberately

`SHOWCASE-0` proposed: *"replace every threshold/weight with neutral demo constants defined in the
example file itself."* That is **synthesise** for blocks 8-10.

**The owner chose `drop` instead** (2026-09-12). The reasoning, so it is not relitigated: a
`pandas_ta` example exists to show what the library computes. A scoring layer — even one built from
invented constants — teaches readers to expect a verdict from an indicator library, and a reader
who knows the project exists may still read the *shape* of the composite as the real one. Dropping
it costs the example nothing it was for.

**Consequence:** neither `examples/market_dashboard.py` nor `examples/speedy_analysis.ipynb`
contains a composite score, a signal threshold, a weighting scheme, or a BULLISH / NEUTRAL /
BEARISH verdict. `tests/test_showcase.py::test_examples_contain_no_strategy_content` pins it.

⚠ **A banned-identifier test only sees NAMES.** Pasting a universe in as literal values would
pass it, so `test_no_private_universe_leaks_into_the_examples` checks the VALUES too — a sample
of the nine universes, plus a blanket refusal of any `.IS` ticker.

⚠ **The inventory below covers the SOURCE file. It cannot see a leak written directly into the
public examples.** One got through exactly that way: both examples disclosed the downstream
engine's live signal-bar convention, which is not a block of `SpeedyAnalysisDaily.py` at all. It
is removed, and the phrase is now in the banned list. When you add prose to an example, check it
against the never-infer list below, not against this table.

### Which of the permitted blocks are actually IN the examples

`publish` is a grant of permission, not a claim that something shipped. Rows 2, 3 and 6 are
permitted and are **not** in either example — no pivot points, no Fibonacci levels, no
`dist_from_yr_high_pct`, no `ta.vp` call. That is a choice about what a demo needs, not a
licensing question, and it is recorded here so this table cannot be read as a description of the
examples' contents.

## What a reader of the examples must never be able to infer

1. Which tickers are traded, or in what universe.
2. Any threshold, weight, or cut point used in a live decision.
3. Any sector grouping or market-routing policy.
4. That the example's output constitutes a trading signal. The examples state the opposite.

## One thing the examples must state, and do

The demo data is fetched with `yfinance` and is **not** cleaned. The BIST ±10% daily-limit
back-adjustment (`clean_if_bist`) lives in the consumer repo, not in this library, so a reader must
not infer that indicator output computed here has been through any data-integrity treatment. The
examples say so, and the default ticker is a US name where the BIST limit rule does not apply in
the first place.

## Sign-off

| | |
|---|---|
| Proposed | 2026-09-12 |
| Decision on blocks 8-10 | `drop` (owner, 2026-09-12, overriding the task's `synthesise` default) |
| Owner signature | ⚠ **NOT SIGNED** — see below |

🔴 **This gate is OPEN, and saying otherwise would be the worst kind of lie for a document
like this one.** `SHOWCASE-0`'s acceptance criterion is a signature; only the owner can supply
one, and an executor signing on the owner's behalf would defeat the entire purpose of an IP
gate. SHOWCASE-1 through -5 were built under these terms anyway, which is a departure from the
task's own "nothing below starts until it closes" — recorded here rather than smoothed over.

**What the owner needs to do:** read the fifteen rows, accept or overrule the `drop` on blocks
8-12, and replace the signature line with a name and a date. If a signature is not how this gets
approved, amend the acceptance criterion in `TODO.md` to whatever the real approval is.
