# `c22_mode_5` — measured

PandasTa issue **#134** (C22-MODE-5), ported 2026-11-22 on branch
`issue-134-c22-mode-5`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_mode_5.py` |
| column | `C22MODE5_100` (`SF`, a z-score value) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `DN_HistogramMode_5` — the hctsa operation `DN_HistogramMode(y, 5)`; reference code pycatch22 1.0.2, **GPL-3.0** — ported from the definition |
| tests | `tests/test_c22_mode_5.py` (111 tests) |
| harness | `docs/measure_c22_mode_5.py` (sections A, B, C, D, G, **P**; P is opt-in and is the only part of this repository that imports the GPL-3.0 reference), `docs/measure_c22_mode_5_cpu.py` |
| Gate A | 0 of 1,200 sampled windows (six frames) disagree with the exact-rational bin-assignment oracle beyond float noise (worst 1.9e-15); the designed 4-way tie (bins 0, 1, 3, 4) matches the oracle to 1.0e-16 (test bound 1e-9); against the actual GPL-3.0 reference, `pycatch22.catch22_all`'s `DN_HistogramMode_5`, 0 of 8,400 windows disagree beyond 1e-5 (worst 2.13e-6, consistent with the reference's own float32 internals) — §A, §P |
| Gate B | causal; 0 of 43 offsets leak on six frames; four mutants (write-back-dated, three cross-row chunk-wide reads) all live and caught 43/43, 43/43, 43/43 and 34/43 of 43 offsets — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames; not constant on five of six (the cosine frame is near-constant at ≈0 by construction, a clean periodic signal's own symmetric histogram); the tick-rounded penny frame (21.7% exactly-zero returns) still fires on every eligible bar — §C |
| Gate D | ×8/×64/×2⁻⁴⁰/×2⁴⁰ bit-identical; worst |diff| 1.3e-13 under ×10/×3.7/×0.1/×1.0000001 inexact return rescale on the `walk` frame; `0 < fires < n`; not constant — §D |
| Gate E | max \|ρ\| 0.1271 vs `Dist_to_SMA_200_pct` (manifest, n = 381,138), per-frame max median 0.1508 → **SHIP** — §E |
| Gate F | PandasTa green (111 module tests, both dispatches; required subset below); whole suites run by issue-solver in clean worktrees — §F |

Every number below was produced by `python docs/measure_c22_mode_5.py`, by
`docs/measure_c22_mode_5_cpu.py` for the CI CPU-dispatch row, or by
`python -m pytest tests/test_c22_mode_5.py` for §B3, §B4, the ×2⁻⁴⁰/×2⁴⁰
cells of §D1 and §H, on this machine (numpy 1.26.4, pandas 2.3.3, Python
3.11).

---

## 0. What the column is

```
r[t]    = close[t] / close[t-1] - 1
X       = r[T-99 .. T]                       (the 100 returns ending at T)
Z       = (X - mean(X)) / sd(X, ddof=1)
edges   = linspace(min(Z), max(Z), 6)         (5 equal-width bins)
counts  = histogram of Z over edges (last bin closed on both ends)
M       = {i : counts[i] = max(counts)}
C22MODE5 = mean over i in M of (edges[i] + edges[i+1]) / 2
```

**Unlike this fork's other catch22-on-returns ports** (`c22_entropy_pairs`,
`c22_dfa`, both order/quantile-based and so affine-invariant), z-scoring is
NOT inert here: the output is a bin-centre position in z-units, and an
affine map of the raw returns moves it by that same affine map. What IS
invariant to z-scoring is the bin ASSIGNMENT (an order-and-ratio fact about
the raw window), which is what lets §A's oracle be mostly exact (Fraction
arithmetic) rather than only a tolerance check.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository
tests it on BIST: the feature's presence here is existence, not evidence.
The issue says so and this receipt repeats it.

The reference implementation is GPL-3.0 and this fork is MIT. The port was
written from the DEFINITION — hctsa's own `DN_HistogramMode(y, numBins)`:
the mode of an equal-width histogram with `numBins` bins over the series'
own `[min, max]`, with the tie rule "average every bin tied for the most
observations" — and from catch22's standard z-score preprocessing, never
from the reference's source. No shipped module imports it:
`test_the_reference_implementation_is_not_imported_by_shipped_code` sweeps
every `.py` file under `pandas_ta/` for an import mentioning `catch22` (with
`c22` stripped first, so this port's own filename cannot trip its own
check) and finds none. ⚠ pycatch22 **is installed in this worktree**, so
that guard is not vacuous.

The one place the reference is run at all is `docs/measure_c22_mode_5.py`
section **P** (opt-in; a bare run skips it and does not import it) —
MEASUREMENT only, the same use the owner's own screen prototype makes of
it. The result is in §P: **0 of 8,400 sampled windows disagree beyond
1e-5**, worst absolute difference 2.13e-6 — a gap the same order as
single-precision rounding, not a convention mismatch (see §P discussion).

## A. Gate A — correctness

### A1. Against the exact rational bin-assignment oracle

Every 7th window of six 1,500-bar synthetic frames (an iid walk, a
tick-rounded walk, a 2-lira stock on a 1-kurus tick, an AR(1)-in-returns
path, a 20-bar cosine, a Student-t(3) path), 200 windows each, 1,200
total. The oracle recomputes which bin every element falls into with ZERO
rounding (`Fraction`), takes the exact tied-bin set, and converts only the
final bin-centre average to z-units in floats:

| frame | windows | worst |diff| |
|---|---|---|
| walk | 200 | 8.9e-16 |
| tick-rounded | 200 | 7.8e-16 |
| penny | 200 | 1.1e-15 |
| ar1 | 200 | 7.8e-16 |
| cosine | 200 | 3.3e-16 |
| student-t | 200 | 1.9e-15 |

Every gap is at machine-precision noise (< 2e-15), not a real
disagreement.

### A2. The designed 4-way tie

`[0.2, 0.3, 1.2, 1.3, 2.5, 3.1, 3.9, 4.5, 5.0]`: `floor((v - min) / width)`
over 5 equal bins puts 2 elements in bin 0, 2 in bin 1, 1 in bin 2, 2 in
bin 3 and 2 in bin 4 — tied bins **(0, 1, 3, 4)**, a four-way tie, not a
two-way one. Shipped: **0.08661676591984258**; oracle:
**0.08661676591984248** (diff 1.0e-16). `tests/test_c22_mode_5.py` also
pins that "average all tied bins" disagrees with "pick just the first
tied bin" and "pick just the last tied bin" on this same window by more
than 1e-6 — the tie rule is not merely stated, it is exercised and shown
to matter.

### A3. Against the GPL-3.0 reference, every window of six frames — see §P

**0 of 8,400 windows disagree beyond 1e-5**; worst absolute difference
2.13e-6. This section exists separately from §P because §P is opt-in and
this repository's CI does not run it; §A1/§A2 are the ungated correctness
evidence, §P is the (measured, not assumed) confirmation that the
definition and the tie rule were read correctly.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a
×1.0003 jump, and no bar before J may move. 43 offsets per frame:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 43** each |

### B2. Four mutants, read off this module's source, edited and exec'd in memory

| mutant | edit | walk |
|---|---|---|
| `write-back-dated` | the chunk's write slice moved one bar earlier | 43 / 43 |
| `chunk-wide-mean` | per-row mean replaced by the whole chunk's | 43 / 43 |
| `chunk-wide-sd` | per-row sd replaced by the whole chunk's | 43 / 43 |
| `chunk-wide-minmax` | per-row `[min(Z), max(Z)]` replaced by the whole chunk's | 34 / 43 |

All four are look-ahead bugs, not merely wrong values: the default
`CHUNK_VALUES` budget holds this 1,500-bar frame in ONE chunk, so a
per-chunk (rather than per-row) mean, sd or range mixes every row's own
future bars into every other row's output. `chunk-wide-minmax` catches
fewer offsets (34/43) than the other three because a changed range only
moves the OUTPUT when it also changes which bin(s) tie for the mode —
a weaker condition than "the value changed at all" — but 34/43 (79%) is
still far above the ≥10 threshold the test module pins.

The pytest module (`tests/test_c22_mode_5.py`) runs the same four mutants
(plus `window-one-ahead`, `window-ten-ahead` and `returns-rolled`, shared
with this fork's other return-window catch22 ports) on a 35-offset sweep
and gets the matching result: 0 real leaks, every mutant caught ≥ 10 of 35.

### B3. The bad-return mask mutant

Dead on a clean frame (0 difference from the real module) and caught on
a frame with one injected NaN close, at 12 of 12 offsets tried — the same
"dead on clean, caught on dirty" shape this fork's `c22_entropy_pairs`
documents for the identical mutant.

### B4. The overflow guard is redundant with the width check, measured not assumed

`no-overflow-guard` (drops `~np.isfinite(sd)` from the blanking rule) is
inert on all six synthetic frames (bit-identical to the real module). A
designed adversarial window (one close pair of ratio 1e200, making one
return's SQUARE overflow `float64` inside `block.std`, so `sd` itself
comes back `inf`) blanks under the real module via that guard — **but
removing the guard does not revive it**: with `sd = inf`, every element's
`z = (v - mean) / sd` collapses to `0.0` (a finite numerator over an
infinite denominator, true even for the one extreme element, since `mean`
is itself dominated by that same return), so `z.min() == z.max() == 0.0`,
`width = 0.0`, and the module's SEPARATE `~(width > 0.0)` check catches
the window anyway (0 of 100 would-be-blanked bars are saved by removing
the guard). Unlike this fork's `c22_ami2`, whose equivalent guard IS
load-bearing on the analogous attack, this module's overflow guard is
provably redundant on this pathway — pinned so nobody "cleans it up"
believing it is load-bearing without re-checking.

## C. Gate C — reachability

1,500-bar synthetic frames, 100-bar warm-up:

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 1,400 | -1.0052 .. 1.0262 | -0.0329 |
| tick-rounded | 1,400 | 1,400 | -0.7577 .. 0.7473 | -0.0226 |
| penny | 1,400 | 1,327 | -1.2158 .. 1.2091 | -0.0090 |
| ar1 | 1,400 | 1,400 | -0.9267 .. 0.8694 | 0.0464 |
| cosine (period 20) | 1,400 | 223 | ≈0 .. ≈0 | ≈0 |
| student-t | 1,400 | 1,400 | -0.7105 .. 0.7936 | -0.0270 |

Every bar with a full window fires on all six frames. The cosine frame is
near-constant at 223 distinct values of a value near 0 (not exactly 1, the
way `c22_acf_first_min`'s sentinel-bound column is) — a clean periodic
signal's own histogram is close to symmetric every window, so the mode
bin(s) sit near the centre; this is the feature behaving as expected on a
degenerate-by-construction input, not a dead column (five of six frames
are NOT near-constant; see §D3 for the explicit bound).

### C1. The issue's own worry: tick-rounded BIST-shaped data

`penny` (a 2-lira stock on a 1-kurus tick): **21.68%** of its one-bar
returns are exactly 0.00%. The column still fires on all 1,400 eligible
bars and reads 1,327 distinct values (fewer than `walk`'s 1,400, as
expected — repeated zero returns can tie several windows into the same
bin pattern — but nowhere near collapsing to a handful of values).

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64) | 12 of 12 **bit-identical** |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`; z-scoring then cancels the
constant exactly in real arithmetic, and a power-of-two rescale is exact
in floating point too. `tests/test_c22_mode_5.py` also checks ×2⁻⁴⁰ and
×2⁴⁰ on all six frames (12 more cells; 24 in all, re-running ×8/×64 as
well), all bit-identical.

### D2. Inexact rescale

| frame | factor | worst |diff| |
|---|---|---|
| walk | ×10.0 | 2.2e-15 |
| walk | ×3.7 | 4.0e-15 |
| walk | ×0.1 | 1.3e-13 |
| walk | ×1.0000001 | 1.5e-14 |

Not bit-identical by construction (these factors are not exact in binary),
but the output is unchanged in EXACT real arithmetic (z-scoring cancels
any positive affine rescale of the returns), and the measured gap is
machine-precision noise, nowhere near the 1e-6 tolerance
`tests/test_c22_mode_5.py` pins.

### D3. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on the walk frame. Five of six frames (all but
`cosine`) have at least 20 distinct rounded values and a range wider than
0.1 z-units; `cosine` is the one near-constant frame, by construction
(§C).

## E. Gate E — attribution (run by issue-solver, recorded 2026-11-22)

Run `is134-c22_mode_5-be94141e`, 89 ALTPORT-1 frames, 398,849 pooled bars,
687 comparators (329 `compute_all` + 358 manifest), canary bit-equal
(AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `C22MODE5_100` | 0.1271 | `Dist_to_SMA_200_pct` (manifest) | 381,138 | 0.1508 | **SHIP** |

0.1271 < 0.76 (`r3-perframe-0.90` ship line). Recorded in
`docs/gate_e_ledger.csv` (`python docs/gate_e_ledger.py record
{runs}/20261121-234543-134/gatee/is134-c22_mode_5-be94141e
--measured 2026-11-22`).

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_c22_mode_5.py` | **111 passed** |
| the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_mode_5_cpu.py`) | **111 passed** |
| `python docs/measure_c22_mode_5_cpu.py A B C D G` — re-measured under the disabled dispatch | every structural figure (fires, distinct-count bounds, mutant catch counts, bit-identical cells) identical to the default-dispatch run; float values agree to the same ~1e-15 noise floor, not digit-for-digit (expected: this column is several `sqrt`/reduction steps from the raw returns, unlike an integer-valued catch22 port) |
| `python docs/measure_c22_mode_5_cpu.py P` — the GPL-3.0 black box re-measured under the disabled dispatch | identical to the default-dispatch run: 0 of 8,400 disagree beyond 1e-5, worst |diff| 2.13e-6 |
| `python -m pytest -q tests/test_c22_mode_5.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **255 passed, 7 skipped** |
| `python -m pytest -q tests/test_gate_e_ledger.py` | ran red before this receipt session (`no Gate E ledger row for ['c22_mode_5']`, expected/owed); row recorded §E |
| `python -m pytest -q tests/test_c22_mode_5.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` (receipt session, after §E) | **1425 passed, 7 skipped** |

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring, all five touch points measured live

The module exists; it is exported from `pandas_ta.statistics`;
`"c22_mode_5"` is in `Category["statistics"]`; `df.ta.c22_mode_5()`
returns `C22MODE5_100` bit-equal to the function and forwards `length`
and `offset`; `tests/test_c22_mode_5.py` exists. README's three counts
moved 365 → 366, 373 → 374 and statistics 63 → 64; `CATEGORY_TOTAL` in
`tests/test_altport2_ports.py` moved 365 → 366; `docs/IndicatorDictionary.md`
was regenerated by its own generator (tagged `SF`, warm-up 100);
`docs/MLCompanionContract.md`'s tagged-column counts moved 710 → 711 /
345 → 346 `SF`.

## G. The floor, and what it buys

`NOISE_ULPS = 4096` on the return standard deviation (`ddof=1`) — the same
constant this fork's other catch22-on-returns ports use.

| input | fires | max window sd | < floor |
|---|---|---|---|
| geometric ladder, step +1% | 0 | 1.4e-16 | yes |
| geometric ladder, step +0.1% | 0 | 1.5e-16 | yes |
| geometric ladder, step -0.5% | 0 | 1.2e-16 | yes |
| price flat except ONE 1-ulp step (400 bars) | 0 | — | — |
| one 1-kurus tick per bar at 100 (a 1e-4 return, 300 bars) | 200 | — | — |
| 400 identical closes | 0 | — | — |

The one-ulp step and the flat frame are both below the floor on every
window that could hold them; the 1-kurus/100 frame is real variation (a
genuine, if tiny, non-zero return) and fires on every eligible window,
the same result `firstzero_ac`, `c22_ami2` and `c22_acf_first_min` report
on close variants of this same frame.

## H. Bad data and edge cases

| input | behaviour |
|---|---|
| `close` holding NaN / ±inf / 0 / −1 / 1e−310 | bad return propagates to NaN on that window the same way as this fork's other return-based catch22 ports |
| `n` = 99 or 100 | `None` — `length` = 100 returns need 101 closes |
| `n` = 101 | 1 bar fires |
| `n` = 102 | 2 bars fire |
| `length` = None / 0 / 1 / `MIN_LENGTH - 1` (4) | falls back to 100, column named `C22MODE5_100` |
| `length` = `MIN_LENGTH` (5) | fires on `1500 - 5 = 1495` bars, column named `C22MODE5_5` |
| `length` = 250 or 250.7 | fires on 1,250 bars, column named `C22MODE5_250` |
| chunk boundary (`CHUNK_VALUES` forced to 100, 400, 1024) | bit-identical to the default budget on all three |
| `offset` = 2 | shifts the series by 2, bit-identical to the unshifted column elsewhere |
| `fillna` = -99 | 0 NaN remain; exactly the 100 warm-up bars read -99 |

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_mode_5.py P`. Not run by a bare invocation, and
the module is not imported unless the section runs.

### P1. Shipped against `pycatch22.catch22_all(...)["DN_HistogramMode_5"]`, every window of six frames

| frame | windows | disagree (>1e-9) | disagree (>1e-5) | worst |diff| |
|---|---|---|---|---|
| walk | 1,400 | 1,400 | 0 | 1.34e-06 |
| tick-rounded | 1,400 | 1,400 | 0 | 1.30e-06 |
| penny | 1,400 | 1,400 | 0 | 1.29e-06 |
| ar1 | 1,400 | 1,400 | 0 | 1.31e-06 |
| cosine | 1,400 | 1,400 | 0 | 2.81e-07 |
| student-t | 1,400 | 1,400 | 0 | 2.13e-06 |
| **TOTAL** | **8,400** | **8,400** | **0** | **2.13e-06** |

**Every window disagrees at the 1e-6 level and none disagrees beyond
1e-5.** Every window reading a small, consistent gap rather than zero
rules out a convention difference (a wrong ddof or a wrong tie rule would
produce gaps of a very different, usually much larger, size, and would
not be this UNIFORM across six structurally different frames); the
measured size (order 1e-6, close to single-precision epsilon 1.19e-7
times a small constant) is consistent with the GPL-3.0 reference's own C
implementation doing its internal arithmetic in `float` (32-bit) rather
than `double` (64-bit) — this receipt does not read that reference's
source to confirm it (it is GPL-3.0; only the measured gap is reported),
and states this as the most consistent explanation of the measured
pattern, not as a read fact. Re-run under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`: identical, 0 of
8,400 disagree beyond 1e-5, worst |diff| 2.13e-06.
