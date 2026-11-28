# `c22_trev` — measured

PandasTa issue **#263** (C22-TREV), ported 2026-11-28 on branch
`issue-263-c22-trev`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_trev.py` |
| column | `C22TREV_100` (`SF`, dimensionless — a mean cubed z-score difference) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `CO_trev_1_num` (time-reversal asymmetry of returns at lag 1); reference code pycatch22, **GPL-3.0** — ported from the paper's definition, never from that code |
| tests | `tests/test_c22_trev.py` (98 tests) |
| harness | `docs/measure_c22_trev.py` (sections A, B, C, D, G, **P**; P is opt-in and is the only part of this repository that imports the GPL-3.0 reference), `docs/measure_c22_trev_cpu.py` |
| Gate A | 1,200 sampled windows (six frames) agree with an independent scalar-loop (`math.fsum`/`math.sqrt`) oracle to float noise (worst 6.0e-15); a hand-computed designed window (`[1, 2, 3, 5, 4]`) matches both the shipped function and the oracle to 1e-16; reversing that window negates the output exactly, the defining property of a time-reversal statistic; against the actual GPL-3.0 reference (`pycatch22.catch22_all`'s `CO_trev_1_num`), 0 of 8,400 windows disagree beyond 1e-9 (worst 1.1e-14) — §A, §A2, §P |
| Gate B | causal; 0 of 43 offsets leak on six frames (and 0 of 35 at `length` 3, 120, 250 — `tests/test_c22_trev.py`); six mutants (write-back-dated, two window-shift, returns-rolled, two chunk-wide-mean/sd) all live and caught 43/43 (10 of 10 in the pytest 35-offset sweep for each); the overflow guard is LOAD-BEARING here (unlike `c22_mode_5`'s redundant one): removing it revives exactly the 100 bars the real guard blanks, reading ≈0.0 — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames; not constant on five of six (the cosine frame is near-constant at ≈0 by construction); the tick-rounded penny frame (21.68% exactly-zero returns) still fires on every eligible bar — §C |
| Gate D | ×8/×64/×2⁻⁴⁰/×2⁴⁰ bit-identical; worst |diff| 2.3e-13 under ×10/×3.7/×0.1/×1.0000001 inexact return rescale on the `walk` frame; `0 < fires < n`; not constant — §D |
| Gate E | max \|ρ\| 0.1534 vs `SMA_50_200_Spread_pct_Pctl` (manifest, n = 375,887); per-frame max median \|ρ\| 0.1612 (same comparator, 89 frames); verdict **SHIP** — §E |
| Gate F | PandasTa green (98 module tests, both dispatches; required subset below); whole suites run by issue-solver in clean worktrees — §F |

Every number below was produced by `python docs/measure_c22_trev.py`, by
`docs/measure_c22_trev_cpu.py` for the CI CPU-dispatch row, or by
`python -m pytest tests/test_c22_trev.py` for the module's own pinned
tests, on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11).

---

## 0. What the column is

```
r[t]    = close[t] / close[t-1] - 1
X       = r[T-99 .. T]                       (the 100 returns ending at T)
Z       = (X - mean(X)) / sd(X, ddof=1)
C22TREV = mean_{i=1..99}((Z[i+1] - Z[i])**3)
```

Positive when rises in the window are sharper (bigger jumps up than down);
negative when falls are sharper; zero for a time-symmetric process.
Reversing the order of a window's returns negates every lag-1 difference
and so negates the output exactly — the defining property of a
time-reversal asymmetry statistic, and a property checked directly in
`tests/test_c22_trev.py::test_a_time_reversed_designed_window_flips_the_sign`.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository
tests it on BIST: the feature's presence here is existence, not evidence.
The issue says so and this receipt repeats it.

The 2026-10-24 round-3 screen (`docs/issues/screen/ind_screen_r3.py`,
candidate `c22_trev`) prototyped this feature with pycatch22 (GPL-3.0); this
module was written from the paper's own definition —
`TREV_t = mean_{i=1..99}((z_{i+1} - z_i)^3)` over a z-scored 100-return
window — never from that reference's source. No shipped module imports it:
`test_the_reference_implementation_is_not_imported_by_shipped_code` sweeps
every `.py` file under `pandas_ta/` for an import mentioning `catch22`
(with `c22` stripped first, so this port's own filename cannot trip its own
check) and finds none. ⚠ pycatch22 **is installed in this worktree**, so
that guard is not vacuous.

The one place the reference is run at all is `docs/measure_c22_trev.py`
section **P** (opt-in; a bare run skips it and does not import it) —
MEASUREMENT only, the same use the owner's own screen prototype makes of
it. The result is in §P: **0 of 8,400 sampled windows disagree beyond
1e-9**, worst absolute difference 1.1e-14 — tight enough to rule out a
convention mismatch (a wrong `ddof`, a wrong lag, or a different cubing
convention would produce gaps many orders larger and not this uniform
across six structurally different frames).

## A. Gate A — correctness

### A1. Against an independent scalar-loop oracle

Every 7th window of six 1,500-bar synthetic frames (an iid walk, a
tick-rounded walk, a 2-lira stock on a 1-kurus tick, an AR(1)-in-returns
path, a 20-bar cosine, a Student-t(3) path), 200 windows each, 1,200
total. The oracle re-derives the value with scalar Python loops and
`math.fsum`/`math.sqrt` — no `numpy` vectorisation, a different code path
from the shipped chunked implementation:

| frame | windows | worst |diff| |
|---|---|---|
| walk | 200 | 1.8e-15 |
| tick-rounded | 200 | 1.0e-15 |
| penny | 200 | 1.0e-15 |
| ar1 | 200 | 3.9e-16 |
| cosine | 200 | 2.6e-18 |
| student-t | 200 | 6.0e-15 |

Every gap is at machine-precision noise, not a real disagreement.

### A2. The designed asymmetric window

`[1.0, 2.0, 3.0, 5.0, 4.0]` (a steady climb, a sharp 2-unit rise, then one
1-unit fall): shipped **0.5692099788303084**; scalar oracle
**0.5692099788303083** (diff 1.0e-16); a hand-derivation in the test's own
comments (`sd = sqrt(2.5)`, `z = [-2,-1,0,2,1]/sd`,
`diffs = [1,1,2,-1]/sd`, mean of cubes) matches both to the same tolerance.
Reversing the window's order gives **-0.5692099788303083** — the exact
negation, confirming the time-reversal property is not merely asserted but
exercised.

### A3. Against the GPL-3.0 reference, every window of six frames — see §P

**0 of 8,400 windows disagree beyond 1e-9**; worst absolute difference
1.1e-14. This section exists separately from §P because §P is opt-in and
this repository's CI does not run it; §A1/§A2 are the ungated correctness
evidence, §P is the (measured, not assumed) confirmation that the
definition was read correctly.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a
×1.0003 jump, and no bar before J may move. 43 offsets per frame:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 43** each |

`tests/test_c22_trev.py` additionally sweeps 35 offsets at `length` 3
(`MIN_LENGTH`), 120 and 250 on the `walk` frame: **0 / 35** each.

### B2. Six mutants, read off this module's source, edited and exec'd in memory

| mutant | edit | walk |
|---|---|---|
| `write-back-dated` | the chunk's write slice moved one bar earlier | 43 / 43 |
| `window-one-ahead` | the sliding window read one return ahead | caught (pytest: 35/35) |
| `window-ten-ahead` | the sliding window read ten returns ahead | caught (pytest: 35/35) |
| `returns-rolled` | the whole return series shifted one bar early | caught (pytest: 35/35) |
| `chunk-wide-mean` | per-row mean replaced by the whole chunk's | 43 / 43 |
| `chunk-wide-sd` | per-row sd replaced by the whole chunk's | 43 / 43 |

All six are look-ahead bugs, not merely wrong values: the default
`CHUNK_VALUES` budget holds this 1,500-bar frame in ONE chunk, so a
per-chunk (rather than per-row) mean or sd mixes every row's own future
bars into every other row's output. The pytest module
(`tests/test_c22_trev.py`) runs the same mutants on a 35-offset sweep and
gets the matching result: 0 real leaks, every mutant caught ≥ 10 of 35.

### B3. The bad-return mask mutant

Dead on a clean frame (0 difference from the real module) and caught on a
frame with one injected NaN close, at 12 of 12 offsets tried — the same
"dead on clean, caught on dirty" shape this fork's other catch22 ports on
returns document.

### B4. The overflow guard is LOAD-BEARING, measured not assumed

`no-overflow-guard` (drops `~np.isfinite(sd)` from the blanking rule) is
inert on all six synthetic frames (bit-identical to the real module). A
designed adversarial window (one close pair of ratio 1e200, making one
return's SQUARE overflow `float64` inside `block.std`, so `sd` itself comes
back `inf`) blanks under the real module via that guard. **Unlike
`c22_mode_5`, whose equivalent guard is provably redundant with a separate
width check, this column has no second guard**: with `sd = inf`, every
element's `z = (v - mean) / sd` collapses to `0.0` (a finite numerator over
an infinite denominator), so every consecutive diff is `0.0` and the mean
cube is exactly `0.0` — a VALUE, not a blank. Removing the guard revives
exactly the 100 bars the real module blanks, all reading ≈0.0 (worst
|value| < 1e-9). Pinned so nobody "cleans up" the overflow guard believing
it is redundant here the way it is for `c22_mode_5`.

## C. Gate C — reachability

1,500-bar synthetic frames, 100-bar warm-up:

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 1,400 | -1.3577 .. 1.8093 | 0.1213 |
| tick-rounded | 1,400 | 1,400 | -1.3410 .. 1.6763 | -0.1929 |
| penny | 1,400 | 1,400 | -1.3772 .. 1.4585 | 0.1368 |
| ar1 | 1,400 | 1,400 | -0.5126 .. 0.5363 | 0.0500 |
| cosine (period 20) | 1,400 | 1,394-1,395 | ≈0 .. ≈0 | ≈0 |
| student-t | 1,400 | 1,400 | -6.5175 .. 8.2269 | -0.0665 |

Every bar with a full window fires on all six frames. The cosine frame's
distinct-value count (1,394 default dispatch, 1,395 with AVX-512/AVX2/FMA3
disabled) moves by CPU dispatch, as expected for a near-constant float
reading rather than a pinned structural fact — it is near-constant at ≈0
by construction (a clean periodic signal's third central lag-1 difference
is close to zero every window), not a dead column (five of six frames are
NOT near-constant).

### C1. The issue's own worry: tick-rounded BIST-shaped data

`penny` (a 2-lira stock on a 1-kurus tick): **21.68%** of its one-bar
returns are exactly 0.00%. The column still fires on all 1,400 eligible
bars and reads 1,400 distinct values.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64) | 12 of 12 **bit-identical** |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`; z-scoring then cancels the
constant exactly in real arithmetic, and a power-of-two rescale is exact in
floating point too. `tests/test_c22_trev.py` also checks ×2⁻⁴⁰ and ×2⁴⁰ on
all six frames (12 more cells; 24 in all, re-running ×8/×64 as well), all
bit-identical.

### D2. Inexact rescale

| frame | factor | worst |diff| |
|---|---|---|
| walk | ×10.0 | 2.9e-15 |
| walk | ×3.7 | 7.5e-15 |
| walk | ×0.1 | 2.3e-13 |
| walk | ×1.0000001 | 3.1e-14 |

Not bit-identical by construction (these factors are not exact in binary),
but the output is unchanged in EXACT real arithmetic (z-scoring cancels any
positive affine rescale of the returns), and the measured gap is
machine-precision noise, nowhere near the 1e-6 tolerance
`tests/test_c22_trev.py` pins.

### D3. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on the walk frame (and on `ar1`). Five of six frames
(all but `cosine`) have at least 20 distinct rounded values and a range
wider than 0.01; `cosine` is the one near-constant frame, by construction
(§C).

## E. Gate E — attribution

Run `is263-c22_trev-ac0ba962` (issue-solver, 2026-11-28), 89 frozen
ALTPORT-1 BIST frames, 687 comparators (329 `compute_all` + 358
`ml_features` manifest):

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `C22TREV_100` | 0.1534 | `SMA_50_200_Spread_pct_Pctl` (manifest) | 375,887 | 0.1612 (same comparator, 89 frames, 0% ≥ 0.90) | **SHIP** |

0.1534 is well under the 0.76 ship line (CLAUDE.md Gate E bands,
`r3-perframe-0.90`), close to this issue's own round-3 screen reading of
0.1534 pooled / 0.1612 per-frame median. Recorded in
`docs/gate_e_ledger.csv` (row `c22_trev`, `--measured 2026-11-28`).

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_c22_trev.py` | **98 passed** |
| the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_trev_cpu.py`) | **98 passed** |
| `python docs/measure_c22_trev_cpu.py A B C D G P` — re-measured under the disabled dispatch | every structural figure (fires, mutant catch counts, bit-identical cells, GPL-3.0 agreement) identical to the default-dispatch run; float values agree to the same ~1e-14 noise floor, not digit-for-digit; the cosine frame's distinct-value count moves 1,394 → 1,395 (expected, not pinned) |
| `python -m pytest -q tests/test_c22_trev.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **1868 passed, 7 skipped** |
| `python -m pytest -q tests/test_c22_trev.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` (after Gate E ledger row `c22_trev` recorded 2026-11-28) | **1876 passed, 7 skipped** |

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring, all five touch points measured live

The module exists; it is exported from `pandas_ta.statistics`; `"c22_trev"`
is in `Category["statistics"]`; `df.ta.c22_trev()` returns `C22TREV_100`
bit-equal to the function and forwards `length` and `offset`;
`tests/test_c22_trev.py` exists. `docs/IndicatorDictionary.md` was
regenerated by its own generator (`python docs/gen_indicator_dictionary.py`)
and carries the `c22_trev` row (tagged `SF`, warm-up 100).

## G. The floor, and what it buys

`NOISE_ULPS = 4096` on the return standard deviation (`ddof=1`) — the same
constant this fork's other catch22-on-returns ports use.

| input | fires | max window sd | < floor |
|---|---|---|---|
| geometric ladder, step +1% | 0 | 1.5e-16 | yes |
| geometric ladder, step +0.1% | 0 | 1.5e-16 | yes |
| geometric ladder, step -0.5% | 0 | 1.2e-16 | yes |
| price flat except ONE 1-ulp step (400 bars) | 0 | — | — |
| one 1-kurus tick per bar at 100 (a 1e-4 return, 300 bars) | 200 | — | — |
| 400 identical closes | 0 | — | — |

The one-ulp step and the flat frame are both below the floor on every
window that could hold them; the 1-kurus/100 frame is real variation (a
genuine, if tiny, non-zero return) and fires on every eligible window.

## H. Bad data and edge cases

| input | behaviour |
|---|---|
| `close` holding NaN / ±inf / 0 / −1 / 1e−310 | bad return propagates to NaN on that window the same way as this fork's other return-based catch22 ports |
| `n` = 99 or 100 | `None` — `length` = 100 returns need 101 closes |
| `n` = 101 | 1 bar fires |
| `n` = 102 | 2 bars fire |
| `length` = None / 0 / 1 / 2 (`< MIN_LENGTH` = 3) | falls back to 100, column named `C22TREV_100` |
| `length` = `MIN_LENGTH` (3) | fires on `1500 - 3 = 1497` bars, column named `C22TREV_3` |
| `length` = 250 or 250.7 | fires on 1,250 bars, column named `C22TREV_250` |
| chunk boundary (`CHUNK_VALUES` forced to 100, 400, 1024) | bit-identical to the default budget on all three |
| `offset` = 2 | shifts the series by 2, bit-identical to the unshifted column elsewhere |
| `fillna` = -99 | 0 NaN remain; exactly the 100 warm-up bars read -99 |
| close pair of ratio 1e200 (`sd` overflows to `inf`) | real module blanks 100 bars via the overflow guard; removing the guard revives them reading ≈0.0 (§B4) |

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_trev.py P`. Not run by a bare invocation, and the
module is not imported unless the section runs.

### P1. Shipped against `pycatch22.catch22_all(...)["CO_trev_1_num"]`, every window of six frames

| frame | windows | disagree (>1e-9) | disagree (>1e-5) | worst |diff| |
|---|---|---|---|---|
| walk | 1,400 | 0 | 0 | 2.22e-15 |
| tick-rounded | 1,400 | 0 | 0 | 1.78e-15 |
| penny | 1,400 | 0 | 0 | 2.33e-15 |
| ar1 | 1,400 | 0 | 0 | 7.22e-16 |
| cosine | 1,400 | 0 | 0 | 4.77e-18 |
| student-t | 1,400 | 0 | 0 | 1.11e-14 |
| **TOTAL** | **8,400** | **0** | **0** | **1.11e-14** |

**0 of 8,400 windows disagree beyond 1e-9**, an order tighter than the
`c22_mode_5`/`c22_ami2` precedent's 1e-5 gap: this feature's shipped
computation (`mean of cubed consecutive z-score differences`) involves no
histogram binning and so has no float32-vs-float64 internal-arithmetic
boundary for the reference's C implementation to round differently on.
Re-run under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`:
identical, 0 of 8,400 disagree beyond 1e-9, worst |diff| 9.77e-15.
