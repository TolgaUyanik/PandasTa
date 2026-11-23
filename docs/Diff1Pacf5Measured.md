# Sum of squares of the first 5 return partial autocorrelations — measured (`diff1_pacf5`)

Issue #151 (KATS-DIFF1-PACF5-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_acfpacf_features` →
`diff1y_pacf5 = sum(pacf(diff(x))[1:6] ** 2)` (issue text). The same Kats function
computes `diff2y_acf1`, already ported (#153, `docs/Diff2Acf1Measured.md`), which cites
the shared control flow by line number: the length guard (L1090), `nlag = min(6, len(x)
- 2)` and `diff1x` (L1098–1100), `pacf(x, nlags=7)` (L1107, raises below 14 points), the
zero-variance guard on `diff1x`/`diff2x` (L1109–1116), and `pacf(diff1x, nlags=nlag)`
(L1118) — whose `[1:6] ** 2` sum *is* `diff1y_pacf5` for this feature, not merely run and
discarded as it is for `diff2y_acf1`. **The `diff1y_pacf5` assembly line itself is not
independently re-confirmed in this session** — no network access to the Kats source —
so that last step is taken from the issue text, not from a line citation.

The issue's own candidate registration names the scale-free form actually ported:
"Durbin-Levinson on the unadjusted ACF" — each ACF lag divided by the window's own `c0`
(the full sum of squared deviations), not by `n - lag`. Measured in
`docs/measure_diff1_pacf5.py` (`pacf_method_probe`): that is exactly statsmodels'
`pacf(..., method="ywm")`, not its historical default `method="ywadjusted"` (max
difference 1.39e-17 vs `ywm`, 3.45e-3 vs `ywadjusted`, on one 99-point window). Kats'
own call does not pin a method, so this is a documented divergence, not a bug: see
"Gate A".

**Status:**
- Gates A, B and D are cleared, and this repo's test subset
  (`tests/test_diff1_pacf5.py` plus the wiring/count suites named below) is green,
  which is the half of Gate F that runs here.
- **Gate E: SHIP** (max |ρ| 0.0487, well under the 0.76 ship line). Port ships.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/diff1_pacf5.py` | statistics | `DIFF1PACF5_100` | `[0, 5)` |

Tests: `tests/test_diff1_pacf5.py` (33 tests). Two are skipped where statsmodels is
absent (CI); the rest, including an independent from-scratch Durbin-Levinson recursion,
run everywhere.

Numbers: `python docs/measure_diff1_pacf5.py`, from the repo root; needs statsmodels for
the Gate A oracle. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. CPU-variant
check: `python docs/measure_diff1_pacf5_cpu.py` (33 passed with `AVX512F AVX512_SKX AVX2
FMA3` disabled, standing in for a GitHub runner without AVX-512). Measured 2026-11-23.

## Decisions

1. **Input: log close**, as the issue states and `diff2_acf1` (#153) does for the same
   Kats function. `diff(log close)` is the log return; this feature reads it directly
   (one differencing level), unlike `diff2y_acf1` which differences a second time.
2. **Window = `length` closes**, bar T reads closes T − length + 1 .. T, same convention
   as `diff2_acf1` and `kpss`. At the default that is 99 log returns; the first value is
   at bar 99.
3. **`length` has a floor of 14**, shared with `diff2_acf1`: the function's `pacf(x,
   nlags=7)` call (L1107) raises `ValueError` below 14 points, before `diff1y_pacf5` is
   computed at all. A smaller or missing value falls back to 100, the repo's convention.
4. **Durbin-Levinson on the unadjusted ACF**, per the issue's candidate registration —
   not Kats' own statsmodels default. Measured divergence (`docs/measure_diff1_pacf5.py`,
   `gate_a`, "same, method=ywadjusted"): max abs diff 0.010–0.012, median ~0.003, over
   1,401 bars of two 1,500-bar frames at length 100. Both forms agree with the module to
   rounding when the *same* method is used (see "Gate A").
5. **A rounding guard, one differencing level earlier than `diff2_acf1`'s.** `diff2_acf1`
   guards the variance of the return CHANGES; this column reads the returns directly, so
   it guards their own variance instead. The rule is identical in shape: a window is NaN
   when the std of its returns is at most **64 machine epsilons × (1 + its largest |log
   return|)**, about 1.4e-14 for ordinary returns.
   - Measured, shipped against unguarded (`docs/measure_diff1_pacf5.py`, `guard`). "Units"
     are the window's return std in multiples of eps × (1 + max |log return|):

     | series (300 bars) | shipped fires | unguarded fires, median (max) | largest units |
     |---|---|---|---|
     | `100 * (1 + 1e-2)^t` | 0 | 201, 0.242 (0.405) | 0.64 |
     | `100 * (1 + 1e-4)^t` | 0 | 201, 0.178 (0.253) | 0.59 |
     | `100 * (1 + 1e-7)^t` | 0 | 201, 0.160 (0.225) | 0.61 |
     | `100 * (1 + 1e-8)^t` | 0 | 201, 0.220 (0.302) | 0.63 |
     | `100 * (1 + 1e-10)^t` | 0 | 201, 0.001 (0.980) | 0.10 |
     | `exp(linspace(0, 30, 300))`, 10% a bar | 0 | 201, 0.474 (0.763) | 5.25 |
     | 10.0 with one-ulp jitter | 0 | 201, 0.597 (0.776) | 0.78 |

   - **Headroom of 64.** Rounding-only series reach at most 5.25 units, about 12× margin
     below the floor. The smallest real series measured, iid log returns of standard
     deviation 1e-12, sits at 4.2e3 units, about 66× above it (1e-9 returns: 3.8e6
     units). Ordinary frames (AR(1), iid normal, tick-rounded, a 150-flat-bar mix) and a
     10%-a-bar tick series are bit-identical between the guarded and unguarded module at
     lengths 14/100/252 — the guard changes nothing on any of them (measured: 0 bars
     blanked only by the guard, in every case).
   - All seven rounding-only cases and the two very-small-real-return cases are tests.
6. **Bad inputs**, same rule as `diff2_acf1`: a close that is NaN, infinite, zero,
   negative or subnormal (below 2.2e-308) is missing data, and its windows are NaN. A
   price ratio that overflows is treated as missing, not infinite.

## Gate A — correctness

**Two independent checks**, neither reading the module's own window-construction code:

1. **A from-scratch Durbin-Levinson recursion** (`tests/test_diff1_pacf5.py::_loop`,
   `_loop_pacf5`): no statsmodels, no module code, runs everywhere including CI. Matches
   the module to 1e-12 over a 400-bar AR(1) frame (`test_matches_an_independent_recursion`).
2. **statsmodels' `pacf(..., method="ywm")`**, on the window's own log returns, nlags=6,
   squares of indices 1–5 summed — the literal form the issue's "Durbin-Levinson on the
   unadjusted ACF" names. Matches the module within 1e-9 over every window of a 400-bar
   AR(1) frame, at length 14 and 100 (`test_matches_statsmodels_pacf_ywm`, skipped without
   statsmodels).

**The oracle** in `docs/measure_diff1_pacf5.py` (`kats_diff1y_pacf5`) additionally follows
Kats' own control flow — the length/constant guard, `nlag`, `diff1x`/`diff2x`, the
`pacf(x, nlags=7)` call that raises below 14 points, the zero-variance guard, and
`pacf(diff1x, nlags=nlag, method=method)[1:6] ** 2` summed — run on the log close of
every window of the **unguarded** module (so the rounding guard does not enter), at
`method="ywm"`:

| frame | zero returns | NaN masks equal | max abs difference (4 lengths: 14/63/100/252) |
|---|---|---|---|
| AR(1) φ = 0.2, 1500 bars | 0% | 4 / 4 | 3.7e-14 / 6.9e-15 / 5.6e-15 / 1.2e-15 |
| iid normal, 1500 bars | 0% | 4 / 4 | 3.3e-14 / 6.7e-15 / 3.6e-15 / 8.0e-16 |
| tick-rounded near 5 on a 0.01 tick, 1500 bars | 20% | 4 / 4 | 3.7e-14 / 1.4e-14 / 5.4e-15 / 1.9e-15 |
| iid with 150 flat bars, 800 bars | 19% | 4 / 4 | 4.7e-14 / 1.6e-14 / 1.6e-14 / 1.0e-15 |

- The NaN masks are equal in all 16 cases, and Kats' call raises in none of them.
- The differences are rounding (same order as `diff2_acf1`'s own Gate A, 1e-14 to 1e-15):
  this module takes the log of the price ratio where the oracle differences logs.
- At `method="ywadjusted"` (Kats' own unstated default) the same comparison reads 0.010
  to 0.012 max abs diff (Decision 4) — the expected, documented divergence, not a bug.

**`kats_diff1y_pacf5`'s own minimum** (`docs/measure_diff1_pacf5.py`, `kats_minimum`):
NaN at 9 points (constant-input / length guard), `ValueError` at 10–13 points
(`pacf(x, nlags=7)`), a value from 14 points on — identical to `diff2y_acf1`'s floor,
confirming Decision 3.

**A hand-derived closed form** (`test_closed_form`): for 14 alternating log returns `+a,
-a, ..., -a` (x_t = a·(−1)^t, mean exactly 0 since the counts of +1/−1 match), the
unadjusted ACF has the closed form ρ_k = (−1)^k · (14 − k) / 14. Durbin-Levinson on that
hand-computed ρ (not on the window's own arithmetic) matches the module to 1e-12 — an
independent check of the ACF formula itself, not a restatement of `_loop`.

## Gate B — causality

- **Future perturbation:** 16 offsets, every close from `j` on replaced by another path
  rescaled to join it. Bars before `j` are bit-identical
  (`test_real_module_never_reads_the_future`).
- **Mutant:** the chunk write offset `lo = length - 1 + start` is moved to `length - 2 +
  start`, one bar earlier. The mutant is live (differs from the real module on a 600-bar
  frame) and is caught at 16 of 16 offsets (`test_mutant_is_caught`).
- **A bad tick moves exactly its windows:** a close ×1000 at bar 300 changes log returns
  299 and 300 (window width 99), so the windows holding either end at bars 300..399;
  every other bar is bit-identical (`test_a_bad_tick_moves_exactly_its_windows`).

## Gate C — reachability

- **Synthetic** (`docs/measure_diff1_pacf5.py`, `reachability`; also
  `test_fires_and_is_not_constant`): 501 of 600 bars fire (first at bar 99), all 501
  values distinct, range [0.0031, 0.1375] on this frame — inside the column's full
  `[0, 5)` range.
- **Real data:** Gate E's run, 390,038 non-NaN / non-zero of 398,849 pooled bars
  (89 ALTPORT-1 frames) — see "Gate E" below.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks
  (`test_price_scale_is_bit_identical`).
- ×10 and ×3.7: within 1e-9 (`test_price_scale_within_tolerance`).
- `0 < fires < n`, and the column is not constant (`test_fires_and_is_not_constant`).

## Cost

Machine-dependent (x86_64). Timings are the range over 5 runs with tracemalloc off;
peak memory from a separate run with tracemalloc on
(`docs/measure_diff1_pacf5.py`, `cost`):

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.012–0.013 s | 10 MiB |
| 5,000 | 252 | 0.019–0.029 s | 15 MiB |
| 20,000 | 100 | 0.033–0.038 s | 22 MiB |
| 20,000 | 252 | 0.082–0.084 s | 44 MiB |
| 200,000 | 100 | 0.366–0.404 s | 162 MiB |
| 200,000 | 252 | 0.829–0.866 s | 393 MiB |

## Gate E — attribution

Run `is151-diff1_pacf5-6ce3d0fc` (`gate_e_overlap.py run --module pandas_ta.statistics.diff1_pacf5`,
Backtesting #107), 89 ALTPORT-1 BIST frames, 398,849 pooled bars, 390,038 non-NaN/non-zero,
687 comparators (329 `compute_all` + 358 manifest), canary bit-equal (AKBNK.IS, BIENY.IS,
AGHOL.IS, SASA.IS).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | per-frame max median against | verdict |
|---|---|---|---|---|---|---|
| `DIFF1PACF5_100` | 0.0487 | `CKSP_Width_pct` (manifest) | 390,038 | 0.0862 | `mcgd` | SHIP |

Pooled max |ρ| 0.0487 and per-frame max median 0.0862 are both well under the 0.76 ship
line (`r3-perframe-0.90` band). Ledger row recorded 2026-11-24 (`docs/gate_e_ledger.csv`).

## Gate F — suites

Not the whole suite (the launcher runs it). This session's subset, from the repo root:

```
python -m pytest -q tests/test_diff1_pacf5.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Previous run (pre-ledger-row): 1467 passed, 7 skipped, 1 failed —
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, for exactly the
reason this file then stated: `diff1_pacf5` had no ledger row yet. Expected, not a
finding.

Re-run after recording the ledger row (2026-11-24): 1475 passed, 7 skipped, 0 failed.

CPU-variant check (`python docs/measure_diff1_pacf5_cpu.py`, `NPY_DISABLE_CPU_FEATURES =
"AVX512F AVX512_SKX AVX2 FMA3"`): 33 passed.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 381 → 382 (`tests/test_altport2_ports.py`).
- README: 381 → 382 registered, 389 → 390 callable, statistics (70) → (71).
- `docs/MLCompanionContract.md`: 726 → 727 tagged, 360 → 361 `SF`.
- `docs/IndicatorDictionary.md`, regenerated (`python docs/gen_indicator_dictionary.py`).
  Its diff is the `diff1_pacf5` row (`DIFF1PACF5_100` SF, 99 warm-up), the three headline
  counts, the statistics section header, and the SF shortlist — nothing else.
- `Category`: `diff1_pacf5` is placed alphabetically, before `diff2_acf1`.
