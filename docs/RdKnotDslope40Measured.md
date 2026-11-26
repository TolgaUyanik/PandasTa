# Slope change at the best one-knot spline break (40) — measured (`rd_knot_dslope_40`)

Issue #175 (RD-KNOT-DSLOPE-40), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:smxy8i (2022-02-07)
https://www.reddit.com/r/algotrading/comments/smxy8i/ — the poster's words: "Linear splines
with 1 knot. Fit that model while trying all possible values for the knot and record the
mean squared error in each knot/model." Claimed use: locate where a trend changes slope —
**not independently tested here.** The exact same post as issue #166's `rd_knot_pos_40`
(`pandas_ta/statistics/rd_knot_pos_40.py`): that port ships WHERE the best knot sits (its
age); this port ships HOW MUCH the fitted slope changes there — the hinge coefficient
itself. A Reddit post is not a script, so there is no source line number to cite; Gate A
below reads the formula directly from the issue's own restatement (its own instruction:
"Gate A starts from the source formula, not the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_knot_dslope_40`, which is mathematically the
same reading but is not what Gate A cites). The 40-bar window and the 5..34 knot search
range are not in the poster's words — the issue discloses both as the prototype's own
choice, kept here as the `length`/`knot_margin` defaults, not hard-coded, matching
`rd_knot_pos_40`'s own convention.

**Status:** Gates A, B, C, D, F measured, SHIP; Gate E owed again (round-2 review, 2026-11-26 —
see Decision 6: the module's arithmetic changed to get a real Gate D bit-identical claim, which
moves the module's sha1, so the Gate E run already on record no longer describes this tree and must
be re-run by issue-solver).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/rd_knot_dslope_40.py` | statistics | `RD_KNOT_DSLOPE_40_5` | continuous, both signs reachable (measured -0.0186..0.0198 across 11 synthetic frames below); NaN during warm-up |

Tests: `tests/test_rd_knot_dslope_40.py` (20 tests). Numbers: `python
docs/measure_rd_knot_dslope_40.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-26.

## Decisions

1. **Shares its knot search with `rd_knot_pos_40` (#166), reports a different quantity.**
   Both ports fit the identical continuous one-knot hinge model
   (`a + b*t + c*MAX(t-k,0)`) over the identical trailing window and keep the identical
   lowest-SSE knot; `rd_knot_pos_40` reports `(length-1-best)/(length-1)` (the knot's AGE),
   this port reports `c_best` (the knot's HINGE COEFFICIENT, i.e. the fitted slope AFTER the
   knot minus the slope BEFORE it — "change in log return per bar" per the issue's own
   scale-free form). The two modules do not share code (each ports its own basis builder),
   matching this fork's convention of one module per shipped column, but they are
   mathematically siblings and the module docstrings cross-reference each other.
2. **Two parameters, not a fixed window and knot range** — same decision as `rd_knot_pos_40`:
   the poster's words give only the model and the fitting rule, not a window length or knot
   search range, so `length` (default 40) and `knot_margin` (default 5) stay parameters.
3. **SSE, not MSE, is compared directly** — same equivalence as `rd_knot_pos_40`: every
   candidate knot's model has the same 3 free parameters over the same `length` points, so
   `MSE_k = SSE_k / (length - 3)` is minimised by exactly the same `k` that minimises `SSE_k`.
4. **A window with any non-finite `log(close)` reads NaN**, not an arbitrary knot's
   coefficient — the argmin over an all-NaN SSE row is not well-defined
   (`tests/test_rd_knot_dslope_40.py::test_nonfinite_window_reads_nan`).
5. **Column name carries both parameters**, `RD_KNOT_DSLOPE_{length}_{knot_margin}` — e.g.
   `RD_KNOT_DSLOPE_40_5` at defaults, `RD_KNOT_DSLOPE_20_3` at `length=20, knot_margin=3`.
6. **Bit-identical under a power-of-two price rescale, by fitting on a ratio, not raw `log`.**
   Round-1 review (this port's own `docs/reviews/auto-2026-11-26-rd-knot-dslope-40/`) shipped a
   version that fed the fit `log(close)` directly and could only measure a tiny tolerance
   (~1.8e-15) under x8/x64, on the argument that `LN` is transcendental so `LN(close*k) !=
   LN(close) + LN(k)` even at an exact power of two. That argument is true of *that
   implementation*, not of the column: the fork already has the fix, in `level_shift_size`
   (`pandas_ta/statistics/level_shift_size.py:51`, Decision 3 of
   `docs/LevelShiftSizeMeasured.md`) — a continuous-VALUE output (unlike `rd_knot_pos_40`'s
   discrete index, which only needs the ARGMIN stable) can still get bit-identical by fitting
   on `log(window / window's own first close)` instead of `log(window)`: under an
   exactly-representable rescale by `k`, multiplying by `k` is an exact exponent shift (no
   mantissa rounding), so both the numerator and denominator of the ratio are multiplied by
   the same exact factor and IEEE-754 division returns bit-identical results — and `LN` of a
   bit-identical input returns a bit-identical output. Round 2 (this review) adopts that device
   (`rd_knot_dslope_40.py:152,158`): OLS is invariant to the per-window additive shift the ratio
   introduces (same argument as before), so `c_best` itself is now measured bit-identical under
   x8/x64 (max abs diff 0.0, see Gate D) — not merely argued. A non-power-of-two rescale (x10,
   x3.7) still only gets the tiny-tolerance claim, since that division is not exact.

## Gate A — correctness

The issue's own formula (not the prototype — issue #175's explicit instruction), read
bar-by-bar in the module's docstring:

```
y = LN(close)
for each window of `length` bars (t = 0..length-1, t=0 the oldest bar):
    for each candidate knot k in [knot_margin, length-1-knot_margin]:
        model_k(t) = OLS fit of y on [1, t, MAX(t-k, 0)] -> coefficients a_k, b_k, c_k
        SSE_k = SUM((y - model_k)^2)
    best = argmin_k SSE_k
RD_KNOT_DSLOPE = c_best
```

A noiseless hand-derived fixture, chosen on paper before the module ran
(`tests/test_rd_knot_dslope_40.py::test_hand_derived_value`): log close rising with slope 1
for bars 0–5 then slope 3 for bars 5–9 — an EXACT continuous hinge with knot=5, slope change
`3 - 1 = 2`. At `length=10, knot_margin=2` (candidates 2..7), the module's output at the one
defined bar is `2.0` exactly (`python docs/measure_rd_knot_dslope_40.py`), matching the
hand-derived value to the bit — the knot=5 model reproduces the data with (near) zero
residual, far below any other candidate's.

Cross-checked against an independent per-window Python loop built straight from the formula
above (`np.linalg.lstsq` per candidate knot, keeping the winning knot's own hinge
coefficient, not read from the module) on a 300-bar synthetic log-price random walk
(length=40, knot_margin=5, 261 defined bars): NaN masks identical, **max |diff| 2.661e-15**
(`test_matches_an_independent_loop`, `python docs/measure_rd_knot_dslope_40.py`; the oracle
fits on `log(close)` directly rather than the module's ratio-to-first-bar form, so the two are
not expected to match to the bit, only to OLS's own invariance up to float noise).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic log-price walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1
  in both the base and the spliced series, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ...,
  1450, `python docs/measure_rd_knot_dslope_40.py`): **real module leaked at 0 of 28**.
- **The mutant (the final `pd.Series(out, index=close.index)` with a `.shift(-1)` appended,
  reading one bar into the future) is live** (differs from the real module on the
  unperturbed frame) **and leaked at 28 of the same 28 swept J values.** Pinned as `>= 14 of
  28` (a majority) rather than the exact count, since the issue-solver's own CPU-variant rule
  forbids pinning a bit-level count that could move with the runner's dispatched float
  kernels (`tests/test_rd_knot_dslope_40.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from the port session:

- **1,600-bar frame (seed 4):** 1,561 of 1,600 bars fire (39-bar warm-up); values range
  **-0.016534 to 0.016918** across **1,561 distinct values** — a continuous coefficient, not
  a discrete grid like `rd_knot_pos_40`'s age (every firing bar reads its own float, not one
  of a fixed set of 30).
- **10 independent 600-bar frames (seeds 100–109):** every frame fires on 561 of 600 bars
  (the fixed 39-bar warm-up) and reads 561 distinct values; every seed's min is negative and
  max is positive (ranges from -0.018623 to 0.019822 across the ten seeds) — both signs of
  slope change (steepening and flattening/reversing) are reachable, not a one-sided column.
- **A window with a non-finite `log(close)` reads NaN** by construction
  (`test_nonfinite_window_reads_nan`); not observed on the random synthetic frames above (no
  injected non-finite values there), which is expected, not a defect.
- **Real-data reachability** (non-NaN / non-zero counts on the 89-frame BIST pool) is left to
  the next Gate E run, not measured here: the 2026-11-26 run recorded below (`non_nan`
  395,378, `non_zero` 395,378 of 398,849, no `degenerate.csv` row) measured the PRE-Decision-6
  module (sha1 `de923cbcbbd6e0a32213680d8adde855750765dd`), not the ratio-fitted module this
  file now describes (sha1 below, Gate D); those counts are expected to carry over unchanged
  (NaN pattern and `0 < fires < n` are structural, not value-dependent) but are not re-claimed
  here until the re-run confirms it.

## Gate D — scale-free

- **Bit-identical under a power-of-two price rescale (x8/x64), tolerance under any other
  (x10/x3.7).** The fitted hinge model carries an intercept `a_k` with `t` and `MAX(t-k,0)` as
  the other two design columns; for a design matrix `X` whose first column is exactly `1`,
  `pinv(X) @ 1 = e_1` exactly (because `1` is literally `X`'s own first column and
  `pinv(X) @ X = I`), so adding a constant to `y` moves ONLY the intercept coefficient — `b_k`
  and `c_k` (hence every knot's SSE, the argmin knot, AND the reported `c_best`) are exactly
  unchanged in REAL-NUMBER arithmetic under any additive shift of `y`. The module fits on
  `y = log(window / window's own first close)` rather than `log(window)` directly (Decision 6,
  the `level_shift_size` device): a price rescale by an exactly-representable `k` multiplies
  both the ratio's numerator and denominator by the same exact factor (a power-of-two multiply
  only shifts the exponent, no mantissa rounding), so IEEE-754 division of the two returns
  bit-identical results, and `log` of a bit-identical input is bit-identical — so `c_best` is
  measured bit-identical, not merely tolerance-close, under x8/x64. A non-power-of-two rescale
  (x10, x3.7) is not exact at the division step, so that stays a tiny-tolerance claim.
- **Measured on the 1,600-bar seed-4 frame, 1,561 co-finite cells**
  (`python docs/measure_rd_knot_dslope_40.py`):

  | k | max abs diff | max rel diff |
  |---|---|---|
  | 8.0 | 0.0 | 0.0 |
  | 64.0 | 0.0 | 0.0 |
  | 10.0 | 6.072e-17 | 1.674e-14 |
  | 3.7 | 3.860e-17 | 1.975e-14 |

  x8/x64 are exact zero (`test_price_scale_is_bit_identical`, `==` comparison, not a
  tolerance). x10/x3.7 land near the float noise floor, tighter than the pre-Decision-6
  version's ~1.3e-15 (that version computed `log(close)` directly for every k, carrying more
  rounding even at the non-exact rescales).
  `tests/test_rd_knot_dslope_40.py::test_scale_stays_within_a_tiny_tolerance` bounds the x10/x3.7
  case at `rtol=1e-9, atol=1e-12` — a generous margin above the measured figures, not the
  measured figures themselves, per the issue-solver's own CPU-variant rule (the exact last bit
  is the CPU's dispatched kernels' call, not this module's logic).
- `0 < fires < n`, not constant: 1,561 of 1,600 bars fire on the 1,600-bar frame above, 1,561
  distinct values, min -0.016534 and max 0.016918 (both signs reachable).

## Gate E — attribution

**Pending, run by issue-solver after this session.** A run already happened once
(`is175-rd_knot_dslope_40-eef638c4`, 2026-11-26) and was recorded in `docs/gate_e_ledger.csv`:
89 ALTPORT-1 BIST frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal
(AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS), `RD_KNOT_DSLOPE_40_5` max |ρ| 0.7012077500109714 vs
`MACD_Hist_ATR` (per-frame max median 0.7235662692561251 vs `MACDAS_Signal`), n 395,378,
verdict SHIP. That run measured the module at sha1
`de923cbcbbd6e0a32213680d8adde855750765dd` — the version that fed the fit `log(close)`
directly (pre-Decision-6). This review round changed the module's arithmetic to get a real
Gate D bit-identical claim (Decision 6), which moved the module to sha1
`f48afaf88e993671fa92390428b7bee35b8b6406` and so moved the output fingerprint too
(`log(window/window[0])` computes different float bits than `log(window)`, even though both
are the same `c_best` up to float noise, per Gate A/D above). The ledger row described the OLD module and has been
removed from `docs/gate_e_ledger.csv` rather than left stale (CLAUDE.md: "a deleted row counts
as owed too") — `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is expected to fail/skip again until issue-solver re-runs Gate E on this tree and a receipt
session re-records it. Given the arithmetic change is bit-noise-level (not a formula change),
the SHIP verdict and the ~0.70 ρ are expected to reproduce closely, but that is not claimed
here until measured.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_knot_dslope_40.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,614 passed, 7 skipped, 1 failed** — round-2 review re-run, after Decision 6's arithmetic
change moved the module's sha1 and the stale ledger row was deleted (Gate E above);
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails here (no
`GATE_E_PENDING_OK` locally) — expected, per the issue-solver's own rule ("Gate E owed, not
failed"; the launcher's CI sets that flag and turns the same failure into a skip).
`tests/test_rd_knot_dslope_40.py` alone: 20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_knot_dslope_40_cpu.py` — **20 passed** (just
`tests/test_rd_knot_dslope_40.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 401 → 402 (`tests/test_altport2_ports.py`).
- README: 401 → 402 registered, 409 → 410 callable, statistics (82) → (83).
- `docs/MLCompanionContract.md`: 746 → 747 tagged and 375 → 376 `SF` (newest first in the
  chain). `RD_KNOT_DSLOPE_40_5` tags `SF` because the fitted hinge model's intercept makes
  the reported coefficient invariant to any additive shift of `log(close)` in exact
  arithmetic — fed `log(window / window's own first close)` (Decision 6), so measured
  bit-identical under x8/x64 and within a tiny tolerance under x10/x3.7.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package after Decision
  6's arithmetic change: `git diff docs/IndicatorDictionary.md` is empty (the column's tag,
  warm-up and range-shape classification are unaffected by a same-value-up-to-float-noise
  change in how it is computed).
- `Category`: `rd_knot_dslope_40` is placed alphabetically between `rd_gap_fill_rate_60` and
  `rd_knot_pos_40` in `statistics`.
