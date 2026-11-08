# a101_058 — measured (issue #42)

> **Status: Gates A-D cleared this session.** Gate E: pending, run by issue-solver
> after this session. Gate F (both repos' suites) is run by the launcher in clean
> worktrees; `python -m pytest -q` in this worktree is reported below for the record.

Decayed price-volume correlation rank: Kakushadze's (2016, Wilmott, "101 Formulaic
Alphas") Alpha101 `#58`, without its cross-sectional `IndNeutralize` wrapper (this fork
has no sector/industry classification to neutralise against), per issue #42's own
instruction. Module `pandas_ta/volume/a101_058.py`, column `A101_058_4_8_6`. Tests:
`tests/test_a101_058.py` (17, all passing). Numbers below: `python docs/measure_a101_058.py`.
Environment: this worktree's pinned pandas/numpy. Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #42 states Alpha101 `#58` (`IndNeutralize` dropped), with its own scale-free
substitution for `vwap`:

    -ts_rank(decay_linear(corr(vwap, volume, 4), 8), 6)
    vwap -> (H+L+C)/3

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are
both unavailable in this worktree, so the issue's own named copy -- vnpy's `vnpy/alpha101`
module (MIT) -- was never read. Everything below is derived from the issue's own
restated formula and from this fork's already-shipped operators, not from vnpy or from
Kakushadze's original paper text.

Each of the three operators is read from the issue's formula string and mapped to an
existing, already-tested primitive, not reimplemented from scratch:

1. `corr(x, y, d)` = rolling Pearson correlation over a trailing `d`-bar window. Reused
   verbatim: `pandas_ta.utils._pine.correlation`, the same helper `pvcorr` (issue #18)
   already ships behind. No new correlation code was written.
2. `decay_linear(x, d)` = a `d`-bar weighted moving average with linearly increasing
   weights, heaviest on the most recent bar (weight `d` on the current bar, `1` on the
   oldest, normalised by `d(d+1)/2`). This is EXACTLY `pandas_ta.overlap.wma`'s own
   definition at `asc=True`: `wma.py`'s rolling-window `apply` dots an ascending weight
   vector `[1, 2, ..., d]` against a window whose LAST element is the current bar, so the
   current bar gets the top weight `d` and the oldest gets `1` -- read from `wma.py`'s own
   source, not assumed. Reused, not reimplemented.
3. `ts_rank(x, d)` = the percentile rank of the current bar within its own trailing
   `d`-bar window. **ASSUMPTION, disclosed, not independently confirmed against vnpy or
   Kakushadze's glossary text:** Kakushadze's operator glossary names `Ts_Rank` but (per
   the issue's own restatement, the only source available this session) does not spell
   out tie handling or normalisation. This fork already ships one operator under this
   exact name and convention -- `pandas_ta.statistics.rank`'s `RANK_d[t] = count(close
   [t-d+1..t] <= close[t]) / d`, itself a port of qlib's `Rank` operator (issue #34) --
   so `ts_rank` here uses the identical convention (count-of-less-or-equal over the
   window, divided by the window length, range `(0, 1]`) for internal consistency across
   this fork's own operator library, NOT because it was confirmed against vnpy's actual
   implementation. A future session with web/`docs/pine/` access should re-check this
   against vnpy's `alpha101.py` `ts_rank` before treating the convention as settled.

`vwap -> (H+L+C)/3` is the issue's own literal substitution, taken as given (same
disclosure pattern as `osap_lrrev`'s month-to-trading-day conversion): this fork's
`vwap` is a volume-weighted price LEVEL (not scale-free on its own), so the issue
substitutes the scale-free typical-price proxy instead. No independent re-derivation of
this substitution was attempted; it is quoted directly from the issue text and from
`docs/issues/screen/candidates.csv`'s `a101_058` row (read for this one field, matching
the issue's own `conv` field, not consulted for anything else).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, built entirely from already-shipped, already-tested primitives (`corr`, `wma`, and this fork's own `ts_rank` convention from `rank.py`) | Hand-derived 8-bar example at `corr_length=2, decay_length=1, rank_length=2` (a 2-point Pearson correlation is always exactly +-1, decided by direction alone; `decay_length=1` is the identity): bars 2-6 read exactly -1.0, bar 7 reads exactly -0.5, derived by hand from the formula, not by re-running the module. Matches an independent `numpy.corrcoef` + hand-coded dot-product loop at the shipped defaults (`corr_length=4, decay_length=8, rank_length=6`), 3 spot-checked bars (300, 500, 899) on a 900-bar synthetic walk, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep (all of high/low/close/volume rewritten from `j` onward), 30 offsets past the 15-bar warm-up: real module **0 of 30** leaks (`python docs/measure_a101_058.py`). The repo test module (`tests/test_a101_058.py`) runs the same check over a shorter 15-offset sweep on a 900-bar frame, same result. A single-bar lookahead inside the correlation step was tried FIRST as the mutant and rejected: `ts_rank`'s 6-bucket output sometimes absorbs a 1-bar perturbation without changing bucket, catching only **18 of 30** offsets (`rejected_mutant` in `docs/measure_a101_058.py`, kept and run rather than only described, so the count is re-derivable) -- a quantisation artefact of the discretised final rank, not a causality gap. The mutant actually shipped shifts the whole write index `rank_length=6` bars into the future (`result = -ranked.shift(-rank_length)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **30 of 30** (measure script) / every offset (test module) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, σ=1.5%/bar close, σ=1.95%/bar volume), shipped defaults: **1,485 of 1,500** bars non-NaN (99.00%) -- exactly `n - 15`, the `corr_length+decay_length+rank_length-3=15`-bar combined warm-up, no wider gap. Only **6 distinct values** among the 1,485 fired bars: -1.0 (439), -0.833333 (151), -0.666667 (140), -0.5 (155), -0.333333 (154), -0.166667 (446) -- see the CARDINALITY note below, this is a structural property of `ts_rank(d, 6)`, not a defect |
| D Scale-free | pass | x8/x64 on EITHER high/low/close OR volume independently: **bit-identical, 0.0 max\|diff\|** (`corr` is scale-invariant in either argument by definition; `wma` and `ts_rank` inherit it). x10/x3.7 on either input: **also 0.0 max\|diff\|**, exact rather than merely within the 1e-9 tolerance the test asserts -- no floating-point drift anywhere in the chain. `0 < 1,485 fires < 1,500` and 6 distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | — |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4263 passed, 83 skipped** -- the 3 failures are all pre-existing/expected: `test_pine_coverage_csv.py` (known break, untracked `docs/pine/` corpus -- see CLAUDE.md "Known breaks"), `test_altrepo_talib_csv.py` (needs the sibling `../AlternativeRepos` checkout), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (this port's row is owed -- a future receipt session records it) |

## CARDINALITY: `A101_058_4_8_6` can only take 6 distinct values, by construction

`ts_rank(x, 6)[t] = count(x[t-5..t] <= x[t]) / 6` is an integer-over-6 fraction: its only
possible outputs are `{1/6, 2/6, ..., 6/6}`, whatever `x` is. Negating gives exactly
`{-1, -5/6, -4/6, -3/6, -2/6, -1/6}` -- 6 values, never more, regardless of how much the
underlying correlation varies. This is a direct consequence of `rank_length=6` being
small, not a bug in the port: Gate C above measures exactly 6 distinct values on a
1,500-bar synthetic walk with no repeats or degenerate input, confirming the bound is hit
exactly, not an artefact of insufficient data. `tests/test_a101_058.py::
test_fires_and_is_not_constant` asserts `1 < nunique <= 6` rather than reusing other
ports' three-digit floor, so this property is pinned rather than silently tightened.
Whether 6 discrete levels still carry useful information for a tree-based consumer (vs.
e.g. an `ORD` tag) is a Gate E / downstream-model question, not resolved here.

## Wiring

`Category` **276 → 277** (`volume` **31 → 32**); `df.ta.<name>()` accessor count **284 →
285**. Touch points: `pandas_ta/volume/a101_058.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_058` (accessor), `tests/test_a101_058.py` (tests). `README.md`'s
headline and `volume (32)` row, and `docs/IndicatorDictionary.md` (regenerated), both
updated and checked by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s
running tag count updated **621 → 622 / 265 → 266 `SF`** (`A101_058_4_8_6` probes cleanly
at the dictionary's 600-bar synthetic frame -- the 15-bar warm-up fits trivially);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (276 → 277) and `CATEGORY_BUCKETS["volume"]`
updated (31 → 32), since that test pins the exact per-category count.

## Receipt (pending)

Gate E has not run yet. A future receipt session records the launcher's run in
`docs/gate_e_ledger.csv` and fills in this section with the measured verdict, max|ρ| and
comparator, deciding ship vs. revert per CLAUDE.md's bands. The issue's own 2026-10-24
prototype screen (`a101_058` in `docs/issues/screen/candidates.csv`) measured the
PROTOTYPE (not this port) at max|ρ| 0.1913 vs `Dist_to_hma_pct_Pctl` on the manifest
(n=380,892), top-5 per-frame max median 0.1879 → SHIP, with the fork-overlap stage-2 max
at 0.1906 vs `smi:SMIo_5_20_5` -- stated here as the issue's own prior evidence only, not
re-asserted as this port's result until the launcher's run on the actual module confirms
it. Note the prototype used Kakushadze's literal `vwap` proxy conversion per the issue's
`cand` field; this port's `ts_rank` convention (count-of-less-or-equal, disclosed above as
an assumption) was not part of what the prototype screen measured, since the screen ran
on `ind_screen.py`'s own implementation, not this module.
