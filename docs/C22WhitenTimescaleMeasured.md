# `c22_whiten_timescale` — measured

PandasTa issue **#139** (C22-WHITEN-TIMESCALE), ported 2026-11-27 on branch
`issue-139-c22-whiten-timescale`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_whiten_timescale.py` |
| column | `C22WHITENTIMESCALE_100` (`SF`, a dimensionless ratio of two continuous, linearly interpolated lag counts) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `FC_LocalSimple_mean1_taurat` — the hctsa operation `FC_LocalSimple(y, 'mean1')`'s `taurat` statistic: the ratio of the residual series' own ACF timescale (`CO_FirstZero`) to the raw series'; reference code pycatch22 1.0.2, **GPL-3.0** — ported from the definition |
| tests | `tests/test_c22_whiten_timescale.py` (38 tests) |
| harness | `docs/measure_c22_whiten_timescale.py` (sections A, B, C, D, G, **P**, plus diagnostics Y and Z; P is opt-in and is the only part of this repository that imports the GPL-3.0 reference), `docs/measure_c22_whiten_timescale_cpu.py` |
| Gate A | 0 of 366 sampled windows (six frames) disagree with the exact-fsum oracle beyond float noise (worst 3.9e-16); against the actual GPL-3.0 reference, `pycatch22.catch22_all`'s `FC_LocalSimple_mean1_taurat`, **0 of 8,400** windows (all six frames, every window) disagree beyond 1e-9 (worst 1.6e-12) — §A, §P |
| Gate B | causal; 0 of 43 offsets leak on six frames; four look-ahead mutants (write-back-dated, window-one/ten-ahead, returns-rolled) all live and caught 43/43 of 43 offsets each; the floor-removal mutant is inert on all six synthetic frames (none reaches it) — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames; up to 1,400 distinct (continuous) values; not constant on five of six (the cosine frame is near-constant by construction); the tick-rounded penny frame (21.68% exactly-zero returns) still fires on every eligible bar — §C |
| Gate D | ×8/×64/×2⁻⁴⁰/×2⁴⁰ bit-identical (24/24 cells, including on `penny`); worst |diff| 6.2e-13 under ×10/×3.7/×0.1/×1.0000001 inexact return rescale on the `walk` frame; `0 < fires < n`; not constant — §D |
| Gate E | max \|ρ\| **0.2521** vs `mad_pct` (manifest, n = 389,949), per-frame max median 0.2504 vs `Swing_Range_pct` → **SHIP** — §E |
| Gate F | PandasTa green (38 module tests, both dispatches; required subset below); whole suites run by issue-solver in clean worktrees — §F |

Every number below was produced by `python docs/measure_c22_whiten_timescale.py`
(default dispatch) or `python docs/measure_c22_whiten_timescale_cpu.py` (the CI
CPU-dispatch row: `AVX512F AVX512_SKX AVX2 FMA3` disabled), or by
`python -m pytest tests/test_c22_whiten_timescale.py` for the module's own 38
tests, on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11, pycatch22
1.0.2 installed in this worktree).

---

## 0. What the column is

```
r[t]   = close[t] / close[t-1] - 1
X      = r[T-99 .. T]                       (the 100 returns ending at T)
D      = X[1:] - X[:-1]                     (the residual: the plain first
                                              difference, hctsa's trivial
                                              "forecast = the previous
                                              point" predictor, train
                                              length 1)
k(y)   = min{k >= 1 : acf_y(k) <= 0}, else len(y)       (hctsa CO_FirstZero,
tau(y) = (k - 1) + acf_y(k-1) / (acf_y(k-1) - acf_y(k))  LINEARLY INTERPOLATED,
                   if k < len(y), else len(y)            else the sentinel)
C22WHITENTIMESCALE = tau(D) / tau(X)
```

A value near 1 means differencing the window does not change how long its
autocorrelation takes to turn negative; well below 1 means differencing
shortens that timescale a lot; above 1 means differencing lengthens it.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository
tests it on BIST: the feature's presence here is existence, not evidence.
The issue says so and this receipt repeats it.

The reference implementation is GPL-3.0 and this fork is MIT. The port was
written from the DEFINITION — "the trailing mean forecast with a training
window of 1 point is simply the previous point" and "the first zero crossing
of the autocorrelation function" are both public-domain mathematics, not
reference code — and from catch22's standard preprocessing. No shipped
module imports it: `test_no_shipped_module_imports_pycatch22` sweeps every
`.py` file under `pandas_ta/` for an import mentioning `pycatch22` and finds
none. ⚠ pycatch22 **is installed in this worktree**, so that guard is not
vacuous.

The one place the reference is run at all is
`docs/measure_c22_whiten_timescale.py` section **P** (opt-in; a bare run
skips it and does not import it) — MEASUREMENT only, the same use the
owner's own screen prototype makes of it.

### 1.1 The interpolation step was fit against the reference as a black box

An earlier, simpler build of `_first_zero_lag` scanned only the bare
INTEGER crossing lag `k` and read EXACTLY 1.0 on every one of the first 15
sampled `walk`-frame windows (both the raw window and its residual crossed
at the very first integer lag, so the integer ratio was always 1/1), while
`pycatch22.catch22_all(...)["FC_LocalSimple_mean1_taurat"]` read a tight
band around 0.70–0.73 on the SAME windows — a fractional value no integer
scan can produce (`docs/measure_c22_whiten_timescale.py` section Z). Adding
the linear interpolation between the ACF values bracketing the crossing
(`tau = (k - 1) + acf(k-1) / (acf(k-1) - acf(k))`) closed the gap: **0 of
8,400 windows (every window of six synthetic frames) disagree with the
reference beyond 1e-9**, worst absolute difference 1.6e-12 — a result as
clean as this fork's cleanest prior catch22 black-box fit
(`c22_forecast_error`, 1.1e-15) once the right definition was found; the
residual gap here before the fix was not float noise but a whole missing
step, confirmed rather than merely fit-tuned.

## A. Gate A — correctness

### A1. Against the exact fsum oracle

Every 23rd window of six 1,500-bar synthetic frames (an iid walk, a
tick-rounded walk, a 2-lira stock on a 1-kurus tick, an AR(1)-in-returns
path, a 20-bar cosine, a Student-t(3) path), 61 windows each, 366 total. The
oracle recomputes the whole definition in plain Python with `math.fsum`
(mean, autocovariance at every lag, the interpolated crossing) and no numpy
vectorisation:

| frame | windows | worst |diff| |
|---|---|---|
| walk | 61 | 2.2e-16 (default) / 1.1e-16 (CPU-disabled) |
| tick-rounded | 61 | 3.3e-16 / 3.9e-16 |
| penny | 61 | 2.8e-16 / 1.7e-16 |
| ar1 | 61 | 8.3e-17 / 8.3e-17 |
| cosine | 61 | 2.2e-16 / 2.2e-16 |
| student-t | 61 | 3.3e-16 / 2.2e-16 |

Every gap is at machine-precision noise, under both CPU dispatch settings.

### A2. Against the GPL-3.0 reference, every window of six frames — see §P and §1.1

**0 of 8,400 windows disagree beyond 1e-9**, worst absolute difference
1.6e-12. This section exists separately from §P because §P is opt-in and
this repository's CI does not run it; §A1 is the ungated correctness
evidence, §P is the (measured, not assumed) confirmation.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a ×1.0003
jump (section B) or a ×1000 jump (the pytest module's own sweep, needed to
move this column's continuous-but-quantised-near-integer values visibly —
a ×1.0003 jump produced 0 / 43 leaking offsets on every mutant too, which is
why the pytest module and this harness both use the larger jump), and no
bar before J may move. 43 offsets per frame:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 43** each |

### B2. Four mutants, read off this module's source, edited and exec'd in memory

| mutant | edit | walk |
|---|---|---|
| `write-back-dated` | the chunk's write slice moved one bar earlier | 43 / 43 |
| `window-one-ahead` | the sliding window reads one bar past the cut | 43 / 43 |
| `window-ten-ahead` | the sliding window reads ten bars past the cut | 43 / 43 |
| `returns-rolled` | the whole return stream rolled back one bar | 43 / 43 |
| `no-floor` (diagnostic, not a look-ahead mutant) | the no-variation floor removed | 0 / 43 (inert — no synthetic frame reaches it) |

All four look-ahead mutants are caught at every offset tried. The pytest
module runs the same mutants on a 16-offset sweep (`OFFSETS = range(130,
600, 30)`) and gets the matching result: 0 real leaks on the real module,
every mutant caught 16 of 16.

### B3. A bad tick

A ×1000 close at bar 300 changes the returns at bars 299 and 300, which only
the windows ending at bars 300..400 can hold. Measured: the moved bars are a
(non-empty) subset of that range, and every bar outside it is bit-identical
to the unperturbed column (`tests/test_c22_whiten_timescale.py::
test_a_bad_tick_moves_only_the_windows_that_hold_it`).

## C. Gate C — reachability

1,500-bar synthetic frames, 100-bar warm-up:

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 1,400 | 0.0838 .. 0.7794 | 0.6264 |
| tick-rounded | 1,400 | 1,400 | 0.0821 .. 0.7994 | 0.6941 |
| penny | 1,400 | 1,400 | 0.0855 .. 0.7427 | 0.3962 |
| ar1 | 1,400 | 1,400 | 0.0390 .. 0.4003 | 0.1515 |
| cosine (period 20) | 1,400 | 160 (default) / 159 (CPU-disabled) | 0.9589 .. 1.0415 | 0.9996 |
| student-t | 1,400 | 1,400 | 0.1157 .. 0.9586 | 0.6713 |

Every bar with a full window fires on all six frames. The `cosine` frame's
distinct count moved by one between CPU-dispatch settings (160 vs 159) — a
float-boundary count this fork's own rules say not to pin exactly; the
structural fact (fires on every eligible bar, not constant) holds under
both.

### C1. The issue's own worry: tick-rounded BIST-shaped data

`penny` (a 2-lira stock on a 1-kurus tick): **21.68%** of its one-bar returns
are exactly 0.00%. The column still fires on all 1,400 eligible bars and
reads 1,400 distinct values — tick rounding does not collapse this column's
reachability the way the issue worried a shape feature might.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64) | 12 of 12 **bit-identical** |
| six frames × (×2⁻⁴⁰, ×2⁴⁰) | 12 of 12 **bit-identical** (24 total, incl. `penny`) |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`; the autocorrelation (and so its
interpolated zero crossing) already cancels a positive affine rescale in
real arithmetic, and a power-of-two rescale is exact in floating point too.

### D2. Inexact rescale

| frame | factor | moved | worst |diff| |
|---|---|---|---|
| walk | ×10.0 | 910 / 1400 (default) / 849 / 1400 (CPU-disabled) | 2.1e-15 / 8.2e-15 |
| walk | ×3.7 | 1,156 / 1,078 | 6.7e-15 / 7.2e-15 |
| walk | ×0.1 | 1,396 / 1,386 | 3.7e-13 / 6.2e-13 |
| walk | ×1.0000001 | 1,310 / 1,242 | 3.2e-14 / 3.3e-14 |

Not bit-identical by construction (unlike this fork's discrete-lag catch22
siblings): the output is a CONTINUOUS interpolated ratio, so an inexact
rescale moves most individual bars by float noise even though the value is
unchanged in exact real arithmetic (each series' own ACF already
normalises by its own variance). The "moved" count is therefore large by
construction; the number that matters is the magnitude, and the worst
measured gap (6.2e-13) is nowhere near the 1e-6 tolerance
`tests/test_c22_whiten_timescale.py` pins.

### D3. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on the `ar1` frame (§D of the harness, which measures
this cell); the `walk` frame's own bound is confirmed separately by
`tests/test_c22_whiten_timescale.py::test_fires_and_is_not_constant`. Five
of six frames (all but `cosine`) read well over 20 distinct values with a
range wider than 0.01; `cosine` is near-constant by construction (§C).

## E. Gate E — attribution

Measured 2026-11-27 by the issue-solver launcher,
`gate_e_overlap.py run --module pandas_ta.statistics.c22_whiten_timescale`,
89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators,
canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`). Output:
`docs/gate_e_ledger.csv` row `c22_whiten_timescale`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | per-frame max median against | verdict |
|---|---|---|---|---|---|---|
| `C22WHITENTIMESCALE_100` | 0.2521 | `mad_pct` (manifest) | 389,949 | 0.2504 | `Swing_Range_pct` | **SHIP** |

0.2521 is well under the 0.76 ship line and the per-frame max median is well
under the 0.90 struck line (`r3-perframe-0.90` bands) — the column ships.

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_c22_whiten_timescale.py` | **38 passed** |
| the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_whiten_timescale_cpu.py`) | **38 passed** |
| `python docs/measure_c22_whiten_timescale_cpu.py A B C D G` — re-measured under the disabled dispatch | every structural figure (fires, distinct-count bounds, mutant catch counts, bit-identical cells) identical to the default-dispatch run; float values agree to float noise, not digit-for-digit; `cosine`'s distinct-value count moved by 1 (160 -> 159), the one figure this fork's rules say not to pin exactly |
| `python docs/measure_c22_whiten_timescale_cpu.py P` — the GPL-3.0 black box re-measured under the disabled dispatch | identical to the default-dispatch run: 0 of 8,400 disagree beyond 1e-9, worst |diff| 1.6e-12 |
| `python -m pytest -q tests/test_c22_whiten_timescale.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` (receipt session, after the ledger row was recorded) | **1,792 passed, 7 skipped** |

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring, all five touch points measured live

The module exists; it is exported from `pandas_ta.statistics`;
`"c22_whiten_timescale"` is in `Category["statistics"]`;
`df.ta.c22_whiten_timescale()` returns `C22WHITENTIMESCALE_100` bit-equal to
the function and forwards `length` and `offset`; `tests/
test_c22_whiten_timescale.py` exists. README's three counts moved
420 → 421, 428 → 429 and statistics 85 → 86; `CATEGORY_TOTAL` in
`tests/test_altport2_ports.py` moved 420 → 421; `docs/IndicatorDictionary.md`
was regenerated by its own generator (tagged `SF`, warm-up 100);
`docs/MLCompanionContract.md`'s tagged-column counts moved 765 → 766 /
390 → 391 `SF`.

## G. The floor, and what it buys

`NOISE_ULPS = 64` on BOTH the raw window's and the residual's own standard
deviation — the same constant this fork's `c22_acf_first_min`/
`firstzero_ac` use on the raw window, applied here to two series instead of
one.

| input | fires | notes |
|---|---|---|
| geometric ladder, step +1% | 0 | flat raw returns, below the floor |
| geometric ladder, step +0.1% | 0 | " |
| geometric ladder, step -0.5% | 0 | " |
| price flat except ONE 1-ulp step (400 bars) | 0 | " |
| one 1-kurus tick per bar at 100 (a 1e-4 return, 300 bars) | 200 | real variation, fires on every eligible bar |
| 400 identical closes | 0 | flat raw returns |
| linear return ramp (differences to a constant) | **0** | the RAW returns vary, but the RESIDUAL (the ramp's first difference) is a constant step, below the floor on the residual side — the second, distinct way to trip this module's shared floor rule |

The ramp row is the module's own closed-form test
(`tests/test_c22_whiten_timescale.py::
test_a_deterministic_ramp_differences_to_a_constant_and_blanks`): a linear
return ramp differences to EXACTLY a constant, so this column reads NaN
everywhere on it — the opposite of `c22_acf_first_min`'s behaviour on the
same input (that feature never differences the series, and reads a single
non-NaN constant, 71, on it).

## H. Bad data and edge cases

| input | behaviour |
|---|---|
| `close` holding NaN / ±inf / 0 / −1 / 1e−310 | bad return propagates to NaN on that window the same way as this fork's other return-based catch22 ports |
| `n` = 100 | `None` — `length` = 100 returns need 101 closes |
| `n` = 101 | at most 1 bar fires |
| `length` = None / 0 / 1 / 2 / 3 (below `MIN_LENGTH` = 4) | falls back to 100, column named `C22WHITENTIMESCALE_100` |
| `length` = `MIN_LENGTH` (4) | column named `C22WHITENTIMESCALE_4` |
| alternating returns (`+a, -a, ...`) | ratio very close to 1.0 but NOT exactly 1.0 — the residual series is one point shorter than the raw window (99 vs 100, an odd/even parity mismatch), so demeaning each series leaves a slightly different mean even on a perfectly alternating input (measured: 1.000051 on a 150-bar test frame) |
| linear return ramp | blanks entirely (§G) |
| offset = 2 | shifts the series by 2, bit-identical to the unshifted column elsewhere |
| `fillna` = -99 | 0 NaN remain; exactly the warm-up bars read -99 |
| chunk boundary (`CHUNK_CELLS` forced to 700) | moves a handful of bars by FFT batch-size float noise, worst measured 5.6e-17 (§Y) — a tolerance, not exact equality, unlike this module's discrete-lag siblings |

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_whiten_timescale.py P`. Not run by a bare
invocation, and the module is not imported unless the section runs.

### P1. Every window of six frames, default dispatch

| frame | windows | disagree (>1e-6) | disagree (>1e-9) | worst |diff| |
|---|---|---|---|---|
| walk | 1,400 | 0 | 0 | 5.88e-13 |
| tick-rounded | 1,400 | 0 | 0 | 1.63e-12 |
| penny | 1,400 | 0 | 0 | 5.53e-13 |
| ar1 | 1,400 | 0 | 0 | 1.52e-13 |
| cosine | 1,400 | 0 | 0 | 7.99e-15 |
| student-t | 1,400 | 0 | 0 | 1.25e-13 |
| **TOTAL** | **8,400** | **0** | **0** | **1.63e-12** |

Identical under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`: 0
of 8,400 disagree beyond 1e-9, worst |diff| 1.63e-12.

### P2. The diagnostic that found the missing interpolation step (§1.1)

`docs/measure_c22_whiten_timescale.py Z` prints the first 15 `walk`-frame
windows' value against the reference. The bare-integer build read exactly
`1.0` on all 15 (`mine`); the reference read a tight band 0.6996–0.7260
(`theirs`) — the gap that motivated re-deriving `_first_zero_lag` with
linear interpolation, kept in the harness as a permanent regression probe
for anyone who simplifies the kernel back to integer lags.
