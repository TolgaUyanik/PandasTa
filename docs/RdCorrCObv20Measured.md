# Rolling correlation of price and OBV (20) — measured (`rd_corr_c_obv_20`)

Issue #168 (RD-CORR-C-OBV-20), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition
comes from a post or comment, and nothing in this port tests what the poster says it
does — existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:chnbr1
(2019-07-25) https://www.reddit.com/r/algotrading/comments/chnbr1/ — "walking correlation
of z-scored price and OBV (z-scoring does not change a Pearson correlation)". Poster's
words: "Try to normalize indicators (e.g. z-score) and then just use walking
correlation." Claimed use: detect divergence between price and a volume indicator — **not
independently tested here.** The issue gives the formula directly, not a script, so there
is no source line number to cite; Gate A below reads the formula from the issue's own
statement (its own instruction: "Gate A starts from the source formula, not the
prototype"), not from the screen prototype (`docs/issues/screen/ind_screen_r6.py`'s
`rd_corr_c_obv_20`, which is mathematically the same reading but is not what Gate A
cites).

**Status:** shipped through Gates A–F. Gate E measured 2026-11-25 (SHIP), ledger row
recorded.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volume/rd_corr_c_obv_20.py` | volume | `RD_CORR_C_OBV_20` | `[-1, 1]` or NaN |

Tests: `tests/test_rd_corr_c_obv_20.py` (19 tests). Numbers: `python
docs/measure_rd_corr_c_obv_20.py`, run from the repo root. Environment: Python 3.11.2,
pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **The formula is `close.rolling(20).corr(OBV(close, volume))`.** `OBV` is this fork's
   existing `pandas_ta.volume.obv` (signed-volume cumulative sum), imported from its own
   module per this repo's import rule, not reimplemented.
2. **The z-score step is skipped, not added.** The issue's own parenthetical — "z-scoring
   does not change a Pearson correlation" — is correct for a GLOBAL (whole-series,
   constant mean/std) z-score, which is an affine transform (`a*x + b`, `a > 0`) a Pearson
   correlation is invariant to. `tests/test_rd_corr_c_obv_20.py::test_zscoring_either_input_first_does_not_move_the_result`
   proves this directly, built with a global mean/std (not a rolling, per-point one, which
   is a *different*, non-affine transform and would not read the poster's claim
   correctly).
3. **Window = 20 bars, fixed by the issue's own title and prototype parameter**, not a
   Gate A judgment call the way `pvcorr`'s window was (issue #18, no source window at
   all). A `length` argument is still offered, following this fork's fixed-suffix-port
   convention (`osap_retskew_21`, `lean_tdd_20`): a parameter with that default, not a
   hard constant.
4. **Non-redundant with `pvcorr`** (issue #18, "Related open issue" named in #168).
   `pvcorr` correlates the bar RETURN against the log CHANGE in volume (instantaneous,
   differenced). `rd_corr_c_obv_20` correlates the PRICE LEVEL against the OBV LEVEL,
   where OBV accumulates every prior signed-volume bar — a different pair of series
   through different transforms of volume (flow-change vs. all-time running sum).

## Gate A — correctness

The issue's own formula:

```
RD_CORR_C_OBV_20 = close.rolling(20).corr(OBV(close, volume))
```

`python docs/measure_rd_corr_c_obv_20.py`:

- **Monotone-close construction.** Strictly increasing close (`100 + i`) with constant
  volume forces `OBV` to be a linear function of bar index — two perfectly linear series
  correlate at exactly +1 by construction. Measured: 51 non-NaN bars (length 10), max
  `|corr − 1|` = **2.22e-16** (float epsilon). A `-1` construction is not reachable: OBV's
  increment always shares the SIGN of `close.diff()`, so a monotone close forces OBV
  monotone in the same direction, never the opposite — this is a structural fact about the
  formula, not a gap in the test.
- **Independent per-window loop.** A plain-Python signed cumulative sum (never calling
  `pandas_ta.volume.obv`) plus `np.corrcoef` per 20-bar window (never calling pandas'
  rolling `.corr`), on a 400-bar GBM close (seed 11) against an independent lognormal
  volume (seed 21): NaN masks match the module exactly, max `|diff|` = **5.47e-13**.
- **Z-score equivalence.** Global (whole-series) z-score of each input, then rolling corr
  of the z-scored pair, against this module's direct correlation on the same 300-bar
  frame: 281 compared bars, max `|diff|` = **4.30e-13** — the poster's own claim, measured,
  not merely re-asserted.

## Gate B — causality

- **`OBV` is itself purely backward-looking** (a cumulative sum of signed volume up to and
  including bar T), and the rolling correlation window `[T-19, T]` likewise never reaches
  forward. `python docs/measure_rd_corr_c_obv_20.py` / `tests/test_rd_corr_c_obv_20.py`:
  future-perturbation over **16 offsets** (60..1035, step 65), rewriting both `close` and
  `volume` from the offset onward: **real module leaked at 0 of 16**.
- **Mutant.** The module's one correlation call, with the OBV series read one bar ahead
  (`.shift(-1)`) before correlating, `importlib`-read and `exec`'d in memory (never a
  hand-written copy): proved live (differs from the real module on the unperturbed frame)
  and **caught at 16 of 16** swept offsets.

## Gate C — reachability

Synthetic, from this session (no real-data cache in this worktree; the receipt session
adds the Gate E run's real-data reachability count):

- **1,200-bar frame (seed 11 close / seed 21 volume), default length 20:** 1,181 of 1,200
  bars non-NaN (19-bar warm-up, `min_periods=length`); all 1,181 non-zero; **1,181
  distinct values** — not constant.
- **10 independent 600-bar frames (seeds 100–109, paired volume seeds 200–209):** every
  one of the 10 frames reads 581 non-NaN bars (warm-up 19) with 581 distinct values — the
  column fires on every frame tried, not just the one the reachability test happens to
  use.
- What blanks a bar: the 19-bar warm-up (`min_periods=20`); nothing else, since `close`
  and `volume` are finite by construction on every synthetic frame used.

## Gate D — scale-free

`python docs/measure_rd_corr_c_obv_20.py`, same 1,200-bar frame, 1,181 co-finite cells at
every factor:

| rescale | target | x8 | x64 | x10 | x3.7 |
|---|---|---|---|---|---|
| price | `close *= k` | bit-identical (0) | bit-identical (0) | max\|diff\| 2.43e-12 | max\|diff\| 3.07e-12 |
| volume | `volume *= k` | bit-identical (0) | bit-identical (0) | max\|diff\| 4.71e-13 | max\|diff\| 8.32e-13 |

All four non-power-of-two differences are far under the tests' 1e-9 tolerance. NaN masks
match exactly at every factor, both inputs. `0 < 1,181 fires < 1,200` bars, 1,181 distinct
values (not a constant column) — the same frame as Gate C.

The reason both scales hold *at all* (not just within tolerance, but bit-identically at
powers of two): `OBV` depends only on the SIGN of `close.diff()` (unaffected by a positive
price rescale) and scales exactly by `k` under a `k`-rescale of volume (an affine
transform with `b=0`), and a Pearson correlation is invariant to an affine rescale of
either of its inputs — see the module docstring for the full argument.

## Gate E — attribution

Run by issue-solver, `is168-rd_corr_c_obv_20-8d3eb2c8`, 89 ALTPORT-1 frames, 398,849
pooled bars, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS), 329 + 358 = 687
comparators, 0 degenerate columns.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_CORR_C_OBV_20` | 0.4010 | `Dist_to_BB_Lower_pct` (manifest) | 384,750 | 0.4094 | **SHIP** |

Non-NaN 384,750 / non-zero 384,361 of the pooled 398,849 bars. Pooled max |ρ| 0.3797 vs
`LINREG_SLOPE` against the `compute_all` set alone (329 comparators); the manifest set
(358 comparators) carries the overall max against `Dist_to_BB_Lower_pct`. Both well under
the `r3-perframe-0.90` SHIP line (< 0.76): pooled 0.40 and per-frame max median 0.41, not
0.90. Column ships as measured.

Prior-session context (prototype screen run, not Gate E itself): issue text quoted max |ρ|
0.4032 vs `Dist_to_BB_Lower_pct`, consistent with this module's own 0.4010.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_corr_c_obv_20.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,581 passed, 7 skipped** (receipt session, after the ledger row was recorded —
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` now passes).
`tests/test_rd_corr_c_obv_20.py` alone: 19 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_corr_c_obv_20_cpu.py` — **19 passed** (just
`tests/test_rd_corr_c_obv_20.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 396 → 397 (`tests/test_altport2_ports.py`); `CATEGORY_BUCKETS["volume"]`
  44 → 45.
- README: 396 → 397 registered, 404 → 405 callable, volume (44) → (45).
- `docs/MLCompanionContract.md`: 741 → 742 tagged and 371 → 372 `SF` (newest first in the
  chain). `RD_CORR_C_OBV_20` tags `SF` because a Pearson correlation is invariant to the
  affine rescale a price/volume rescale induces in `close`/`OBV` — the dictionary
  generator's own probe frame confirms it (`docs/IndicatorDictionary.md`'s
  `rd_corr_c_obv_20` row), not merely asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_corr_c_obv_20` row (`RD_CORR_C_OBV_20` SF, 19-bar warm-up), the three header
  counts, the volume section count, the SF shortlist, and nothing else (checked: `git diff
  docs/IndicatorDictionary.md`).
- `Category`: `rd_corr_c_obv_20` is placed alphabetically between `pvt` and `tod_profile`
  in `volume`.

## Open

None. Gates A–F measured, ledger row recorded, column ships. Closes #168.
