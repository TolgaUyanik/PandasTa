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

**Status:** Gates A–F measured. Gate E: DISCLOSE_GAP (max |ρ| 0.8343 vs `cfo_ta_Pctl`), ships.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/rd_quadfit_resid_20.py` | statistics | `RD_QUADFIT_RESID_20` | unbounded (z-score-like); measured [-2.83, 2.76] across 11 synthetic frames, or NaN |

Tests: `tests/test_rd_quadfit_resid_20.py` (20 tests). Numbers: `python
docs/measure_rd_quadfit_resid_20.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

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
3. **Gate D is NOT bit-identical under a power-of-two price rescale — measured, and this is
   the headline finding of this port's gates.** The fitted quadratic has an intercept, so in
   EXACT (real-number) arithmetic any additive shift of `log(close)` leaves every residual
   unchanged, and a power-of-two rescale of `close` adds an exact constant to `log(close)`.
   But unlike `stdev` (a sum-of-squared-deviations reduction on the RAW, un-logged price,
   where an exact power-of-two multiply is bit-preserving all the way through — see
   `rd_std_ratio_20_60`) or `rd_knot_pos_40` (an ARGMIN over a fixed integer grid, insensitive
   to a last-bit nudge unless it flips an already-tied argmin), this port's output is a
   CONTINUOUS ratio built from `np.log` of the rescaled price itself. `log(8*x)` is not
   bit-identical to `log(x) + log(8)` in IEEE-754 doubles even for an exact power-of-two `8`
   — `log` is transcendental, not scale-preserving the way an exact multiply or a
   correctly-rounded `sqrt` of an exact square is. Measured: 0 of 1,581 co-finite cells
   bit-identical under x8/x64, max relative difference ~5e-9 — the SAME order of magnitude as
   a non-power-of-two rescale (x10/x3.7, also ~2-3e-9), not meaningfully smaller. Both stay
   well inside the test's generous `rtol=1e-6` bound.
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
1.807e-12** (`test_matches_an_independent_loop`, `python docs/measure_rd_quadfit_resid_20.py`).

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

Synthetic, from the port session (real-data reachability is part of the owed Gate E run):

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

## Gate D — scale-free

- **Power-of-two (x8, x64): measured NOT bit-identical** — 0 of 1,581 co-finite cells
  bit-identical, max absolute difference 8.3e-12 (x8) / 1.7e-11 (x64), max RELATIVE difference
  2.6e-9 (x8) / 5.1e-9 (x64) (`python docs/measure_rd_quadfit_resid_20.py`). See Decision 3
  above for why: the fitted quadratic's intercept makes the residual invariant to an additive
  shift of `log(close)` only in exact real-number arithmetic, and `np.log` of a
  power-of-two-rescaled `close` is not itself bit-preserving the way an exact multiply or a
  correctly-rounded `sqrt` of an exact square is. `tests/test_rd_quadfit_resid_20.py::test_power_of_two_scale_stays_within_a_tiny_tolerance`
  bounds this at a generous `rtol=1e-6` (the measured noise floor is ~5e-9, two orders of
  magnitude below the bound) rather than asserting bit-identity, per the issue-solver's own
  CPU-variant rule (a bit-level claim here would not survive a different CPU's dispatched
  `log` kernel).
- **Non-power-of-two (x10, x3.7): measured within the SAME order of magnitude** — max
  absolute difference 9.5e-12 (x10) / 5.3e-12 (x3.7), max relative difference 2.8e-9 (x10) /
  1.6e-9 (x3.7) on the same 1,581 co-finite cells. Not meaningfully larger than the
  power-of-two case — both are dominated by `log`'s own rounding, not by the extra last-bit
  rounding a non-power-of-two multiply adds on top.
  `tests/test_rd_quadfit_resid_20.py::test_other_scales_stay_within_a_tiny_tolerance` uses the
  same `rtol=1e-6` bound.
- `0 < fires < n`, not constant: 1,581 of 1,600 bars fire on the 1,600-bar frame above, 1,581
  distinct values, min -2.6635 and max 2.5259 — both signs reached, so a constant column
  cannot pass.

**Run on the port itself** (not the prototype), issue-solver, run id
`is180-rd_quadfit_resid_20-457a93c0`, module `pandas_ta.statistics.rd_quadfit_resid_20`,
89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358
`ml_features` manifest), canary bit-equal on AKBNK.IS / BIENY.IS / AGHOL.IS / SASA.IS,
`pandas_ta_src_sha1` `6c03de9c7e550be764e9234f0bbfd57af5212a78`:

| column | max \|ρ\| | against | n | perframe max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_QUADFIT_RESID_20` | 0.8343003635723028 | `cfo_ta_Pctl` (manifest) | 392,886 | 0.8356157515953884 | **DISCLOSE_GAP** |

Next comparator (`compute_all`): `cfo` 0.8030023191691446, n = 397,158. Band: `r3-perframe-0.90`
— DISCLOSE_GAP is 0.80 ≤ ρ < 0.90, below the 0.90 STRUCK line (pooled 0.8343, perframe max
median 0.8356, neither reaches 0.90) — **ships, disclosed**, not reverted. Matches the screen
prototype's own quoted figures (0.8343 / 0.8356 vs `cfo_ta_Pctl`) to the digit: the port is
mathematically the same reading as the prototype, measured independently on the port's own code.
Recorded: `docs/gate_e_ledger.csv`, measured 2026-11-27.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_quadfit_resid_20.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,726 passed, 7 skipped** (receipt session, after the Gate E ledger row above was recorded).
`tests/test_rd_quadfit_resid_20.py` alone: 20 passed.

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
  measured NOT bit-identical at the IEEE-754 level (see Decision 3), but within the same
  tight tolerance for both a power-of-two and a non-power-of-two rescale, confirmed by the
  dictionary generator's own probe frame (`docs/IndicatorDictionary.md`'s
  `rd_quadfit_resid_20` row), not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is the
  `rd_quadfit_resid_20` row (`RD_QUADFIT_RESID_20` SF, 19-bar warm-up), the three header
  counts, the statistics section count, the no-transform-needed shortlist, and nothing else
  (checked: `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_quadfit_resid_20` is placed alphabetically between `rd_knot_pos_40` and
  `skew` in `statistics`.
- Module sha1 (LF-normalised, for the later `docs/gate_e_ledger.csv` row):
  `c64bc78ae2f721e66ede3208242cd38635fb4d01`.
