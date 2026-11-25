# Age of the best one-knot spline break (40) — measured (`rd_knot_pos_40`)

Issue #166 (RD-KNOT-POS-40), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:smxy8i (2022-02-07)
https://www.reddit.com/r/algotrading/comments/smxy8i/ — the poster's words: "Linear splines
with 1 knot. Fit that model while trying all possible values for the knot and record the
mean squared error in each knot/model." Claimed use: locate where a trend changes slope —
**not independently tested here.** A Reddit post is not a script, so there is no source line
number to cite; Gate A below reads the formula directly from the issue's own restatement
(its own instruction: "Gate A starts from the source formula, not the prototype"), not from
the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_knot_pos_40`, which is
mathematically the same reading but is not what Gate A cites). The 40-bar window and the
5..34 knot search range are not in the poster's words — the issue discloses both as the
prototype's own choice, kept here as the `length`/`knot_margin` defaults, not hard-coded.

**Status:** Gates A–D measured. **Gate E: pending, run by issue-solver after this session.**

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/rd_knot_pos_40.py` | statistics | `RD_KNOT_POS_40_5` | `[0.0, 1.0]` or NaN, 30 discrete levels at defaults |

Tests: `tests/test_rd_knot_pos_40.py` (20 tests). Numbers: `python
docs/measure_rd_knot_pos_40.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **Two parameters, not a fixed window and knot range.** The poster's words give only the
   model (a one-knot continuous piecewise line) and the fitting rule (lowest MSE), with no
   window length or knot search range; the issue's own text discloses "40 bars, knots 5..34"
   as the screen prototype's own choice. This port keeps both as parameters — `length`
   (default 40) and `knot_margin` (default 5, so candidate knots are `[knot_margin,
   length-1-knot_margin]` = `[5, 34]` at defaults) — rather than hard-coding either, matching
   the fork's convention for every other rolling-window indicator (`rd_gap_fill_rate_60`'s
   `length`/`min_gap`).
2. **SSE, not MSE, is compared directly.** Every candidate knot's model has the same 3 free
   parameters (intercept, slope, hinge coefficient) fit over the same `length` points, so
   `MSE_k = SSE_k / (length - 3)` is minimised by exactly the same `k` that minimises `SSE_k`
   — the issue's own equivalence, not a new assumption. This port computes `SSE_k` only.
3. **The output is DISCRETE, not a free-running continuous ratio.** Because the knot itself
   is a point on a fixed integer grid (`length - 2*knot_margin` candidates, 30 at defaults),
   `RD_KNOT_POS_40_5` can only ever take one of those 30 values — measured directly: every
   synthetic frame below reads exactly **30 distinct values**, `{0.1282, 0.1538, ..., 0.8718}`
   in steps of `1/39`. This is unlike `rd_gap_fill_rate_60`'s continuous share; it reads more
   like a quantised position than a smooth statistic, though it is still a genuine
   scale-free `[0, 1]` fraction, not a small integer count (`ORD`) or a flag (`BIN`).
4. **A window with any non-finite `log(close)` reads NaN**, not an arbitrary knot's age —
   the argmin over an all-NaN SSE row is not well-defined, so this port masks those rows
   explicitly rather than trusting whatever `numpy.argmin` happens to return on an all-NaN
   input (`tests/test_rd_knot_pos_40.py::test_nonfinite_window_reads_nan`).
5. **Column name carries both parameters**, `RD_KNOT_POS_{length}_{knot_margin}` — e.g.
   `RD_KNOT_POS_40_5` at defaults, `RD_KNOT_POS_20_3` at `length=20, knot_margin=3` —
   following the fork's convention of encoding every parameter that changes the output in
   the column name (`tests/test_rd_knot_pos_40.py::test_custom_length_and_knot_margin_in_name`).

## Gate A — correctness

The issue's own formula (not the prototype — issue #166's explicit instruction), read
bar-by-bar in the module's docstring:

```
y = LN(close)
for each window of `length` bars (t = 0..length-1, t=0 the oldest bar):
    for each candidate knot k in [knot_margin, length-1-knot_margin]:
        model_k(t) = OLS fit of y on [1, t, MAX(t-k, 0)]      (continuous hinge)
        SSE_k = SUM((y - model_k)^2)
    best = argmin_k SSE_k
RD_KNOT_POS = (length - 1 - best) / (length - 1)
```

A noiseless hand-derived fixture, chosen on paper before the module ran
(`tests/test_rd_knot_pos_40.py::test_hand_derived_value`): log close rising with slope 1 for
bars 0–5 then slope 3 for bars 5–9 — an EXACT continuous hinge with knot=5. At `length=10,
knot_margin=2` (candidates 2..7), the module's output at the one defined bar is
`0.4444444444444444`, matching the hand-derived `4/9 = 0.4444444444` to 1e-9 — the knot=5
model reproduces the data with (near) zero residual, far below any other candidate's.

Cross-checked against an independent per-window Python loop built straight from the formula
above (`np.linalg.lstsq` per candidate knot, not read from the module) on a 300-bar synthetic
log-price random walk (length=40, knot_margin=5, 261 defined bars): NaN masks identical,
**max |diff| 0.000e+00** (`test_matches_an_independent_loop`,
`python docs/measure_rd_knot_pos_40.py`).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic log-price walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1
  in both the base and the spliced series, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ...,
  1450, `python docs/measure_rd_knot_pos_40.py`): **real module leaked at 0 of 28**.
- **The mutant (the final `pd.Series(out, index=close.index)` with a `.shift(-1)` appended,
  reading one bar into the future) is live** (differs from the real module on the
  unperturbed frame) **and leaked at 25 of the same 28 swept J values.** Pinned as `>= 14 of
  28` (a majority) rather than the exact count, since the issue-solver's own CPU-variant
  rule forbids pinning a bit-level count that could move with the runner's dispatched float
  kernels (`tests/test_rd_knot_pos_40.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from this session (real-data reachability on BIST frames is Gate E's job, run by
issue-solver after this session):

- **1,600-bar frame (seed 4):** 1,561 of 1,600 bars fire (39-bar warm-up); values range
  0.1282–0.8718 across **30 distinct values** — the full discrete grid at defaults
  (`length=40, knot_margin=5` gives `length - 2*knot_margin = 30` candidate knots), never
  exactly 0 or 1 (the margin excludes the window's two ends from the candidate set by
  construction).
- **10 independent 600-bar frames (seeds 100–109):** every frame fires on 561 of 600 bars
  (the fixed 39-bar warm-up) and reads all 30 distinct values, min 0.1282 and max 0.8718 on
  every seed — the full grid is reachable, not a narrow subset, across independent draws.
- **A window with a non-finite `log(close)` reads NaN** by construction
  (`test_nonfinite_window_reads_nan`); not observed on the random synthetic frames above
  (no injected non-finite values there), which is expected, not a defect.

## Gate D — scale-free

- **Power-of-two (x8, x64): bit-identical, 0 mismatches on 1,561 co-finite cells**
  (`tests/test_rd_knot_pos_40.py::test_power_of_two_scale_is_bit_identical`,
  `python docs/measure_rd_knot_pos_40.py`). The fitted hinge model carries an intercept, so
  in exact arithmetic any additive shift of `log(close)` leaves every knot's SSE — and so the
  argmin knot — unchanged; a power-of-two price rescale adds the constant `LN(k)` to every
  bar before this port's own OLS fit runs.
- **Non-power-of-two (x10, x3.7): ALSO measured 0 mismatches on the same 1,561 co-finite
  cells** on this frame — reported as a measured bound, not a mathematical guarantee the way
  the power-of-two case is (an isolated bar within ~1e-15 relative of flipping an already-tied
  argmin between two adjacent knots could in principle move under a non-power-of-two
  rescale's extra last-bit rounding). `tests/test_rd_knot_pos_40.py::test_other_scales_stay_within_a_tiny_tolerance`
  bounds this at 1% of valid bars rather than asserting exactly 0, per the issue-solver's own
  CPU-variant rule.
- `0 < fires < n`, not constant: 1,561 of 1,600 bars fire on the 1,600-bar frame above, 30
  distinct values, min 0.1282 and max 0.8718 both strictly inside `[0, 1]`.

## Gate E — attribution

**Pending, run by issue-solver after this session.** The harness
(`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.statistics.rd_knot_pos_40`) needs the private Backtesting engine and the 89-frame
BIST cache, neither available in this worktree; this port's own rules forbid running or
reading it here. `module_sha1` for the ledger row (`python docs/measure_rd_knot_pos_40.py`):
`64f0f86a9a55b7f154711d22abc454b7c9199846`.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_knot_pos_40.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,558 passed, 7 skipped, 1 failed** — the one failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected before the
ledger row exists per this session's own rules ("Gate E owed, not a finding"); a later
receipt session records the row after the launcher's Gate E run, which resolves it.
`tests/test_rd_knot_pos_40.py` alone: 20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_knot_pos_40_cpu.py` — **20 passed** (just
`tests/test_rd_knot_pos_40.py`; the ledger/readme/wiring modules above are not CPU-sensitive
and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 394 → 395 (`tests/test_altport2_ports.py`).
- README: 394 → 395 registered, 402 → 403 callable, statistics (81) → (82).
- `docs/MLCompanionContract.md`: 739 → 740 tagged and 370 → 371 `SF` (newest first in the
  chain). `RD_KNOT_POS_40_5` tags `SF` because the fitted hinge model's intercept makes the
  output invariant to any additive shift of `log(close)` — measured bit-identical under
  x8/x64 and (on this frame) x10/x3.7 as well, confirmed by the dictionary generator's own
  probe frame (`docs/IndicatorDictionary.md`'s `rd_knot_pos_40` row), not merely asserted
  here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_knot_pos_40` row (`RD_KNOT_POS_40_5` SF, 39-bar warm-up), the three header counts,
  the statistics section count, the no-transform-needed shortlist, and nothing else
  (checked: `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_knot_pos_40` is placed alphabetically between `rd_gap_fill_rate_60` and
  `skew` in `statistics`.
