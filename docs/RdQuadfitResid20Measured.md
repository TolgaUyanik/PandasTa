# Last-bar residual of a 20-bar quadratic fit, in residual sd — measured (`rd_quadfit_resid_20`)

Issue #180 (RD-QUADFIT-RESID-20), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:vgulql (2022-06-20)
https://www.reddit.com/r/algotrading/comments/vgulql/ — the poster's words: "(observed -
predicted) of a 2nd-order polynomial fit on a trailing window." Claimed use: "The reason
this works for breakpoint detection is that a sudden reversal can not be captured by a low
order polynomial" — detect a trend reversal when the fit error grows — **not independently
tested here.** A Reddit post is not a script, so there is no source line number to cite;
Gate A below reads the formula directly from the issue's own restatement (its own
instruction: "Gate A starts from the source formula, not the prototype"), not from the
screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `rd_quadfit_resid_20`, which is
mathematically the same reading but is not what Gate A cites). The 20-bar window, the log
transform, and "residual over the window's residual sd" (population, ddof=0) are not in the
poster's words — the issue discloses them as the prototype's own scale-free form, kept here
as the `length` default and the fixed ddof=0 recipe, following the same pattern as issue
#179's "p = 20" / "3p" and issue #166's "40 bars, knots 5..34."

**Status:** Gates A-F measured. Ships: DISCLOSE_GAP, not STRUCK.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/rd_quadfit_resid_20.py` | statistics | `RD_QUADFIT_RESID_20` | unbounded (z-score-like); measured [-2.83, 2.76] across 11 synthetic frames, or NaN |

Tests: `tests/test_rd_quadfit_resid_20.py` (20 tests). Numbers: `python
docs/measure_rd_quadfit_resid_20.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27 (round 2, after Decision 3's Gate D fix).

## Decisions

1. **One parameter, not two.** The poster's words give only the model (a 2nd-order
   polynomial / quadratic OLS fit) and the residual definition (observed minus predicted at
   the last bar); the issue's own text discloses "on log close, 20 bars" as the screen
   prototype's own choice. This port keeps `length` (default 20) as a parameter, matching
   the fork's convention for every other rolling-window indicator, rather than hard-coding
   it; a `length < 4` raises (a quadratic's 3 fitted parameters leave no residual degree of
   freedom below that, so every window would fit exactly and the output would be `0/0 = NaN`
   on every bar — a silent all-NaN column would be worse than a loud error).
2. **Residual sd is POPULATION (ddof=0), not pandas' ddof=1 default.** The poster's words
   name no estimator for "residual sd." The only concrete recipe the issue discloses is the
   screen prototype's own `_quad_resid` helper, `R.std(1)` — numpy's `.std()` default,
   ddof=0 — so this port reads that off the prototype the same way issue #179's `std` /
   `mean` were read off its own helpers.
3. **Gate D round 1 fed the fit `log(close)` directly and measured NOT bit-identical under a
   power-of-two price rescale** (0 of 1,581 co-finite cells bit-identical, max relative
   difference ~5e-9), defended on the argument that `log(8*x)` is not bit-identical to
   `log(x) + log(8)` in IEEE-754 doubles even for an exact power-of-two `8` — `log` is
   transcendental, not scale-preserving the way an exact multiply or a correctly-rounded
   `sqrt` of an exact square is. Round 1 review rejected that defence: this fork already has
   the fix, `rd_knot_dslope_40` (`pandas_ta/statistics/rd_knot_dslope_40.py`), a continuous
   value from an intercept-carrying OLS fit on log close just like this column, which was
   forced through the identical argument and now measures bit-identical by fitting on
   `log(window / window's own first close)` — the `level_shift_size` ratio-to-first-bar device
   — instead of `log(window)` directly. **Round 2 adopts that device here.** The fitted
   quadratic has an intercept, so in EXACT (real-number) arithmetic any additive shift of
   `log(close)` leaves every residual unchanged (the argument that was already true, just
   applied to the wrong implementation); under an exactly-representable rescale by `k`, both
   the numerator and denominator of the ratio are multiplied by the same exact factor (a
   power-of-two multiply only shifts the exponent), so IEEE-754 division returns bit-identical
   results, and `log` of a bit-identical input returns a bit-identical output. **Measured: 0 of
   1,581 co-finite cells MISMATCH under x8/x64 — bit-identical**, not merely within tolerance.
   A non-power-of-two rescale (x10/x3.7) is not exact at the division step, so that stays a
   tiny-tolerance claim, and it is now three orders of magnitude tighter than round 1's: max
   relative difference 2.756e-12 (x10) / 3.135e-12 (x3.7), well inside the test's `rtol=1e-6`
   bound.
4. **A window with any non-finite `log(close)` reads NaN**, not an arbitrary fitted value —
   masked explicitly (`tests/test_rd_quadfit_resid_20.py::test_nonfinite_window_reads_nan`).
5. **Column name carries the one parameter**, `RD_QUADFIT_RESID_{length}` — e.g.
   `RD_QUADFIT_RESID_20` at the default, `RD_QUADFIT_RESID_40` at `length=40`.

## Gate A — correctness

The issue's own formula (not the prototype — issue #180's explicit instruction), read
bar-by-bar in the module's docstring:

```
y = LN(close)
for each window of `length` bars (t = 0..length-1, t=0 the oldest bar):
    a, b, c = OLS fit of y on [1, t, t**2]
    resid(t) = y(t) - (a + b*t + c*t**2)
RD_QUADFIT_RESID = resid(length-1) / STDEV(resid(0..length-1), ddof=0)
```

A hand-derived fixture, chosen on paper before the module ever ran
(`tests/test_rd_quadfit_resid_20.py::test_hand_derived_value`): for 4 equally spaced points
the quadratic design's residual-maker is EXACTLY the classic orthogonal cubic contrast
`v = (-1, 3, -3, 1)` (orthogonal to the constant, linear and quadratic design columns for ANY
equally spaced grid — checked directly against this module's own `t = 0, 1, 2, 3` by hand).
Chosen `y = (0, 1/9, 4/9, 2)` gives `v.y = 1`, `v.v = 20`, so `resid = 0.05 * v`, last residual
`0.05`, population sd of `(-0.05, 0.15, -0.15, 0.05)` is `sqrt(0.0125)`, and the ratio
simplifies exactly to `1/sqrt(5) = 0.4472135954999579`. Module's measured output at the one
defined bar: `0.4472135954999547` — matches to **3.2e-15** (float round-trip through `exp`
then `log`, not the module's own arithmetic, which is why it is not exactly `0.0`).

Cross-checked against an independent per-window Python loop built straight from the formula
above (`np.linalg.lstsq` per window, not read from the module) on a 300-bar synthetic
log-price random walk (length=40, 261 defined bars): NaN masks identical, **max |diff|
9.442e-13** (`test_matches_an_independent_loop`, `python docs/measure_rd_quadfit_resid_20.py`;
the oracle fits on `log(close)` directly rather than the module's ratio-to-first-bar form, so
the two are not expected to match to the bit, only to OLS's own invariance up to float noise —
same caveat as `rd_knot_dslope_40`'s own cross-check).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic log-price walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1
  in both the base and the spliced series, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ...,
  1450, `python docs/measure_rd_quadfit_resid_20.py`): **real module leaked at 0 of 28**.
- **The mutant (the final `pd.Series(out, index=close.index)` with a `.shift(-1)` appended,
  reading one bar into the future) is live** (differs from the real module on the
  unperturbed frame) **and leaked at 28 of the same 28 swept J values** — every one, since a
  continuous residual ratio moves on almost every bar once shifted.
  `tests/test_rd_quadfit_resid_20.py::test_lookahead_mutant_is_caught` pins `>= 14 of 28` (a
  majority) rather than the exact count, since the issue-solver's own CPU-variant rule
  forbids pinning a bit-level count that could move with the runner's dispatched float
  kernels.

## Gate C — reachability

Synthetic, from the port session:

- **1,600-bar frame (seed 4):** 1,581 of 1,600 bars fire (19-bar warm-up); values range
  -2.6635 to 2.5259 across **1,581 distinct values** (a continuous ratio, not a discrete
  grid), both signs reached.
- **10 independent 600-bar frames (seeds 100–109):** every frame fires on 581 of 600 bars
  (the fixed 19-bar warm-up) and reads 581 distinct values; per-seed min ranges -2.8327 to
  -2.5325, max ranges 2.3376 to 2.7615 — both signs reachable on every independent draw, not
  a narrow subset.
- **A window with a non-finite `log(close)` reads NaN** by construction
  (`test_nonfinite_window_reads_nan`); not observed on the random synthetic frames above (no
  injected non-finite values there), which is expected, not a defect.
- **Real-data reachability**, round 2 run on the fixed module (`is180-rd_quadfit_resid_20-2e3d7c9e`,
  2026-11-27, `pandas_ta_src_sha1` `e65f49cab1a0f9fb36737d6a031529cbc642f35b`): `non_nan`
  397,158, `non_zero` 397,158 of 398,849 pooled bars across the 89 ALTPORT-1 frames
  (`overlap_max.csv`) — unchanged from round 1, confirming the Gate D fix did not move
  reachability.

## Gate D — scale-free

- **Power-of-two (x8, x64): measured BIT-IDENTICAL** — 0 of 1,581 co-finite cells mismatch,
  max absolute difference 0.0, max relative difference 0.0
  (`python docs/measure_rd_quadfit_resid_20.py`). See Decision 3 above: the module fits on
  `log(window / window's own first close)` rather than `log(window)` directly, so a
  power-of-two rescale multiplies both the ratio's numerator and denominator by the same exact
  factor (only the exponent shifts), IEEE-754 division returns bit-identical results, and
  `log` of a bit-identical input is bit-identical — and the fitted quadratic's intercept makes
  OLS invariant to the per-window additive shift that ratio introduces, in exact arithmetic.
  `tests/test_rd_quadfit_resid_20.py::test_power_of_two_scale_is_bit_identical` asserts this
  with `np.testing.assert_array_equal`, not a tolerance.
- **Non-power-of-two (x10, x3.7): tolerance, not bit-identity** — that rescale is not exact at
  the division step, so the ratio itself picks up a last-bit difference before `log` is even
  called. Measured max absolute difference 4.452e-14 (x10) / 3.408e-14 (x3.7), max relative
  difference 2.756e-12 (x10) / 3.135e-12 (x3.7) on the same 1,581 co-finite cells — three
  orders of magnitude tighter than round 1's pre-fix `log(close)` form (~2.8e-9 / ~1.6e-9),
  since the ratio-to-first-bar device also shrinks the non-exact case's rounding, not only the
  exact one's. `tests/test_rd_quadfit_resid_20.py::test_other_scales_stay_within_a_tiny_tolerance`
  bounds this at a generous `rtol=1e-6`, per the issue-solver's own CPU-variant rule (the exact
  last bit is the CPU's dispatched kernels' call, not this module's logic).
- `0 < fires < n`, not constant: 1,581 of 1,600 bars fire on the 1,600-bar frame above, 1,581
  distinct values, min -2.6635 and max 2.5259 — both signs reached, so a constant column
  cannot pass.

## Gate E — attribution

Round 3 (receipt session), run by issue-solver on the HEAD commit (module unchanged since
round 2): `is180-rd_quadfit_resid_20-2dc6c0ac` (2026-11-27), module
`pandas_ta.statistics.rd_quadfit_resid_20`, 89 ALTPORT-1 frames, 398,849 pooled bars, 687
comparators (329 `compute_all` + 358 `ml_features` manifest), canary bit-equal on AKBNK.IS /
BIENY.IS / AGHOL.IS / SASA.IS, `pandas_ta_src_sha1` `05efa633fae04a9a039a182c6d42ad69d18be5b8`
(differs from round 2's `e65f49ca...` because unrelated files changed elsewhere in the tree
between the two runs; `module_sha1` — the only thing this port owns — is unchanged,
`724c0d4c13c75836f3bbbccf4e6c3f9ab2b4d973`):

| column | max \|ρ\| | against | n | perframe max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_QUADFIT_RESID_20` | 0.834300363578934 | `cfo_ta_Pctl` (manifest) | 392,886 | 0.8356157515953884 | DISCLOSE_GAP |

Next comparator (`compute_all`): `cfo` 0.8030023191927524, n = 397,158. Identical to round 2's
figures (0.834300363578934 / 0.8356157515953884) to every digit shown — this round re-runs the
unchanged module and confirms the result, it does not remeasure a code change. **Band:
DISCLOSE_GAP (0.80 ≤ ρ < 0.90), not STRUCK** — ships per `docs/gate_e_ledger.csv`'s recorded
verdict (ledger run `is180-rd_quadfit_resid_20-2dc6c0ac`).

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_quadfit_resid_20.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,726 passed, 7 skipped, 0 failed** -- round-3 receipt session, after recording the round-3
Gate E ledger row (`is180-rd_quadfit_resid_20-2dc6c0ac`, DISCLOSE_GAP, numbers unchanged from
round 2). `tests/test_rd_quadfit_resid_20.py` alone: 20 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub runner
without AVX-512 — the four features issue-solver's rules name, not this machine's full
dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_rd_quadfit_resid_20_cpu.py` — **20 passed** (just
`tests/test_rd_quadfit_resid_20.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 414 → 415 (`tests/test_altport2_ports.py`).
- README: 414 → 415 registered, 422 → 423 callable, statistics (83) → (84).
- `docs/MLCompanionContract.md`: 759 → 760 tagged and 385 → 386 `SF` (newest first in the
  chain). `RD_QUADFIT_RESID_20` tags `SF` because the fitted quadratic's intercept makes the
  output invariant to any additive shift of `log(close)` in exact real-number arithmetic —
  measured BIT-IDENTICAL at the IEEE-754 level under a power-of-two rescale (Decision 3),
  within a tight tolerance under a non-power-of-two one, confirmed by the dictionary
  generator's own probe frame (`docs/IndicatorDictionary.md`'s `rd_quadfit_resid_20` row), not
  merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is the
  `rd_quadfit_resid_20` row (`RD_QUADFIT_RESID_20` SF, 19-bar warm-up), the three header
  counts, the statistics section count, the no-transform-needed shortlist, and nothing else
  (checked: `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_quadfit_resid_20` is placed alphabetically between `rd_knot_pos_40` and
  `skew` in `statistics`.
- Module sha1 (LF-normalised, for the later `docs/gate_e_ledger.csv` row, round 3 after
  the round-2 pre-push review's docstring-currency fixes -- the Gate E numbers below are
  unchanged, the module text is not): `724c0d4c13c75836f3bbbccf4e6c3f9ab2b4d973` (measured,
  `python docs/measure_rd_quadfit_resid_20.py`).
