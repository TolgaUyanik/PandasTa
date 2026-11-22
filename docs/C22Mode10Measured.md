# `c22_mode_10` — measured

PandasTa issue **#136** (C22-MODE-10), ported 2026-11-22 on branch
`issue-136-c22-mode-10`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_mode_10.py` |
| column | `C22MODE10_100` (`SF`, a z-score value) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `DN_HistogramMode_10` — the hctsa operation `DN_HistogramMode(y, 10)`; reference code pycatch22 1.0.2, **GPL-3.0** — ported from the definition |
| tests | `tests/test_c22_mode_10.py` (111 tests) |
| harness | `docs/measure_c22_mode_10.py` (sections A, B, C, D, G, SHIFT, **P**; P is opt-in and is the only part of this repository that imports the GPL-3.0 reference), `docs/measure_c22_mode_10_cpu.py` |
| Gate A | 0 of 1,200 sampled windows (six frames) disagree with the exact-rational bin-assignment oracle beyond float noise (worst 1.9e-15); the designed 4-way tie (bins 0, 2, 5, 8) matches the oracle to 1.7e-16 (test bound 1e-9); against the actual GPL-3.0 reference, `pycatch22.catch22_all`'s `DN_HistogramMode_10`, 39 of 8,400 windows — ALL on the degenerate `penny` frame — disagree beyond 1e-5 (worst 0.53), root-caused to a float64-vs-float32 boundary flip, not a convention mismatch — §A, §P, §P2 |
| Gate B | causal; 0 of 43 offsets leak on six frames; four mutants (write-back-dated, three cross-row chunk-wide reads) all live and caught 43/43, 43/43, 43/43 and 34/43 of 43 offsets — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames; not constant on five of six (the cosine frame is near-constant at ≈0 by construction, a clean periodic signal's own symmetric histogram); the tick-rounded penny frame (21.68% exactly-zero returns) still fires on every eligible bar — §C |
| Gate D | ×8/×64/×2⁻⁴⁰/×2⁴⁰ bit-identical (24/24 cells, including on `penny`); worst |diff| 1.8e-13 under ×10/×3.7/×0.1/×1.0000001 inexact return rescale on the `walk` frame; `0 < fires < n`; not constant — §D |
| Gate E | pending, run by issue-solver after this session — §E |
| Gate F | PandasTa green (111 module tests, both dispatches; required subset below); whole suites run by issue-solver in clean worktrees — §F |

Every number below was produced by `python docs/measure_c22_mode_10.py`, by
`docs/measure_c22_mode_10_cpu.py` for the CI CPU-dispatch row, or by
`python -m pytest tests/test_c22_mode_10.py` for §B3, §B4, the ×2⁻⁴⁰/×2⁴⁰
cells of §D1 and §H, on this machine (numpy 1.26.4, pandas 2.3.3, Python
3.11).

---

## 0. What the column is

```
r[t]     = close[t] / close[t-1] - 1
X        = r[T-99 .. T]                       (the 100 returns ending at T)
Z        = (X - mean(X)) / sd(X, ddof=1)
edges    = linspace(min(Z), max(Z), 11)        (10 equal-width bins)
counts   = histogram of Z over edges (last bin closed on both ends)
M        = {i : counts[i] = max(counts)}
C22MODE10 = mean over i in M of (edges[i] + edges[i+1]) / 2
```

The same column family as this fork's `c22_mode_5` (issue #134), at twice
the bin resolution. **Unlike this fork's other catch22-on-returns ports**
(`c22_entropy_pairs`, `c22_dfa`, both order/quantile-based and so
affine-invariant), z-scoring is NOT inert here: the output is a bin-centre
position in z-units, and an affine map of the raw returns moves it by that
same affine map. What IS invariant to z-scoring is the bin ASSIGNMENT (an
order-and-ratio fact about the raw window), which is what lets §A's oracle
be mostly exact (Fraction arithmetic) rather than only a tolerance check.

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

The one place the reference is run at all is `docs/measure_c22_mode_10.py`
section **P** (opt-in; a bare run skips it and does not import it) —
MEASUREMENT only, the same use the owner's own screen prototype makes of
it. The result is in §P: **39 of 8,400 sampled windows disagree beyond
1e-5**, worst absolute difference 0.53 — see §P2 for why, and why this is
NOT a convention mismatch.

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
| walk | 200 | 1.0e-15 |
| tick-rounded | 200 | 9.4e-16 |
| penny | 200 | 8.9e-16 |
| ar1 | 200 | 6.8e-16 |
| cosine | 200 | 3.3e-16 |
| student-t | 200 | 1.9e-15 |

Every gap is at machine-precision noise (< 2e-15), not a real
disagreement — this oracle check uses the SAME float64 formula as the
shipped module, so it cannot see the boundary-sensitivity effect §A3/§P2
measures against an INDEPENDENT (GPL-3.0) implementation.

### A2. The designed 4-way tie

`[0.1, 0.2, 0.3, 1.2, 1.3, 2.2, 2.3, 2.4, 3.2, 4.2, 5.2, 5.3, 5.4, 6.2, 7.2,
8.2, 8.3, 8.4, 9.0, 9.9]`: `floor((v - min) / width)` over 10 equal bins
puts 3 elements each in bins **0, 2, 5 and 8**, with every other occupied
bin holding strictly fewer (1 or 2) — a four-way tie, not a two-way one or
an accidental uniform spread. Shipped: **-0.08058231677243333**; oracle:
**-0.08058231677243316** (diff 1.7e-16). `tests/test_c22_mode_10.py` also
pins that "average all tied bins" disagrees with "pick just the first tied
bin" and "pick just the last tied bin" on this same window by more than
1e-6 — the tie rule is not merely stated, it is exercised and shown to
matter.

### A3. Against the GPL-3.0 reference, every window of six frames — see §P, §P2

**39 of 8,400 windows disagree beyond 1e-5**, worst absolute difference
0.53 — all 39 on the `penny` frame, none on the other five. §P2 root-causes
this to a float64-vs-float32 boundary flip on the window's dominant
repeated return value, not to a convention error in the definition or tie
rule (both of which §A1/§A2 confirm independently, in float64, against a
rational oracle). This section exists separately from §P because §P is
opt-in and this repository's CI does not run it; §A1/§A2 are the ungated
correctness evidence, §P/§P2 are the (measured, not assumed) confirmation
— including of the one place it disagrees and why.

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
still far above the ≥10 threshold the test module pins. (Same counts as
`c22_mode_5` measures on the same `walk` frame at this mutant set — the
mutants' catch rate here does not depend on the bin count.)

The pytest module (`tests/test_c22_mode_10.py`) runs the same four mutants
(plus `window-one-ahead`, `window-ten-ahead` and `returns-rolled`, shared
with this fork's other return-window catch22 ports) on a 35-offset sweep
and gets the matching result: 0 real leaks, every mutant caught ≥ 10 of 35.

### B3. The bad-return mask mutant

Dead on a clean frame (0 difference from the real module) and caught on
a frame with one injected NaN close, at 12 of 12 offsets tried — the same
"dead on clean, caught on dirty" shape this fork's `c22_entropy_pairs` and
`c22_mode_5` document for the identical mutant.

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
the guard) — the identical mechanism `c22_mode_5` documents for this same
designed attack.

## C. Gate C — reachability

1,500-bar synthetic frames, 100-bar warm-up:

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 1,400 | -0.8817 .. 0.9749 | 0.0641 |
| tick-rounded | 1,400 | 1,400 | -0.9252 .. 0.6590 | -0.0088 |
| penny | 1,400 | 1,332 | -1.0025 .. 0.9568 | 0.1081 |
| ar1 | 1,400 | 1,400 | -0.9384 .. 1.0005 | -0.0915 |
| cosine (period 20) | 1,400 | 227 | ≈0 .. ≈0 | ≈0 |
| student-t | 1,400 | 1,400 | -0.7558 .. 0.6450 | 0.0760 |

Every bar with a full window fires on all six frames. The cosine frame is
near-constant at 227 distinct values of a value near 0 (not exactly 1, the
way `c22_acf_first_min`'s sentinel-bound column is) — a clean periodic
signal's own histogram is close to symmetric every window, so the mode
bin(s) sit near the centre; this is the feature behaving as expected on a
degenerate-by-construction input, not a dead column (five of six frames
are NOT near-constant; see §D3 for the explicit bound).

### C1. The issue's own worry: tick-rounded BIST-shaped data

`penny` (a 2-lira stock on a 1-kurus tick): **21.68%** of its one-bar
returns are exactly 0.00%. The column still fires on all 1,400 eligible
bars and reads 1,332 distinct values (fewer than `walk`'s 1,400, as
expected — repeated zero returns can tie several windows into the same
bin pattern — but nowhere near collapsing to a handful of values). This is
the SAME frame §A3/§P2 shows diverging from the GPL-3.0 reference on 39 of
its 1,400 windows: the column still fires correctly everywhere by this
module's own definition, it is the independent reference implementation
that lands a dominant repeated value in a different bin on those 39.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64) | 12 of 12 **bit-identical** |
| six frames × (×2⁻⁴⁰, ×2⁴⁰) | 12 of 12 **bit-identical** (24 total, incl. `penny`) |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`; z-scoring then cancels the
constant exactly in real arithmetic, and a power-of-two rescale is exact
in floating point too. This holds on `penny` as well — the
boundary-sensitivity effect in §A3/§P2 is triggered by an INEXACT
perturbation (a float additive shift, a non-power-of-two rescale, or an
independent re-implementation), never by this EXACT algebraic identity, so
Gate D's formal requirement is unaffected by it.

### D2. Inexact rescale

| frame | factor | worst |diff| |
|---|---|---|
| walk | ×10.0 | 1.8e-15 |
| walk | ×3.7 | 4.4e-15 |
| walk | ×0.1 | 1.3e-13 |
| walk | ×1.0000001 | 1.6e-14 |

Not bit-identical by construction (these factors are not exact in binary),
but the output is unchanged in EXACT real arithmetic (z-scoring cancels
any positive affine rescale of the returns), and the measured gap is
machine-precision noise, nowhere near the 1e-6 tolerance
`tests/test_c22_mode_10.py` pins. Measured only on `walk` (not `penny`),
the same frame choice `c22_mode_5`'s D2 uses.

### D3. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on the walk frame. Five of six frames (all but
`cosine`) have at least 20 distinct rounded values and a range wider than
0.1 z-units; `cosine` is the one near-constant frame, by construction
(§C).

## E. Gate E — attribution

**pending, run by issue-solver after this session.** This port cannot run
the private Backtesting engine or the 827 MB BIST cache from inside this
worktree; `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here for exactly that reason, and a later receipt session records the
measured row once the launcher's run lands.

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_c22_mode_10.py` | **111 passed** |
| the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_mode_10_cpu.py`) | **111 passed** |
| `python docs/measure_c22_mode_10_cpu.py A B C D G` — re-measured under the disabled dispatch | every structural figure (fires, distinct-count bounds, mutant catch counts, bit-identical cells, designed-tie bin set) identical to the default-dispatch run; float values agree to the same ~1e-15 noise floor, not digit-for-digit (expected: this column is several `sqrt`/reduction steps from the raw returns, unlike an integer-valued catch22 port) |
| `python docs/measure_c22_mode_10_cpu.py P` — the GPL-3.0 black box re-measured under the disabled dispatch | identical to the default-dispatch run: 39 of 8,400 disagree beyond 1e-5, worst |diff| 0.53, same root cause |
| `python -m pytest -q tests/test_c22_mode_10.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **1,425 passed, 7 skipped** |
| `python -m pytest -q tests/test_gate_e_ledger.py` | **1 failed** (`test_every_indicator_that_needs_a_row_has_one`) — expected and owed, per the rules above; no ledger row exists yet |

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring, all five touch points measured live

The module exists; it is exported from `pandas_ta.statistics`;
`"c22_mode_10"` is in `Category["statistics"]`; `df.ta.c22_mode_10()`
returns `C22MODE10_100` bit-equal to the function and forwards `length`
and `offset`; `tests/test_c22_mode_10.py` exists. README's three counts
moved 366 → 367, 374 → 375 and statistics 64 → 65; `CATEGORY_TOTAL` in
`tests/test_altport2_ports.py` moved 366 → 367; `docs/IndicatorDictionary.md`
was regenerated by its own generator (tagged `SF`, warm-up 100);
`docs/MLCompanionContract.md`'s tagged-column counts moved 711 → 712 /
346 → 347 `SF`.

## G. The floor, and what it buys

`NOISE_ULPS = 4096` on the return standard deviation (`ddof=1`) — the same
constant this fork's other catch22-on-returns ports use.

| input | fires | max window sd | < floor |
|---|---|---|---|
| geometric ladder, step +1% | 0 | 1.4e-16 | yes |
| geometric ladder, step +0.1% | 0 | 1.4e-16 | yes |
| geometric ladder, step -0.5% | 0 | 1.3e-16 | yes |
| price flat except ONE 1-ulp step (400 bars) | 0 | — | — |
| one 1-kurus tick per bar at 100 (a 1e-4 return, 300 bars) | 200 | — | — |
| 400 identical closes | 0 | — | — |

The one-ulp step and the flat frame are both below the floor on every
window that could hold them; the 1-kurus/100 frame is real variation (a
genuine, if tiny, non-zero return) and fires on every eligible window,
the same result `firstzero_ac`, `c22_ami2`, `c22_acf_first_min` and
`c22_mode_5` report on close variants of this same frame.

## H. Bad data and edge cases

| input | behaviour |
|---|---|
| `close` holding NaN / ±inf / 0 / −1 / 1e−310 | bad return propagates to NaN on that window the same way as this fork's other return-based catch22 ports |
| `n` = 99 or 100 | `None` — `length` = 100 returns need 101 closes |
| `n` = 101 | 1 bar fires |
| `n` = 102 | 2 bars fire |
| `length` = None / 0 / 1 / `MIN_LENGTH - 1` (9) | falls back to 100, column named `C22MODE10_100` |
| `length` = `MIN_LENGTH` (10) | fires on `1500 - 10 = 1490` bars, column named `C22MODE10_10` |
| `length` = 250 or 250.7 | fires on 1,250 bars, column named `C22MODE10_250` |
| chunk boundary (`CHUNK_VALUES` forced to 100, 400, 1024) | bit-identical to the default budget on all three |
| `offset` = 2 | shifts the series by 2, bit-identical to the unshifted column elsewhere |
| `fillna` = -99 | 0 NaN remain; exactly the 100 warm-up bars read -99 |

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_mode_10.py P`. Not run by a bare invocation, and
the module is not imported unless the section runs.

### P1. Shipped against `pycatch22.catch22_all(...)["DN_HistogramMode_10"]`, every window of six frames

| frame | windows | disagree (>1e-9) | disagree (>1e-5) | worst |diff| |
|---|---|---|---|---|
| walk | 1,400 | 1,400 | 0 | 6.71e-07 |
| tick-rounded | 1,400 | 1,400 | 0 | 6.52e-07 |
| penny | 1,400 | 1,400 | **39** | **0.53** |
| ar1 | 1,400 | 1,400 | 0 | 6.54e-07 |
| cosine | 1,400 | 1,400 | 0 | 1.41e-07 |
| student-t | 1,400 | 1,400 | 0 | 1.06e-06 |
| **TOTAL** | **8,400** | **8,400** | **39** | **0.53** |

Five of six frames read the SAME ~1e-6/1e-7 gap `c22_mode_5`'s P1 measures
and attributes (not read from source, GPL-3.0) to the reference's internal
arithmetic plausibly being `float` (32-bit) rather than `double` (64-bit).
The sixth, `penny`, disagrees far more on 39 of its 1,400 windows — §P2.

### P2. Root-causing the 39 large-gap windows (all on `penny`)

Every one of the 39 windows holds a dominant repeated return value (14 to
19 of the window's 100 returns, measured over ALL 39, typically the
tick-rounded 0.00% return).
Re-deriving this module's OWN formula in `float32` instead of `float64` on
three sampled windows:

| window | repeated value | repeat count | bin under float64 | bin under float32 (same formula) |
|---|---|---|---|---|
| idx 150 | 0.0 | 17 / 100 | 4 | **5** |
| idx 151 | 0.0 | 17 / 100 | 4 | **5** |
| idx 152 | 0.0 | 17 / 100 | 4 | **5** |

A single-ulp-scale difference in the window's own mean/sd/width (from
doing the SAME arithmetic in a lower-precision float), propagated through
`floor()`, flips which of the 10 bins the dominant repeated value lands in
— and since that one value holds most of the window's mass, flipping its
bin flips the whole mode (worst gap 0.53, consistent with moving an entire
bin-width's worth of z-score, not a rounding-sized nudge). This bites at
10 bins and not at `c22_mode_5`'s 5 (half as many, so each is roughly
twice as wide) because the SAME sub-ulp float difference needs to cross a
boundary that is twice as close. Confirmed independently in
`docs/measure_c22_mode_10.py` section SHIFT: adding a constant +5.0 to each
window (another inexact float perturbation, nothing to do with pycatch22)
flips the SAME kind of boundary on 40 of `penny`'s 1,400 windows and on 0
of the other five frames' 1,400 each — the identical mechanism, triggered
by a different inexact perturbation, confirming this is a property of
narrow equal-width histograms on heavy-duplicate data, not of the GPL-3.0
reference specifically. Re-run under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`: identical, 39 of
8,400 disagree beyond 1e-5, worst |diff| 0.53, same three sample windows.

Not a Gate A failure: Gate A (§A1/§A2) checks this module against an
independently re-derived RATIONAL oracle using the SAME float64 precision
the shipped module uses, and that oracle agrees to machine noise on all
1,200 sampled windows including `penny`'s. §P/§P2 instead measure this
module against a SEPARATE, lower-precision (plausibly float32)
implementation it was never written from — a measured fact about where
the two diverge, reported honestly rather than smoothed over, not evidence
that the shipped module's own arithmetic is wrong.
