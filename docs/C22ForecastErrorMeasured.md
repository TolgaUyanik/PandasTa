# `c22_forecast_error` — measured

PandasTa issue **#137** (C22-FORECAST-ERROR), ported 2026-11-22 on branch
`issue-137-c22-forecast-error`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_forecast_error.py` |
| column | `C22FORECASTERROR_100` (`SF`, a dimensionless z-score-unit standard deviation) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `FC_LocalSimple_mean3_stde` — the hctsa operation `FC_LocalSimple(y, 'mean3')`, residual standard deviation; reference code pycatch22 1.0.2, **GPL-3.0** — ported from the definition |
| tests | `tests/test_c22_forecast_error.py` (105 tests) |
| harness | `docs/measure_c22_forecast_error.py` (sections A, B, C, D, G, **P**; P is opt-in and is the only part of this repository that imports the GPL-3.0 reference), `docs/measure_c22_forecast_error_cpu.py` |
| Gate A | 0 of 366 sampled windows (six frames) disagree with the exact-fsum oracle beyond float noise (worst 4.4e-16); against the actual GPL-3.0 reference, `pycatch22.catch22_all`'s `FC_LocalSimple_mean3_stde`, **0 of 8,400** windows (all six frames, every window) disagree beyond 1e-9 (worst 1.1e-15) — the cleanest black-box fit of this fork's catch22 ports to date — §A, §P |
| Gate B | causal; 0 of 43 offsets leak on six frames; six look-ahead mutants (write-back-dated, window-one/ten-ahead, returns-rolled, two cross-row chunk-wide reads) all live and caught 43/43 of 43 offsets each; the mask-back-dated mutant is dead on a clean frame and caught 12/12 on a dirty one; the overflow guard is inert on all six synthetic frames and LOAD-BEARING on a designed adversarial window (unlike `c22_mode_10`'s equivalent guard, this module has no separate check to fall back on) — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames; not constant on five of six (the cosine frame is near-constant by construction, a clean periodic signal's own 3-point forecast tracks it closely every window); the tick-rounded penny frame (21.68% exactly-zero returns) still fires on every eligible bar — §C |
| Gate D | ×8/×64/×2⁻⁴⁰/×2⁴⁰ bit-identical (24/24 cells, including on `penny`); worst |diff| 9.1e-15 under ×10/×3.7/×0.1/×1.0000001 inexact return rescale on the `walk` frame; `0 < fires < n`; not constant — §D |
| Gate E | SHIP — max \|ρ\| 0.1832 vs `mad_pct`, n = 389,949, per-frame max median 0.1959 — §E |
| Gate F | PandasTa green (105 module tests, both dispatches; required subset below); whole suites run by issue-solver in clean worktrees — §F |

Every number below was produced by `python docs/measure_c22_forecast_error.py`,
by `docs/measure_c22_forecast_error_cpu.py` for the CI CPU-dispatch row, or by
`python -m pytest tests/test_c22_forecast_error.py` for §B3, §B4, the ×2⁻⁴⁰/×2⁴⁰
cells of §D1 and §H, on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11,
pycatch22 1.0.2 installed in this worktree).

---

## 0. What the column is

```
r[t]   = close[t] / close[t-1] - 1
X      = r[T-99 .. T]                       (the 100 returns ending at T)
Z      = (X - mean(X)) / sd(X, ddof=1)
f[i]   = mean(Z[i-3], Z[i-2], Z[i-1]),       i = 3 .. 99
e[i]   = Z[i] - f[i]
C22FORECASTERROR = sd(e, ddof=1)
```

Z-score the last 100 daily returns. At every index from the 4th point on,
forecast it as the mean of the PREVIOUS 3 z-scored points, take the residual
(actual minus forecast), and report the standard deviation of the 97
residuals so produced. This is the irreducible noise of the naivest local
forecaster this fork's catch22 family has: a flat 3-point moving average,
applied to the OWN past of a z-scored return window.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository
tests it on BIST: the feature's presence here is existence, not evidence.
The issue says so and this receipt repeats it.

The reference implementation is GPL-3.0 and this fork is MIT. The port was
written from the DEFINITION — hctsa's own `FC_LocalSimple` family (a local
forecaster's residual statistics) and the name `mean3_stde` itself, which
states the forecast (a trailing 3-point mean) and the reported statistic
(the residual standard deviation) — and from catch22's standard z-score
preprocessing, never from the reference's source. No shipped module imports
it: `test_the_reference_implementation_is_not_imported_by_shipped_code`
sweeps every `.py` file under `pandas_ta/` for an import mentioning `catch22`
(with `c22` stripped first, so this port's own filename cannot trip its own
check) and finds none. ⚠ pycatch22 **is installed in this worktree**, so
that guard is not vacuous.

The one place the reference is run at all is
`docs/measure_c22_forecast_error.py` section **P** (opt-in; a bare run skips
it and does not import it) — MEASUREMENT only, the same use the owner's own
screen prototype makes of it. The result is in §P: **0 of 8,400 sampled
windows disagree beyond 1e-9**, worst absolute difference 1.1e-15 — the
cleanest agreement any catch22 port in this fork has measured against the
reference, with no residual gap left to root-cause.

## A. Gate A — correctness

### A1. Against the exact fsum oracle

Every 23rd window of six 1,500-bar synthetic frames (an iid walk, a
tick-rounded walk, a 2-lira stock on a 1-kurus tick, an AR(1)-in-returns
path, a 20-bar cosine, a Student-t(3) path), 61 windows each, 366 total. The
oracle recomputes the whole definition in plain Python with `math.fsum`
(mean, variance, the 3-point forecast, the residual, the residual's own
variance) and no numpy vectorisation:

| frame | windows | worst |diff| |
|---|---|---|
| walk | 61 | 4.4e-16 |
| tick-rounded | 61 | 2.2e-16 |
| penny | 61 | 4.4e-16 |
| ar1 | 61 | 2.2e-16 |
| cosine | 61 | 2.2e-16 |
| student-t | 61 | 4.4e-16 |

Every gap is at machine-precision noise. A non-default length (120) is
checked the same way, same result (`tests/test_c22_forecast_error.py`).

### A2. The ddof convention is not interchangeable

`ZSCORE_DDOF` and `RESID_DDOF` both pinned to 1 by the black-box fit (§P1).
On a stochastic window, swapping either knob to 0 moves the value by more
than 1e-4 (pinned, `tests/test_c22_forecast_error.py::
test_the_shipped_ddof_pair_is_not_interchangeable_with_the_others`) — so the
convention is a real choice that matters to the output, not a cosmetic one.

### A3. Against the GPL-3.0 reference, every window of six frames — see §P

**0 of 8,400 windows disagree beyond 1e-9**, worst absolute difference
1.1e-15 (machine noise). This section exists separately from §P because §P
is opt-in and this repository's CI does not run it; §A1/§A2 are the ungated
correctness evidence, §P is the (measured, not assumed) confirmation.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a
×1.0003 jump, and no bar before J may move. 43 offsets per frame:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 43** each |

### B2. Six mutants, read off this module's source, edited and exec'd in memory

| mutant | edit | walk |
|---|---|---|
| `write-back-dated` | the chunk's write slice moved one bar earlier | 43 / 43 |
| `window-one-ahead` | the sliding window reads one bar past the cut | 43 / 43 |
| `window-ten-ahead` | the sliding window reads ten bars past the cut | 43 / 43 |
| `returns-rolled` | the whole return stream rolled back one bar | 43 / 43 |
| `chunk-wide-mean` | per-row mean replaced by the whole chunk's | 43 / 43 |
| `chunk-wide-sd` | per-row sd replaced by the whole chunk's | 43 / 43 |

All six are look-ahead bugs, not merely wrong values: the default
`CHUNK_VALUES` budget holds this 1,500-bar frame in ONE chunk, so a
per-chunk (rather than per-row) mean or sd mixes every row's own future bars
into every other row's output. The pytest module runs the same mutants on a
35-offset sweep and gets the matching result: 0 real leaks on the real
module, every mutant caught ≥ 10 of 35.

### B3. The bad-return mask mutant

Dead on a clean frame (0 difference from the real module) and caught on a
frame with one injected NaN close, at 12 of 12 offsets tried.

### B4. The overflow guard is LOAD-BEARING here, measured not assumed

Unlike `c22_mode_10`'s equivalent guard (redundant with a separate width
check), this module has NO other check that would catch an `sd = inf`
window. `no-overflow-guard` (drops `~np.isfinite(sd)`) is inert on all six
synthetic frames (bit-identical to the real module — none reaches an `sd`
overflow). A designed adversarial window (one close pair of ratio 1e200,
making one return's SQUARE overflow `float64` inside `block.std`, so `sd`
comes back `inf`) blanks under the real module via that guard, and removing
the guard genuinely REVIVES all 100 would-be-blanked bars with a concrete
value of **0.0** (not NaN): with `sd = inf`, every z-score collapses to
`0.0`, the 3-point forecast of three zeros is `0.0`, every residual is
`0.0`, and `std([0]*97, ddof=1) = 0.0`. Pinned in
`tests/test_c22_forecast_error.py::
test_the_overflow_guard_is_load_bearing_on_a_designed_adversarial_window`.

## C. Gate C — reachability

1,500-bar synthetic frames, 100-bar warm-up:

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 1,400 | 1.0284 .. 1.2433 | 1.1556 |
| tick-rounded | 1,400 | 1,400 | 1.0361 .. 1.2502 | 1.1633 |
| penny | 1,400 | 1,400 | 1.0264 .. 1.2305 | 1.1505 |
| ar1 | 1,400 | 1,400 | 0.7759 .. 1.1311 | 0.9398 |
| cosine (period 20) | 1,400 | 199 | 0.6001 .. 0.6170 | 0.6086 |
| student-t | 1,400 | 1,400 | 0.6027 .. 1.2433 | 1.1585 |

Every bar with a full window fires on all six frames. All six stochastic/
walk-like frames read CLOSE TO 1 (median 0.94 to 1.16) — "a 3-bar mean
forecast cannot do much better than the window's own scale" is the "nothing
to see here" reading for a near-random-walk return series, as the module
docstring states. The cosine frame reads near 0.61 (not near 1): a clean,
smooth periodic signal's 3-point trailing mean genuinely tracks it well,
so the residual (and its std) is well below the z-scored window's own
scale — the feature behaving as the definition predicts on a
degenerate-by-construction input, not a dead column.

### C1. The issue's own worry: tick-rounded BIST-shaped data

`penny` (a 2-lira stock on a 1-kurus tick): **21.68%** of its one-bar
returns are exactly 0.00%. The column still fires on all 1,400 eligible
bars and reads 1,400 distinct values — tick rounding does not collapse this
column's reachability the way the issue worried a shape feature might.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64) | 12 of 12 **bit-identical** |
| six frames × (×2⁻⁴⁰, ×2⁴⁰) | 12 of 12 **bit-identical** (24 total, incl. `penny`) |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`; z-scoring then cancels the
constant exactly in real arithmetic (and every later step — the trailing
mean, the residual, its own std — is a further linear function of `Z`), and
a power-of-two rescale is exact in floating point too.

### D2. Inexact rescale

| frame | factor | worst |diff| |
|---|---|---|
| walk | ×10.0 | 6.7e-16 |
| walk | ×3.7 | 6.7e-16 |
| walk | ×0.1 | 9.1e-15 |
| walk | ×1.0000001 | 1.1e-15 |

Not bit-identical by construction (these factors are not exact in binary),
but the output is unchanged in EXACT real arithmetic (z-scoring cancels any
positive affine rescale of the returns), and the measured gap is
machine-precision noise, nowhere near the 1e-6 tolerance
`tests/test_c22_forecast_error.py` pins.

### D3. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on the walk frame. Five of six frames (all but `cosine`)
have at least 20 distinct rounded values and a range wider than 0.01
z-units; `cosine` is near-constant by construction (§C).

## E. Gate E — attribution

Run `is137-c22_forecast_error-b3f2ffe8`, 89 frozen ALTPORT-1 BIST frames,
398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal
(AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS), `pandas_ta_src_sha1`
`f92ae67d7c331c09388e0b5bb01a6160ebb8d1fc`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | per-frame against | verdict |
|---|---|---|---|---|---|---|
| `C22FORECASTERROR_100` | 0.1832 | `mad_pct` | 389,949 | 0.1959 | `BB_BWidth` | **SHIP** |

0.1832 is well under the 0.76 ship line (`r3-perframe-0.90` band); 0 of 89
per-frame windows read ≥ 0.90 against any comparator. Recorded in
`docs/gate_e_ledger.csv` as `c22_forecast_error:C22FORECASTERROR_100`.

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_c22_forecast_error.py` | **105 passed** |
| the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_forecast_error_cpu.py`) | **105 passed** |
| `python docs/measure_c22_forecast_error_cpu.py A B C D G` — re-measured under the disabled dispatch | every structural figure (fires, distinct-count bounds, mutant catch counts, bit-identical cells) identical to the default-dispatch run; float values agree to the same ~1e-15 noise floor, not digit-for-digit |
| `python docs/measure_c22_forecast_error_cpu.py P` — the GPL-3.0 black box re-measured under the disabled dispatch | identical to the default-dispatch run: 0 of 8,400 disagree beyond 1e-9, worst |diff| 1.1e-15 |
| `python -m pytest -q tests/test_c22_forecast_error.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **1,435 passed, 7 skipped** — the Gate E ledger row is now recorded, so `test_every_indicator_that_needs_a_row_has_one` is green |

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring, all five touch points measured live

The module exists; it is exported from `pandas_ta.statistics`;
`"c22_forecast_error"` is in `Category["statistics"]`;
`df.ta.c22_forecast_error()` returns `C22FORECASTERROR_100` bit-equal to the
function and forwards `length` and `offset`; `tests/
test_c22_forecast_error.py` exists. README's three counts moved
367 → 368, 375 → 376 and statistics 65 → 66; `CATEGORY_TOTAL` in
`tests/test_altport2_ports.py` moved 367 → 368; `docs/IndicatorDictionary.md`
was regenerated by its own generator (tagged `SF`, warm-up 100);
`docs/MLCompanionContract.md`'s tagged-column counts moved 712 → 713 /
347 → 348 `SF`.

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

The ladder and the flat frame are both below the floor on every window that
could hold them; the 1-kurus/100 frame is real variation (a genuine, if
tiny, non-zero return) and fires on every eligible window.

## H. Bad data and edge cases

| input | behaviour |
|---|---|
| `close` holding NaN / ±inf / 0 / −1 / 1e−310 | bad return propagates to NaN on that window the same way as this fork's other return-based catch22 ports |
| `n` = 99 or 100 | `None` — `length` = 100 returns need 101 closes |
| `n` = 101 | 1 bar fires |
| `n` = 102 | 2 bars fire |
| `length` = None / 0 / 1 / `MIN_LENGTH - 1` (4) | falls back to 100, column named `C22FORECASTERROR_100` |
| `length` = `MIN_LENGTH` (5) | fires on `1500 - 5 = 1495` bars, column named `C22FORECASTERROR_5` |
| `length` = 250 or 250.7 | fires on 1,250 bars, column named `C22FORECASTERROR_250` |
| chunk boundary (`CHUNK_VALUES` forced to 100, 400, 1024) | bit-identical to the default budget on all three |
| `offset` = 2 | shifts the series by 2, bit-identical to the unshifted column elsewhere |
| `fillna` = -99 | 0 NaN remain; exactly the 100 warm-up bars read -99 |
| adversarial window, one close pair of ratio 1e200 | blanked by the overflow guard (100 bars); removing the guard revives them all at exactly 0.0 (§B4) |

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_forecast_error.py P`. Not run by a bare invocation,
and the module is not imported unless the section runs.

### P1. The candidate fit that settled `ZSCORE_DDOF` and `RESID_DDOF`

Six candidate (z-score ddof, residual-std ddof) readings tried against
`pycatch22.catch22_all(...)["FC_LocalSimple_mean3_stde"]` on 366 sampled
windows (every 23rd of six frames):

| candidate | disagree(>1e-6) | worst |diff| |
|---|---|---|
| `(1, 1)` — **SHIPPED** | 0 / 366 | 8.9e-16 |
| `(1, 0)` | 366 / 366 | 6.4e-3 |
| `(0, 1)` | 366 / 366 | 6.3e-3 |
| no z-score, resid ddof 1 | 366 / 366 | 1.23 |
| `(1, 1)` divided by `sqrt(length - 3)` — literal "std ERROR" | 366 / 366 | 1.12 |
| `(0, 0)` | 366 / 366 | 1.9e-4 |

Only `ddof=1` on BOTH reproduces the reference; every other candidate
disagrees on every single sampled window, by margins from 1.9e-4 to 1.23 —
far outside any plausible float-noise band, so this is not a close-call fit.

### P2. Shipped against the reference, every window of six frames

| frame | windows | disagree (>1e-6) | disagree (>1e-9) | worst |diff| |
|---|---|---|---|---|
| walk | 1,400 | 0 | 0 | 8.88e-16 |
| tick-rounded | 1,400 | 0 | 0 | 8.88e-16 |
| penny | 1,400 | 0 | 0 | 1.11e-15 |
| ar1 | 1,400 | 0 | 0 | 6.66e-16 |
| cosine | 1,400 | 0 | 0 | 4.44e-16 |
| student-t | 1,400 | 0 | 0 | 8.88e-16 |
| **TOTAL** | **8,400** | **0** | **0** | **1.11e-15** |

Unlike this fork's other catch22 ports (`c22_mode_10`/`c22_mode_5`: a
float32-vs-float64 boundary flip on a repeated-value frame; `c22_periodicity`:
an unresolved biased-divisor gap), there is NO residual disagreement to
root-cause here: every one of 8,400 sampled windows across six frames,
including the tick-rounded `penny` frame the issue specifically worried
about, agrees with the GPL-3.0 reference to machine-precision float noise
(worst 1.1e-15). Re-run under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`: identical, 0 of
8,400 disagree beyond 1e-9, worst |diff| 1.1e-15.
