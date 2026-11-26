# Volume-weighted imbalance oscillator (10) — measured (`rd_vwio_10`)

Issue #173 (RD-VWIO-10), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition
comes from a post or comment, and nothing in this port tests what the poster says it
does — existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:algotrading:1c261v8
(2024-04-12) https://www.reddit.com/r/algotrading/comments/1c261v8/ — "buys = volume *
(close > open)` `sells = volume * (close < open)` `VWIO = EMA(buys - sells, 10) /
EMA(volume, 10)". Claimed use: predominant buying vs selling pressure; sign used as entry
confirmation — **not independently tested here.** The issue gives the formula directly,
not a script, so there is no source line number to cite; Gate A below reads the formula
from the issue's own statement (its own instruction: "Gate A starts from the source
formula, not the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_vwio_10`, which is mathematically the same
reading but is not what Gate A cites).

**Status:** Gates A–F measured. Gate E SHIP (0.6542 vs `qstick_pct`). Shipped.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volume/rd_vwio_10.py` | volume | `RD_VWIO_10` | roughly `[-1, 1]` or NaN |

Tests: `tests/test_rd_vwio_10.py` (21 tests). Numbers: `python
docs/measure_rd_vwio_10.py`, run from the repo root. Environment: Python 3.11.2, pandas
2.3.3, numpy 1.26.4. Measured 2026-11-26.

## Decisions

1. **The formula is `EMA(buys - sells, 10) / EMA(volume, 10)`**, with `buys = volume IF
   close > open ELSE 0` and `sells = volume IF close < open ELSE 0` — the issue's own
   pseudocode, unchanged. Equivalently `buys - sells == volume * sign(close - open)`
   (0 on a tie, `close == open`).
2. **"EMA" is read as this fork's own `pandas_ta.overlap.ema`** (SMA-seeded warm-up of
   `length - 1` NaN bars, then the recursive EMA step) — the same reading `pzo`/`vzo`
   take for their own "EMA of a signed source over EMA of the source" shape
   (`pandas_ta/momentum/_zone.py`). A Reddit comment's pseudocode names a standard
   recursion, not a committed script, so there is no single "the" EMA to transcribe —
   this fork's own helper is the concrete choice, not a deviation from a spec that does
   not exist. This matters for Gate D: the screen prototype's own reading, a plain
   `Series.ewm(span=10, adjust=False).mean()` with no SMA seed, starts emitting from bar
   0 with no warm-up NaN at all, so every bar would be non-NaN and the `0 < fires < n`
   scale-free guard could not distinguish a constant column from a real one on a frame
   with no NaNs of its own.
   `tests/test_rd_vwio_10.py::test_matches_the_screen_prototypes_plain_ewm_reading_after_warmup`
   proves the two readings are the same number once both have settled past their own
   warm-up (not merely structurally related).
3. **Window = 10 bars, fixed by the issue's own title and prototype parameter**, not a
   Gate A judgment call. A `length` argument is still offered, following this fork's
   fixed-suffix-port convention (`osap_retskew_21`, `rd_wick_pressure_10`).
4. **Non-redundant with `vzo`** (this fork's other EMA-of-signed-volume ratio). `vzo`
   signs volume by `sign(close.diff())` — the direction close moved from the PRIOR bar's
   close (inter-bar). This port signs volume by `sign(close - open)` — the direction the
   SAME bar's own body ran (intrabar). The issue's own stage-2 fork-overlap screen
   (scale-free `Category` outputs at defaults, 12 frames) reads this column against
   `imi:IMI_14` at its overlap max (0.6546), not against `vzo`.

## Gate A — correctness

The issue's own formula:

```
buys       = volume IF close > open ELSE 0
sells      = volume IF close < open ELSE 0
RD_VWIO_10 = EMA(buys - sells, 10) / EMA(volume, 10)
```

`python docs/measure_rd_vwio_10.py`:

- **All-buy construction.** Every bar closes strictly above its own open: imbalance ==
  volume every bar, so `EMA(imbalance) == EMA(volume)` by construction and the ratio must
  read exactly +1. Measured: 51 non-NaN bars (length 10), max `|ratio − 1|` =
  **0.000e+00** (exact).
- **All-sell construction.** The mirror case (every bar closes strictly below its own
  open): max `|ratio + 1|` = **0.000e+00** (exact).
- **Independent per-bar loop.** A plain-Python reconstruction of `buys`/`sells`/
  `imbalance` and the SMA-seeded EMA recursion (never importing the module's own `ema`),
  on a 400-bar GBM close (seed 11) with a jittered open (seed 31) and an independent
  lognormal volume (seed 21), length 10: NaN masks match the module exactly, max
  `|diff|` = **0.000e+00** (exact).
- **Screen-prototype equivalence.** The prototype's plain `Series.ewm(adjust=False)`
  reading (no SMA seed) against this module's SMA-seeded reading, on a 500-bar frame,
  compared only on bars ≥ 100 (both readings' transients have decayed by
  `(9/11)**91 ≈ 1.2e-8` at that point, seed at bar 9 to bar 100 is 91 steps): 400 compared
  bars, max `|diff|` = **1.144e-09** —
  the two readings of "EMA" are the same number once both have settled.

## Gate B — causality

- **`buys`/`sells` at bar T read only `open[T]`, `close[T]`, `volume[T]`.** The EMA
  recursion (both the SMA seed and the subsequent step) reads only bars `<= T`. Nothing
  in the formula shifts an index forward. `python docs/measure_rd_vwio_10.py` /
  `tests/test_rd_vwio_10.py`: future-perturbation over **16 offsets** (60..1035, step 65),
  rewriting `open`, `close` and `volume` from the offset onward: **real module leaked at
  0 of 16**.
- **Mutant.** The module's final ratio, `.shift(-1)`'d before returning (reading one bar
  ahead), `importlib`-read and `exec`'d in memory (never a hand-written copy): proved live
  (differs from the real module on the unperturbed frame) and **caught at 16 of 16**
  swept offsets.

## Gate C — reachability

Synthetic, from this session (no real-data cache in this worktree):

- **1,200-bar frame (seed 11 close / seed 31 open / seed 21 volume), default length 10:**
  1,191 of 1,200 bars non-NaN (9-bar warm-up, `length - 1`); all 1,191 non-zero; **1,191
  distinct values** — not constant.
- **10 independent 600-bar frames (close seeds 100–109, open seeds 300–309, volume seeds
  200–209):** every one of the 10 frames reads 591 non-NaN bars (warm-up 9) with 591
  distinct values — the column fires on every frame tried, not just the one the
  reachability test happens to use.
- What blanks a bar: the 9-bar warm-up (`length - 1 = 9`); nothing else, since `open`,
  `close` and `volume` are finite by construction on every synthetic frame used.
- **Real data:** Gate E run `is173-rd_vwio_10-cbadc748`, 398,048 non-NaN / 387,237 non-zero
  of 398,849 pooled bars across the 89 ALTPORT-1 frames, no `degenerate.csv` row — fires on
  real data (the 801 blank bars are exactly 89 frames × the 9-bar warm-up).

## Gate D — scale-free

`python docs/measure_rd_vwio_10.py`, same 1,200-bar frame, 1,191 co-finite cells at every
factor:

| rescale | target | x8 | x64 | x10 | x3.7 |
|---|---|---|---|---|---|
| price | `open *= k`, `close *= k` (together) | bit-identical (0) | bit-identical (0) | bit-identical (0) | bit-identical (0) |
| volume | `volume *= k` | bit-identical (0) | bit-identical (0) | max\|diff\| 3.331e-16 | max\|diff\| 3.331e-16 |

**Price scale measured bit-identical at all four tested factors on this frame**,
including the non-power-of-two ones — stronger than this fork's other price/volume ratios
(`rd_wick_pressure_10`, `rd_corr_c_obv_20`), whose denominators are themselves built from
price and only match to float tolerance at a non-power-of-two factor. The reason:
`close > open` / `close < open` is a comparison, invariant to ANY positive rescale of both
operands together IN EXACT REAL-NUMBER ARITHMETIC (no price magnitude enters the formula
past the sign of the difference). This is NOT a floating-point guarantee for every
possible input: a non-power-of-two `k` rounds `open*k` and `close*k` independently, so an
`open`/`close` pair within a few ULPs of each other could in principle have its comparison
flipped — the claim above is what was measured on the tested frame and factors, not a
proof that no input can ever flip a comparison. Volume-scale non-power-of-two differences
(3.331e-16) are float epsilon, far under the tests' 1e-9 tolerance. NaN masks match
exactly at every factor, both inputs. `0 < 1,191 fires < 1,200` bars, 1,191 distinct
values (not a constant column) — the same frame as Gate C.

## Gate E — attribution

Run by issue-solver (launcher), recorded in `docs/gate_e_ledger.csv`. Run dir
`is173-rd_vwio_10-cbadc748`, 89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators
(329 `compute_all` + 358 manifest), canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_VWIO_10` | 0.6542274872500634 | `qstick_pct` (manifest) | 398,048 | 0.642992334952896 | **SHIP** |

0.6542 < 0.76 ship line (`CLAUDE.md`'s Gate E bands) — not DISCLOSE, not STRUCK. Matches
the prior-session screen prototype's number (0.6543 vs `qstick_pct`) to 4 decimal places,
consistent with Gate A's measurement that the two "EMA" readings agree after warm-up (max
|diff| 1.144e-09).

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_vwio_10.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,607 passed, 7 skipped, 0 failed** — this receipt session, after recording the Gate E
ledger row above. `tests/test_rd_vwio_10.py` alone: 21 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_vwio_10_cpu.py` — **21 passed** (just
`tests/test_rd_vwio_10.py`; the ledger/readme/wiring modules above are not CPU-sensitive
and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 399 → 400 (`tests/test_altport2_ports.py`); `CATEGORY_BUCKETS["volume"]`
  45 → 46.
- README: 399 → 400 registered, 407 → 408 callable, volume (45) → (46).
- `docs/MLCompanionContract.md`: 744 → 745 tagged and 374 → 375 `SF` (newest first in the
  chain). `RD_VWIO_10` tags `SF` because the sign gate is invariant to any positive price
  rescale and the EMA ratio is linear in volume — the dictionary generator's own probe
  frame confirms it (`docs/IndicatorDictionary.md`'s `rd_vwio_10` row), not merely
  asserted here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_vwio_10` row (`RD_VWIO_10` SF, 9-bar warm-up), the three header counts, the
  volume section count, the SF shortlist, and nothing else (checked: `git diff
  docs/IndicatorDictionary.md`).
- `Category`: `rd_vwio_10` is placed alphabetically between `rd_corr_c_obv_20` and
  `tod_profile` in `volume`.

## Open

None. Gates A–F measured, ledger row recorded, SHIP.
