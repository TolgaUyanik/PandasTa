# `c22_whiten_timescale` — measured

PandasTa issue **#139** (C22-WHITEN-TIMESCALE), ported 2026-11-20 on branch
`issue-139-wip`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_whiten_timescale.py` |
| column | `C22WHITEN_100` (a ratio of two crossing lags; in practice `1 / tau(returns)`) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `FC_LocalSimple_mean1_tauresrat` — hctsa's `FC_LocalSimple(y, 'mean', 1)` output `taures` over `CO_FirstZero(y, 'ac')`; reference code pycatch22, **GPL-3.0** — ported from the definitions, reference not run |
| tests | `tests/test_c22_whiten_timescale.py` (185 tests) |
| harness | `docs/measure_c22_whiten_timescale.py` (sections S, A–E, G, H, T, X, Z), `docs/measure_c22_whiten_timescale_cpu.py` (the same sections, or the test module, with numpy's AVX2 and FMA3 dispatch disabled) |
| Gate A | bit-equal to a literal re-spelling of the definition on **8,400 of 8,400** windows with numpy's default dispatch, 8,399 with AVX2 and FMA3 disabled (the split is a rounding coin flip in the REFERENCE; the exact oracle sides with the module); exact rational oracle 0 of 648 disagree, and 0 of 1,400 on the cosine frame under both dispatches (§X) — §A |
| Gate B | causal; 0 of 35 offsets leak on six frames × eight splices and at `length` 10/30/250; seven mutants — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames; real data **owed** with Gate E — §C |
| Gate D | ×8/×64/2^±40 bit-identical; inexact rescales 0 bars on the five stochastic frames, 24–33 of 1,400 on the exact cosine — §D |
| Gate E | Gate E: pending, run by issue-solver — §E |
| Gate F | PandasTa targeted suites green; full suites run by the orchestrator — §F |

Every number below was printed by `python docs/measure_c22_whiten_timescale.py`
on this machine, with three exceptions: the disabled-dispatch figures of §A1
and §X, printed by `python docs/measure_c22_whiten_timescale_cpu.py A X`; the
test counts in the table above and in §F, from the pytest commands quoted in
§F; and the 2026-10-24 screen figures in §E, which are the owner's PROTOTYPE
measurements and are quoted from issue #139.

## 0. What the column is

    r[t]      = close[t] / close[t-1] - 1
    X         = r[T-99 .. T]
    E         = X[1:] - X[:-1]          (catch22 `mean1`: predict r[t] by r[t-1])
    tau(x)    = first lag k >= 1 whose autocorrelation of x is <= 0
    C22WHITEN = tau(E) / tau(X)

**On noise the numerator is 1, so the column is `1 / tau(returns)`** — a
coarse reciprocal ladder 1, 1/2, 1/3, …:

| frame | fired | distinct | min | median | max | share == 1 | numerator == 1 | tie rate | largest lag |
|---|---|---|---|---|---|---|---|---|---|
| walk | 1400 | 7 | 0.1250 | 0.5000 | 1.0000 | 0.470 | 1400/1400 | 0.905 | 8 |
| tick-rounded | 1400 | 8 | 0.1111 | 1.0000 | 1.0000 | 0.586 | 1400/1400 | 0.919 | 9 |
| penny | 1400 | 8 | 0.1250 | 0.5000 | 1.0000 | 0.263 | 1400/1400 | 0.880 | 8 |
| ar1 (phi 0.6) | 1400 | 17 | 0.0500 | 0.1667 | 0.6667 | 0.000 | 1397/1400 | 0.848 | 20 |
| cosine (P 20) | 1400 | 3 | 0.8333 | 0.8333 | 1.2000 | 0.094 | 0/1400 | 0.706 | 6 |
| student-t | 1400 | 6 | 0.1667 | 1.0000 | 1.0000 | 0.562 | 1400/1400 | 0.936 | 6 |

Values on the walk: `[0.125, 0.166667, 0.2, 0.25, 0.333333, 0.5, 1.0]`.

## 1. Attribution, and what it is NOT evidence of

catch22 is a subset of hctsa selected for TIME-SERIES CLASSIFICATION on 93
problems. That is not return prediction, and nothing here tests it on BIST:
existence, not evidence. The reference implementation is GPL-3.0; this
module was written from the definitions, no shipped module imports it (a
test sweeps `pandas_ta/`), and it is not installed on this machine, so
nothing here ran it.

## A. Gate A — correctness

### A1. Against a literal re-spelling of the definition, EVERY window

The reference in `docs/measure_c22_whiten_timescale.py` z-scores the window,
takes catch22's FFT autocorrelation (demeaned, padded to twice the next power
of two, divided by lag 0), walks `while acf[z] > 0 and z < maxtau`, and builds
the mean-forecast residual by a loop. Shares no code with the module, which
never divides (only the sign of each lagged sum matters).

| frame | windows | moved | NaN-mask |
|---|---|---|---|
| walk | 1400 | 0 | 0 |
| tick-rounded | 1400 | 0 | 0 |
| penny | 1400 | 0 | 0 |
| ar1 | 1400 | 0 | 0 |
| cosine | 1400 | 0 | 0 |
| student-t | 1400 | 0 | 0 |

**8,400 of 8,400 agree** with numpy's default (AVX2/FMA3) kernels.

⚠ **With numpy's AVX2 and FMA3 dispatch disabled** —
`python docs/measure_c22_whiten_timescale_cpu.py A`, which sets
`NPY_DISABLE_CPU_FEATURES="AVX2 FMA3"` before importing numpy, prints the
features still enabled (`SSSE3, SSE41, POPCNT, SSE42, AVX, F16C`) and refuses
to run if AVX2 or FMA3 is among them — the same section prints:

    cosine | windows 1400 | moved 1 | mask 0 | exact oracle sides with the module on 1 of 1
      split: cosine window 1122 (bar 1222) | module 0.8333 | FFT spelling 1.0000 | exact 0.8333
    total | 8399 of 8400 agree

The deciding lagged sum on that frame is zero for the ideal cosine and sits at
6.78e−18 of the sum of squares on the rounded inputs (§D3), so the FFT
spelling's rounding decides it. Section X runs the module against the exact
oracle on all 1,400 cosine windows: `python docs/measure_c22_whiten_timescale.py X`
and `python docs/measure_c22_whiten_timescale_cpu.py X` both print
`0 disagreements of 1400 windows`. The test pins that: exact agreement on the
five stochastic frames, and on the cosine frame at most 5 splits, each one
won by the module against the exact oracle. The test module itself, under the
same disabled dispatch: `python docs/measure_c22_whiten_timescale_cpu.py`.

### A2. Exact rational oracle

Input doubles, mean, deviations and every lagged sum as `Fraction`s: **0
disagreements of 648 windows** (stride 13, six frames).

### A3. Why the numerator is almost always 1

For a stationary `r` the lag-1 autocorrelation of `r[t] - r[t-1]` is
`(2 rho1 - 1 - rho2) / (2 (1 - rho1))`: −1/2 for white noise, −(1 − phi)/2
for an AR(1). Measured lag-1 autocorrelation of the residual per window:

| frame | max | median |
|---|---|---|
| walk | −0.3328 | −0.4812 |
| tick-rounded | −0.3285 | −0.4866 |
| penny | −0.2549 | −0.4755 |
| ar1 | +0.0104 | −0.1547 |
| cosine | +0.9506 | +0.9412 |
| student-t | −0.0812 | −0.4941 |

Numerator == 1 on AR(1) frames by phi: 1,400 of 1,400 at 0.3, 1,397 at 0.6,
1,095 at 0.8, 691 at 0.9, 557 at 0.95 — sampling noise flips a lag-1
autocorrelation near zero. Cosine returns of period P read near 1 (P = 20:
0.8333 / 1.0 / 1.2; P = 200: 0.6111 .. 0.75), numerator and denominator
both near P/4.

### A4–A5. Conventions that decide nothing here

Z-scoring the window: 0 moved of 200 sampled windows on each frame. Exact-zero
lagged sums met in any scan (`> 0` against `>= 0`): 0 on each frame.
`maxtau = size` is unreachable: the biased autocovariances over lags 1 .. m−1
sum to minus half the lag-0 one.

### A6. Not `firstzero_ac`

Kats' rule (first positive-then-negative sign change, smallest value 2)
cannot report lag 1. Windows with `tau(r) == 1`: walk 658, tick-rounded 821,
penny 368, ar1 0, cosine 0, student-t 787. Per-frame Spearman against
`FIRSTZEROAC_100`: +0.3057, +0.6335, −0.0978, −0.9993, −0.9619, +0.5279.

## B. Gate B — causality

### B1. Real module
0 of 35 offsets leak on each of the six frames (eight splices each), and 0 of
35 on the walk at `length` 10, 30 and 250 (four splices).

### B2. Mutants (offsets caught of 35)

| mutant | walk | tick-rounded | ar1 |
|---|---|---|---|
| write-back-dated | 8 | 8 | 20 |
| window-one-ahead | 8 | 8 | 20 |
| window-ten-ahead | 29 | 26 | 35 |
| returns-rolled | 8 | 8 | 20 |
| mask-back-dated | 0 | 0 | 0 |
| chunk-wide-demean | 33 | 34 | 34 |
| no-overflow-guard | 0 | 0 | 0 |

The mask mutant is bit-equal on a clean frame and caught 12 of 12 on a frame
with one NaN close, the first moved bar always J − 1. The overflow mutant is
not a look-ahead: inert on all six frames, it changes only §H's overflow case.
Where the one-bar mutant moves a pre-splice bar (4 of 35 offsets on the walk)
the first moved bar is J − 1. The low one-bar counts are the ties of §0.

## C. Gate C — reachability

### C1. Synthetic frames
Fired 1,400 of 1,500 on all six, first fired bar 100; distinct 7 / 8 / 8 / 17
/ 3 / 6.

### C2. The issue's worry: tick rounding

| frame | zero returns | median | share == 1 |
|---|---|---|---|
| walk | 0.000 | 0.5000 | 0.470 |
| tick-rounded | 0.003 | 1.0000 | 0.586 |
| penny | 0.217 | 0.5000 | 0.263 |

### C3. Real data — **OWED**, measured by the launcher's Gate E run.

## D. Gate D — scale-free

### D1. Exact binary rescales
×8, ×64, ×2^−40, ×2^40 bit-identical on all six frames; ×8 and ×64 at
`length` 10, 30, 250; ×8 at levels 1e−6, 1e+6, 1e+100 (each 1,400 fired).

### D2. Inexact rescales (bars moved, mask differences)

| frame | ×10 | ×3.7 | ×0.1 | ×1.0000001 |
|---|---|---|---|---|
| walk | (0, 0) | (0, 0) | (0, 0) | (0, 0) |
| tick-rounded | (0, 0) | (0, 0) | (0, 0) | (0, 0) |
| penny | (0, 0) | (0, 0) | (0, 0) | (0, 0) |
| ar1 | (0, 0) | (0, 0) | (0, 0) | (0, 0) |
| cosine | (30, 0) | (33, 0) | (33, 0) | (24, 0) |
| student-t | (0, 0) | (0, 0) | (0, 0) | (0, 0) |

### D3. Margin
Smallest |lagged sum| / sum of squares at a scanned lag: walk 2.98e−05,
tick-rounded 4.81e−05, penny 1.66e−05, ar1 2.23e−05, student-t 1.22e−04 —
and cosine **6.78e−18**: an exact cosine of period 20 has a lagged sum that is
zero in exact arithmetic, so its sign is a rounding coin flip and §D2's cosine
row is that, not a scale dependence.

### D4. Order matters
Permuting each walk window moves 320 of 467 (stride 3). `0 < fires < n` on
every frame (§C1).

## E. Gate E — Gate E: pending, run by issue-solver

Not runnable here. The 2026-10-24 screen measured the PROTOTYPE, not this
port: max |ρ| **0.2521** vs `mad_pct` (n = 389,949), top-5 per-frame max median
0.2504 → SHIP. That is an expectation for this column, not a result: the
prototype (`docs/issues/screen/ind_screen_r3.py`) exists only on the owner's
machine, so this port's agreement with it is unmeasured.

### E3. In-fork overlap (6 synthetic frames, Spearman per frame)

Frames in order walk, tick-rounded, penny, ar1, cosine, student-t:

| column | per frame | median \|ρ\| |
|---|---|---|
| `FIRSTZEROAC_100` | +0.306 +0.634 −0.098 −0.999 −0.962 +0.528 | 0.5807 |
| `TS_AC1_60` | −0.528 −0.632 −0.450 −0.388 −0.887 −0.675 | 0.5803 |
| `DIFF2ACF1_100` | +0.092 −0.577 −0.159 +0.087 +0.826 −0.659 | 0.3679 |
| `TF_AC1E_60` | −0.047 +0.156 +0.033 +0.016 n/a −0.022 | 0.0327 |
| `C22AMI_100` | −0.068 −0.043 +0.158 −0.479 n/a −0.001 | 0.0680 |
| `C22PERIODICITY_100` | −0.194 −0.009 −0.034 −0.100 n/a +0.225 | 0.1004 |
| `HLIFE_100` | −0.309 −0.128 −0.081 −0.027 +0.025 −0.138 | 0.1043 |

(n/a: the comparator is constant on the cosine frame.) The largest single
per-frame |ρ| is **0.999, against `FIRSTZEROAC_100` on the AR(1) frame**
(0.962 on the cosine), with the sign flipping between frames (−0.999 to
+0.634), so the median |ρ| is 0.5807. These are synthetic frames, not Gate E;
the bands that decide (0.76 / 0.80 / 0.90 per CLAUDE.md) are applied by Gate E
on the 89 BIST frames.

## F. Gate F — suites

Targeted run, `python -m pytest -q -p no:cacheprovider -W ignore
tests/test_c22_whiten_timescale.py tests/test_altport2_ports.py
tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py
tests/test_readme_counts.py tests/test_wiring_accessors.py`: 1,408 passed, 8
skipped, one of the skips being `test_gate_e_ledger`'s "Gate E owed … no Gate
E ledger row for ['c22_whiten_timescale']". The module alone with numpy's
AVX2 and FMA3 dispatch disabled, `python docs/measure_c22_whiten_timescale_cpu.py`:
185 passed. The full PandasTa suite and Backtesting's are run by the
orchestrator.

## G. The floor, and what it buys

| case | result |
|---|---|
| flat from bar 400 | last fired bar 499, 400 fired |
| geometric ladder 0.01 / 0.001 / −0.005 | 0 fired; window sd ≤ 1.44e−16; unguarded reference reads a value on 200 of 200 sampled windows |
| returns an exact line | 0 fired; window sd ≥ 2.89e−04, residual sd ≤ 2.37e−16 |
| one kurus a bar from 100.00 | **1,400 fired** (`c22_periodicity`: 0) |
| six frames, guarded vs unguarded | 0 moved, 0 mask |

## H. Bad data

A bad close (NaN, ±inf, 0, −5, 1e−310) at bar 700 blanks exactly 101 bars,
700..800. Close pair 1e−300 / 1e+100 blanks 100 (701..800); 1e−100 / 1e+100
blanks 100 through the overflow guard — without it those 100 bars read 1.0;
1e−50 / 1e+27 blanks none. Inputs of 99 and 100 closes return `None`; 101 → 1
fired, 102 → 2.

## T / Z. Cost and chunking

n = 400,000: 399,900 fired, 1.9 s, traced peak 30.7 MB. Chunk budgets 100,
400, 1,024 and the default are bit-equal.

## What a consumer must know

* The column is `1 / tau(returns)` on anything noise-like; it is not a
  ratio in any useful sense there. 1 means the returns' lag-1
  autocorrelation is already ≤ 0.
* It ties on 85–94% of neighbouring bars on stochastic frames.
* It is not `FIRSTZEROAC_100`: different crossing rule (§A6).
