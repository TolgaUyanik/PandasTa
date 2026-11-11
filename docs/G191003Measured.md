# g191_003 — measured (issue #79)

> **Status: Gates A–D and F (this repo) cleared; Gate E pending, run by
> issue-solver after this session.**

6-day accumulation/distribution sum: Guotai Junan's (2017, "GTJA191",
internal quant report) alpha `#3`, per issue #79, which attributes its
copy of the report to HKUDS/Vibe-Trading (MIT) — a copy not read in this
session, see the disclosure under Gate A. Module
`pandas_ta/momentum/g191_003.py`, column
`G191_003_6`. Tests: `tests/test_g191_003.py` (**27, all passing**).
Numbers below: `python docs/measure_g191_003.py`. Environment: this
worktree's pinned pandas/numpy. Measured 2026-11-11.

## Gate A: derivation from the published formula, not the prototype

Issue #79 states GTJA191 alpha `#3`:

    SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) : MAX(H,C1)), 6)

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy — HKUDS/Vibe-Trading (MIT) — was never read. Everything below is
derived from the issue's own stated formula string, per the issue's own
rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:282-287`):

    @cand("g191_003", "6-day accumulation/distribution sum", G,
          "#3: SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) : MAX(H,C1)), 6)", "/close")
    def _(o, h, l, c, v):
        c1 = delay(c, 1)
        x = np.where(c == c1, 0.0, c - np.where(c > c1, np.minimum(l, c1), np.maximum(h, c1)))
        return tsum(pd.Series(x, index=c.index).where(c1.notna()), 6) / c

with `delay`/`tsum` read off the same module source (`ind_screen.py:45`,
`:49`): `delay(x, n) = x.shift(n)`, `tsum(x, n) = x.rolling(n).sum()`.
The issue's string and the prototype agree, including the 6-bar window and
the scale-free conversion (`conv="/close"`, the issue's own field).

### Three readings the string does not fix on its own

All three follow the prototype, which is the only disambiguating source
available in this worktree. They are decisions, not transcriptions:

1. **`C=C1` is a comparison**, `close == close.shift(1)` — GTJA191's
   pseudo-code spells equality with a single `=` inside a ternary
   condition. The prototype writes `c == c1`.
2. **`MIN(L,C1)` / `MAX(H,C1)` are pointwise**, two-argument min/max of
   two series, not the windowed `TSMIN`/`TSMAX` operators GTJA191 uses
   elsewhere (`ind_screen.py:50-51`). The prototype writes
   `np.minimum(l, c1)` / `np.maximum(h, c1)`.
3. **Bar 0 is masked to NaN, by decision.** `C1` is undefined there, so
   the `C=C1` test is neither true nor false. The prototype resolves it
   with `.where(c1.notna())`; this port does the same. NumPy alone would
   not: `c == nan` is `False`, which sends bar 0 down the `MAX(H,C1)`
   branch, where `np.maximum(h, nan)` is NaN — the same output for the
   wrong reason, and `0.0` the moment anyone "fixes" the comparison.
   `tests/test_g191_003.py::test_bar_zero_is_masked_by_decision_not_by_accident`
   pins it at `length=1`, where the mask is the only thing between bar 0
   and a value.

### The `C=C1 ? 0` branch is load-bearing

Unlike `g191_129`, whose `clip(lower=0)` was a faithful restatement of its
ternary, this zero branch cannot be dropped: a flat bar fails `C > C1`, so
without the branch it takes the `MAX(H,C1)` route and contributes
`C - MAX(H,C) = C - H <= 0` — a negative number on a bar whose close did
not move. Measured against a live `exec`'d mutant with that branch
deleted, on an 8-bar fixture holding one exactly-flat close (`length=3`):

| | `t=3` | `t=4` |
|---|---|---|
| shipped (zero branch) | `5/12 = 0.4166666666666667` | `6/14 = 0.42857142857142855` |
| mutant (branch deleted) | `2/12 = 0.16666666666666666` | `3/14 = 0.21428571428571427` |

identical again from `t=5`, once the flat bar leaves the window. The two
forms' per-bar CONTRIBUTIONS differ at exactly the bars where `C == C1`
and `H > C`; the COLUMN differs at every NON-NaN trailing `length`-bar
window holding such a bar, so one flat bar moves UP TO `length` outputs —
**2** here, because the three windows holding the flat bar are `t=2,3,4`
and `t=2` is still inside the warm-up (NaN in both forms). All four
numbers in the table are pinned by
`test_the_flat_close_branch_is_not_redundant`, together with the `t>=5`
identity.

**How often the branch is reached, disclosed rather than glossed over:**
on the 1,500-bar synthetic continuous-float walk, **0 of 1,500** bars have
`C == C1` exactly (census: **762 up**, **737 down**, 0 flat; bar 0 has no
`C1`). The branch is effectively unreachable on continuous floats (an
exactly-zero increment has probability ~0 on a float64 draw, not zero)
and plausibly common on tick-rounded exchange data — **by analogy only**:
neither this session nor CLAUDE.md measures `C == C1` frequency, and the
nearest measured number is a DIFFERENT statistic, the `fvg`/FVGDEAD note's
21.17% of BIST daily bars closing exactly at an extreme (`C == H` or
`C == L`). So the synthetic walk does **not** exercise the branch, and the
dedicated fixture above plus
`test_an_all_flat_window_is_exactly_zero` are what cover it.

### Per-bar sign

A structural property of the two live branches, holding unconditionally —
no OHLC-consistency assumption needed — and measured as a check rather
than taken on trust: on an up bar the reference is `MIN(L,C1) <= C1 < C`,
so the contribution is strictly positive; on a down bar it is
`MAX(H,C1) >= C1 > C`, so strictly negative. On the 1,500-bar walk, **0 of
762** up bars contribute `<= 0` and **0 of 737** down bars contribute
`>= 0`. The column is therefore a SIGNED tally, not a magnitude like
`g191_129`'s: **767** positive and **727** negative bars of the 1,494 that
fire. 767 + 727 = 1,494, so the walk produces **no zeros at all** — the
third value the column can take is pinned by
`test_an_all_flat_window_is_exactly_zero` on a 7-bar constant-close
frame, where every bar takes the `C=C1` branch, every contribution is a
literal `0.0`, the sum is bit-exact and the column is exactly `0.0` at
`t=6`, or it would be measured nowhere. A MIXED window that cancels only
in real arithmetic is a different case and is **not measured**: it can
land within float64 rounding of zero rather than on it, and neither the
walk nor any fixture here produces one.

### What this is, next to what the fork already ships

The windowed form of Williams' cumulative Accumulation/Distribution (the
issue's own screen says so: `skipped.py:164`, "Williams A/D is cumulative;
g191_003 is its windowed form"). This fork ships no `wad` — measured by one
case-insensitive content search for `wad|williams` over
`pandas_ta/**/*.py` (ripgrep, source files only, so no `__pycache__`
artefacts), which matches **three** files: `momentum/willr.py` (Williams
%R), `volume/bw_mfi.py` (Bill Williams' MFI) and this port's own
docstring. Before this port it matched the first two. The shipped `ad` is a different
construction (volume-weighted close-location). `g191_059` is the 20-bar
window variant of this same formula and was dropped by the screen
(`skipped.py:46`) rather than ported.

**The merged variant.** Issue #79 merges `g191_029` (6-day return ×
volume, prototype ρ 0.9077 against this candidate) into itself. Only
`g191_003` is ported here; `g191_029` ships nothing, which is what
"variants merged here" means.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the issue's own stated formula with three readings fixed and disclosed above, then matched against the prototype BIT-FOR-BIT | A hand-derived 7-bar example (`length=3`) with the arithmetic written out: per-bar contributions `[nan, 3, -3, 6, -7, 12, -13]`, column `[nan, nan, nan, 0.4, -0.5, 0.55, -1.1428571428571428]`, bar-by-bar to `abs=1e-12`. An independent per-bar replay (plain Python loop over numpy scalars — no `.rolling()`, no `.shift()`, no `np.where`) at the shipped default on a 900-bar frame: `t=300 module=-0.01447584866997064 loop=-0.01447584866997064`, `t=600` and `t=899` likewise exact. The retyped prototype expression: same NaN mask, `max\|diff\| = 0.0` on both the 1,500-bar walk (measure script) and a 900-bar seed-29 frame (test). The REAL candidate loaded out of `docs/issues/screen/ind_screen.py` through its own registry — present in this worktree, gitignored so the test may not depend on it: port vs candidate `max\|diff\| = 0.0`, retyped vs candidate `max\|diff\| = 0.0`, so the retyping hides no slip |
| B Causality | pass | Future-perturbation sweep (high/low/close jointly rewritten from `j` onward), 37 offsets past the 7-bar warm-up: real module **0 of 37** leaks. Two mutants (`importlib` source read, `exec`'d in memory), each shown live different from the real module, then caught **37 of 37**: the final write index shifted `length=6` bars into the future, and `rolling(length, center=True)` in place of the causal trailing window (the `bos` look-ahead bug class CLAUDE.md documents) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic high/low/close walk (seed 11, `low <= close <= high` at every bar; see `docs/measure_g191_003.py:_walk`), shipped default: **1,494 of 1,500** bars non-NaN (99.60%) — exactly `n - length` — first valid at bar **6**, the structural warm-up boundary (`min_length - 1`). **1,494 distinct values**. Range `[-0.116513, 0.115872]`, median `0.001073`, **767 positive / 727 negative** |
| D Scale-free | pass | Both branch tests are scale-invariant and `MIN`/`MAX` select rather than compute, so a positive rescale factors straight through the window sum and cancels against the `/close`. Measured on the 1,500-bar walk: PRICE ×8/×64 **bit-identical, 0.0 max\|diff\|**; ×10/×3.7 within float64 rounding tolerance (**3.99e-16 / 4.06e-16**), NaN masks matching at all four. The exact-float branch masks (`C > C1`, `C == C1`) are measured too, since a rescale could in principle move a bar between branches: **0 bars changed branch** at any of the four multipliers. `0 < 1494 fires < 1500` and `1494 > 1` distinct values rule out a constant column |
| E Attribution | **pending, run by issue-solver after this session** | Not run here (the launcher runs `gate_e_overlap.py`; this session may not read `../Backtesting`). Issue #79 measured the PROTOTYPE at max \|ρ\| 0.8525 vs `FWMA_Slope_pct` (n = 397,247), top-5 per-frame max median 0.8563 → DISCLOSE_GAP — a prototype is not a port, so that number is an expectation, not this column's result. See the synthetic non-redundancy check below, which is **not** Gate E and lands higher than the issue's own fork-overlap number |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Non-redundancy on a synthetic frame — NOT Gate E, and it is not comfortable

Spearman ρ of `G191_003_6` against the nearest shipped columns, on the
900-bar seed-5 walk (`python docs/measure_g191_003.py`):

| comparator | ρ | n |
|---|---|---|
| `kdj:J_9_3` | **0.906078** | 888 |
| `WILLR_14` | 0.842164 | 887 |
| `G191_129_12` | -0.647570 | 888 |
| `CMF_20` | 0.204181 | 881 |
| `AD` | 0.060369 | 894 |

`kdj:J_9_3` lands **above** the 0.90 strike line on this frame. Two facts
bound what that means, and neither is a reason to ignore it:

* It is a SYNTHETIC frame of 900 bars, not Gate E. Gate E's bands are
  defined over the 89 frozen ALTPORT-1 BIST frames against the engine's
  687 comparators (CLAUDE.md, Gate E), and `kdj` is a fork column, not
  necessarily one of those 687.
* On REAL data the owner's own stage-2 fork-overlap screen measured
  **0.8394** against this same `kdj:J_9_3` over 12 frames, with a
  per-frame max median of 0.8414 (issue #79) — below the line. The
  synthetic walk is i.i.d.-lognormal and its up/down alternation is
  cleaner than a real tape's, which is the plausible reason the synthetic
  number sits ~0.07 higher; that explanation is a read, not a
  measurement.

The authoritative number is the launcher's Gate E run. If it strikes the
column, the port is reverted with this file kept as the receipt — which
issue #79 counts as done exactly as well as a ship.

## Wiring

`Category` **313 → 314** (`momentum` **79 → 80**); `df.ta.<name>()`
accessor count **321 → 322**; dictionary probe **315 → 316** indicators.
Touch points: `pandas_ta/momentum/g191_003.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.g191_003` (accessor), `tests/test_g191_003.py`
(tests). `README.md`'s headline and `momentum (80)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **658 → 659 / 301 → 302 `SF`** (`G191_003_6` probes cleanly
at the dictionary's 600-bar synthetic frame with a 6-bar warm-up and takes
many distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(313 → 314); no `CATEGORY_BUCKETS` entry needed (that dict tracks only
`trend`/`volatility`/`volume`, not `momentum`).

Gate E will be run by the launcher (`gate_e_overlap.py`, Backtesting
#107); `docs/gate_e_ledger.csv` carries no row for `g191_003` yet, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here by design (CLAUDE.md, "Owed, not failed"). A later receipt
session records the row and fills in the Gate E numbers above.

## Suite run (this repo, this session)

`python -m pytest -q -p no:warnings --tb=no -rf`, full suite, default
collection order: **3 failed, 5221 passed, 83 skipped** (104s).
`g191_003`'s own tests: **27 passed**. The three failures:

* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — "no Gate E ledger row for `['g191_003', 'mtd_ret']`". Owed by design
  for `g191_003` (this session may not run Gate E); the `mtd_ret` half
  pre-dates this session.
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, absent in this
  worktree (CLAUDE.md "Known breaks"; CI deselects it).
* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` corpus (CLAUDE.md "Known breaks").

No other test regresses.

### One pre-existing cross-test observation, found while running subsets

Not caused by this port and not fixed here. Running
`tests/test_wiring_accessors.py` BEFORE `tests/test_altport2_ports.py` in
the same process makes
`test_the_category_count_moved_by_exactly_three` fail with "Category total
311, expected 314": a category-mode `df.ta.strategy()` run mutates
`Category` in place, because `_indicators_by_category` returns the live
list (`pandas_ta/core.py:453`) and the exclusion loop calls `.remove` on
it (`core.py:692`) — that attribution is read in the code, while the 311
is measured. Default (alphabetical) collection order puts `altport2`
first, so the full suite is unaffected, which is why it has never shown
up. Left alone deliberately: fixing it changes `strategy()` behaviour and
is outside issue #79's scope.
