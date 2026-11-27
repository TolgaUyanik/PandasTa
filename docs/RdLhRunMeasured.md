# Run length of consecutive lower highs — measured (`rd_lh_run`)

Issue #182 (RD-LH-RUN), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Trading:1gcotir (2024-10-26)
https://www.reddit.com/r/Trading/comments/1gcotir/; rd:algotrading:1b1qx3c (2024-02-27)
https://www.reddit.com/r/algotrading/comments/1b1qx3c/; rd:algotrading:1gcoq4m (2024-10-26)
https://www.reddit.com/r/algotrading/comments/1gcoq4m/; rd:Daytrading:1gcos5t (2024-10-26)
https://www.reddit.com/r/Daytrading/comments/1gcos5t/ — the poster's words: "After I get at
least 4 lower highs in a row, I place an order at the most recent high." Claimed use:
probability of a (long) reversal rises with the number of consecutive lower highs —
**not independently tested here.** Gate A reads the issue's own restatement of the formula
(its own instruction: "Gate A starts from the source formula, not the prototype"), which
reads the same way as the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_lh_run`, `run_length(h < h.shift(1))`): `n_t = n_{t-1} + 1 if high_t < high_{t-1} else 0`.

**Status:** shipped. Gates A-F measured below (Gate E by the launcher, Gate F whole suites by
the launcher per the issue-solver's own rules).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/trend/rd_lh_run.py` | trend | `RD_LH_RUN_100` | non-negative integer count, capped at 100; measured 0..8 (9 distinct values) on a 1,200-bar synthetic frame below; 0 at any bar that is not a lower high, including bar 0 |

Tests: `tests/test_rd_lh_run.py` (17 tests). Numbers: `python docs/measure_rd_lh_run.py`, run
from the repo root. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

## Decisions

1. **Built on `ml_bars_since`, the same way `range_compress_run` (volatility, issue #176's
   sibling port) is** — flip the condition (`~lower_high` instead of `lower_high`), and
   "bars since the flag last fired, counting the firing bar itself as 0" is exactly the
   issue's own recursion: `n_t = 0` on any bar that is NOT a lower high (the firing bar), and
   `n_t = n_{t-1} + 1` on every lower-high bar after it. This is this fork's established shape
   for a "run length of a condition" port, not a new pattern.
2. **Bar 0 reads 0, not NaN** — unlike `range_compress_run`, which explicitly overrides bar 0
   to NaN because its own condition compares two SUBTRACTED ranges (`prior` is NaN at bar 0).
   This port's condition, `high < high.shift(1)`, is a direct comparison of two raw values;
   pandas already evaluates `high_0 < NaN` as `False` (not NaN), so `~lower_high` already
   fires at bar 0 with no override needed. This matches the prototype's own observed bar-0
   value of 0 (`test_hand_computed`, `test_matches_an_independent_loop`).
3. **`cap` is a parameter, default 100** — not in the issue's own (unbounded) formula, but
   the same ML-feature-contract convention `range_compress_run`'s own `cap` uses (an
   unbounded counter on a rare, ever-growing condition dominates every split it appears in).
4. **No tie tolerance** — `range_compress_run`'s tie-tolerance argument (a decimal tick tie
   coming out unequal after a SUBTRACTION) does not apply here: this port compares `high` to
   `high.shift(1)` directly, with no subtraction in between, so a tie in the raw prices reads
   as a tie in the comparison with no rounding noise. Measured 0 exact ties among 1,199
   consecutive pairs on the synthetic walk (`docs/measure_rd_lh_run.py`), so the scale-free
   claim below needed no tolerance band.
5. **Category: trend.** The nearest named comparator in the issue's own Gate E measurement is
   `HIGHER_HIGH`, a price-structure/swing column; this fork's other run-length-of-a-condition
   port in the SAME shape as a swing count is `short_run`/`long_run` (trend), and `HIGHER_HIGH`
   itself is computed alongside `LOWER_LOW` in `pandas_ta.trend.bos`. `range_compress_run`
   (volatility) is the sibling in build SHAPE, not in subject matter.
6. **Column name `RD_LH_RUN_{cap}`** — e.g. `RD_LH_RUN_100` at the default, `RD_LH_RUN_10` at
   `cap=10` (same convention as `RCR_{cap}`).

## Gate A — the formula, read bar-by-bar

The issue's own formula (not the prototype — the issue's explicit instruction), read
literally in the module's docstring:

```
lower_high = high < high.shift(1)
RD_LH_RUN = bars since the last bar that was NOT a lower high
            (n_t = n_{t-1} + 1 if lower_high_t else 0), clipped to cap
RD_LH_RUN[0] = 0 (no prior bar, so the else branch applies)
```

A hand-computed sequence, chosen on paper before the module ran
(`tests/test_rd_lh_run.py::test_hand_computed`): `high = [10.0, 9.0, 8.0, 8.0, 11.0, 10.0,
10.0]`. Bar 0: no prior, else branch, `0`. Bar 1: `9 < 10` → `1`. Bar 2: `8 < 9` → `2`. Bar 3:
`8 == 8`, not strictly less, → `0`. Bar 4: `11 > 8` → `0`. Bar 5: `10 < 11` → `1`. Bar 6:
`10 == 10` → `0`. Expected `[0.0, 1.0, 2.0, 0.0, 0.0, 1.0, 0.0]`. The module's measured output
(`python docs/measure_rd_lh_run.py`): **exact match.**

Cross-checked against an independent plain-Python loop built straight from the formula above
(not read from the module, not using any pandas `.rolling`/`.groupby` call) on an 800-bar
synthetic OHLC walk (seed 7): **exact match on all 800 bars**
(`test_matches_an_independent_loop`, `python docs/measure_rd_lh_run.py`) — this is an exact
integer comparison, not a float tolerance, because both the module and the independent loop
compute the same strict `<` on the same raw `high` values with no intervening arithmetic.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,200-bar
  synthetic `high` walks (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in
  both the base and the spliced series, so if the module reads no later bar than `T` its
  output on `[0, J)` cannot move. Measured over **31 swept J values** (`J` = 40, 75, ...,
  1075; `python docs/measure_rd_lh_run.py`): **real module leaked at 0 of 31.**
- **The mutant** (`high.shift(1)` replaced with `high.shift(-1)`, comparing each bar to the
  NEXT bar's high instead of the prior one) **is live** (differs from the real module on the
  unperturbed frame) **and leaked at 31 of the same 31 swept J values.** A single random-walk
  replacement of the future alone caught this mutant at only 16 of 31 (a boolean flag is
  already True or False about half the time before the rewrite, so a random replacement flips
  it only about half the time); pairing a future pinned far ABOVE (forces the one affected
  comparison, at bar `J-1`, to read True) with one pinned far BELOW (forces it False) covers
  both cases and catches it at every swept `J`
  (`tests/test_rd_lh_run.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from the port session:

- **1,200-bar frame (seed 4):** 596 of 1,200 bars nonzero (a lower-high run in progress);
  **9 distinct values**, max run **8** bars.
- **10 independent 600-bar frames (seeds 100-109):** every frame has 286-315 of 600 bars
  nonzero, 8-12 distinct values, max run 7-11 bars — consistent with the single-frame figures
  above, not an outlier.
- **`0 < fires < n`, not constant:** every seed above has both zero and nonzero bars and more
  than one distinct value; none is constant.
- Real-data reachability is the launcher's Gate E run (owed).

## Gate D — scale-free

- **Bit-identical under any positive price rescale, with no tolerance band needed.**
  `lower_high = high < high.shift(1)` compares two raw price values directly — it is NOT a
  comparison of a computed difference against zero (the case `range_compress_run`'s own
  tie-tolerance argument addresses). For an exactly-representable `k` (a power of two), the
  rescale introduces no rounding at all (a power-of-two multiply only shifts the float's
  exponent), so the comparison is bit-identical to the unscaled one at every bar, and the
  downstream `cumsum`/`cumcount` (pure integer bookkeeping over a bit-identical boolean
  series) reproduces an identical run-length sequence. A non-power-of-two rescale (x10, x3.7)
  rounds `high*k` and `high.shift(1)*k` independently, which could in principle flip a bar
  that was an EXACT tie in the unscaled series into a strict inequality (or vice versa) — but
  that only matters if such a tie exists.
- **Measured on the 1,200-bar seed-4 frame** (`python docs/measure_rd_lh_run.py`): **0 exact
  consecutive ties among 1,199 pairs** in the unscaled `high`, and **0 mismatches** of 1,200
  bars at every one of x8.0, x64.0, x10.0, x3.7 — all four are bit-identical, not merely within
  a tolerance, because there were no ties to flip:

  | k | mismatches |
  |---|---|
  | 8.0 | 0 of 1200 |
  | 64.0 | 0 of 1200 |
  | 10.0 | 0 of 1200 |
  | 3.7 | 0 of 1200 |

  `tests/test_rd_lh_run.py::test_scale_is_bit_identical` asserts exact (`==`) equality at all
  four `k`, not a tolerance.
- `0 < fires < n`, not constant: 596 of 1,200 bars nonzero on the 1,200-bar frame above, 9
  distinct values, max 8, min 0 (never negative, by construction of `ml_bars_since`'s
  `cumcount`).

## Gate E — attribution

Launcher's run on the shipped module, `pandas_ta.trend.rd_lh_run`
(`is182-rd_lh_run-2043b0b4`, `gate_e_overlap.py run`, 89 ALTPORT-1 frames, pooled n = 398,849,
687 comparators = 329 `compute_all` + 358 `ml_features` manifest, canary bit-equal on AKBNK.IS,
BIENY.IS, AGHOL.IS, SASA.IS, measured 2026-11-27):

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_LH_RUN_100` | 0.8800 | `HIGHER_HIGH` (compute_all) | 398,849 | 0.8972 | DISCLOSE_GAP |

Both the pooled figure (0.8800) and the top-5 per-frame max median (0.8972) sit in `[0.80,
0.90)`, the `r3-perframe-0.90` DISCLOSE_GAP band in `CLAUDE.md` — below the 0.90 STRUCK line
on both tests, so the column ships with this disclosure rather than being reverted. Next
comparators on the launcher's run: `HA_Body_Ratio` 0.6693, `HA_Body_Ratio_Pctl` 0.6669.
Matches the prototype's own prior measurement on the same formula (0.8800 / 0.8972 vs the
same comparator), made on a different harness before this port existed. Ledger row recorded:
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-27`.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_lh_run.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,739 passed, 7 skipped, 0 failed**, measured 2026-11-27, after the receipt session recorded
the ledger row (`docs/gate_e_ledger.py record is182-rd_lh_run-2043b0b4 --measured 2026-11-27`):
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` now passes.
`tests/test_rd_lh_run.py` alone: 17 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub runner
without AVX-512 — the four features issue-solver's rules name, not this machine's full
dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_rd_lh_run_cpu.py` — **17 passed** (just `tests/test_rd_lh_run.py`; the
ledger/readme/wiring modules above are not CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 416 → 417 (`tests/test_altport2_ports.py`); `CATEGORY_BUCKETS["trend"]`
  70 → 71 (trend is one of the three tracked buckets in that file).
- README: 416 → 417 registered, 424 → 425 callable, trend (70) → (71).
- `docs/MLCompanionContract.md`: 761 → 762 tagged and 59 → 60 `ORD` (newest first in the
  chain). `RD_LH_RUN_100` tags `ORD` because it is a capped, non-negative integer count, not a
  continuous ratio — the same tag `range_compress_run`'s own `RCR_100` carries.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package (`python
  docs/gen_indicator_dictionary.py`): adds `rd_lh_run` under `## trend (71)`, tagged `ORD`.
- `Category`: `rd_lh_run` is placed alphabetically between `rd_adx8_med20` and
  `rejection_blocks` in `trend`.

## Next step

None — Gates A-E measured, ledger row recorded, this session's own test subset green. Whole
suites are the launcher's (see the PR body).
