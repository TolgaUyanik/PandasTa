# `c22_acf_first_min` — measured

PandasTa issue **#131** (C22-ACF-FIRST-MIN), ported 2026-11-21 on branch
`issue-131-c22-acf-first-min`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_acf_first_min.py` |
| column | `C22ACFFIRSTMIN_100` (`ORD`, a whole number in `[1, 100]`) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `CO_FirstMin_ac` — the hctsa operation `CO_FirstMin(y, 'ac')`; reference code pycatch22 1.x, **GPL-3.0** — ported from the definition |
| tests | `tests/test_c22_acf_first_min.py` (31 tests) |
| harness | `docs/measure_c22_acf_first_min.py` (sections A, B, C, D, E, G, **P**; P is opt-in and is the only part of this repository that imports the GPL-3.0 reference), `docs/measure_c22_acf_first_min_cpu.py` |
| Gate A | 0 disagreements against an independent double-loop oracle (1,200 sampled windows of six frames) **and** 0 disagreements against the actual GPL-3.0 reference, `pycatch22.CO_FirstMin_ac`, on **every** window of six frames (8,400), Spearman +1.0000 — §A, §P |
| Gate B | causal; 0 of 43 offsets leak on six frames; one mutant (write index back-dated one bar) caught 43 of 43 — §B |
| Gate C | fires on every bar with a full window on all six synthetic frames (1 to 12 distinct values; the cosine frame constant at 10 by construction); the `length` sentinel reached on 0 of 8,400 synthetic windows — §C |
| Gate D | ×8/×64 bit-identical; 0 of 1,400 bars moved under ×10 on each of six frames; `0 < fires < n`; not constant on five of six frames — §D |
| Gate E | max \|ρ\| **0.1058** vs `Swing_Range_pct` (manifest, n = 389,949); per-frame max median 0.1030 vs `natr` (89 frames) — **SHIP** — §E |
| Gate F | PandasTa green (31 module tests, both dispatches; required subset below); whole suites run by issue-solver in clean worktrees — §F |

Every number below was produced by `python docs/measure_c22_acf_first_min.py`
(and, for the CI CPU-dispatch row, `docs/measure_c22_acf_first_min_cpu.py`) on
this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11), except §E's BIST row,
which the launcher measures.

---

## 0. What the column is

```
r[t]    = close[t] / close[t-1] - 1
X       = r[T-99 .. T]                       (the 100 returns ending at T)
d       = X - mean(X)
acov(k) = sum(d[:100-k] * d[k:]) / 100,       k = 0 .. 99
acf(k)  = acov(k) / acov(0)
C22ACFFIRSTMIN = min{k in 1 .. 98 :
                      acf(k - 1) > acf(k) and acf(k) < acf(k + 1)};
                 else 100
```

**100 is both the CEILING of the scale and a SENTINEL** for "no interior
local minimum found in the range this scan can see" — not a long lag in
the ordinary sense. On every synthetic frame tried here it is never
reached (§C); whether real BIST data reaches it is unmeasured in this
receipt.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa's 7,000+, selected by Lubba et al.
(2019) for **time-series classification** performance over 93 reference
problems. That is not return prediction, and nothing in this repository
tests it on BIST: the feature's presence here is existence, not evidence.
The issue says so and this receipt repeats it.

The reference implementation is GPL-3.0 and this fork is MIT. The port was
written from the DEFINITION — "the first local minimum of the series' own
autocorrelation function" is public-domain mathematics, not reference
code — and the sample-autocorrelation convention (demeaned once, divided
by `length` at every lag, FFT-based) is the same transform and divisor
this fork's own `firstzero_ac` already uses on the identical window of
returns. No shipped module imports the reference:
`test_no_shipped_module_imports_pycatch22` sweeps every `.py` file under
the repository root for an import statement mentioning `pycatch22` and
finds none. ⚠ pycatch22 **is installed in this worktree**, so that guard
is not vacuous.

The one place the reference is run at all is
`docs/measure_c22_acf_first_min.py` section **P** (opt-in; a bare run
skips it and does not import it) — MEASUREMENT only, the same use the
owner's own screen prototype makes of it. The result is in §P: **bit-equal
on every one of 8,400 windows**, the best match any catch22 port in this
fork has produced against the black box so far (`c22_periodicity` matched
8,387 of 8,400; `c22_ami2` matched to 1e-12 but not bit-equal).

⚠ catch22 is a subset selected for TIME-SERIES CLASSIFICATION performance
on 93 reference problems. That is not return prediction, and nothing here
tests it on BIST: its presence in this fork is existence, not evidence.

## A. Gate A — correctness

### A1. Against an independent double loop (no FFT, no module code)

Every 7th window of six 1,500-bar synthetic frames (an iid walk, a
tick-rounded walk, a 2-lira stock on a 1-kurus tick, an AR(1)-in-returns
path, a 20-bar cosine, a Student-t(3) path), 200 windows each, 1,200
total:

| frame | windows | disagree |
|---|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | 200 each | **0** |

### A2. Closed forms

* Alternating returns (`+a, -a, +a, -a, ...`): `acf(0) = 1`, `acf(1) < 0`,
  `acf(2) > 0` — an immediate local minimum at the very first interior
  lag. Every fired bar of a 150-bar frame reads **1**.
* A linear return ramp (`np.linspace(0.02, -0.02, 400)`): the
  autocorrelation has exactly one interior local minimum, at a lag fixed
  by the window's own length rather than by its slope — every fired bar
  of a 400-bar frame at `length` 100 reads the SAME value, **71**. (The
  module's own docstring originally guessed this ramp would be
  monotonically falling with no interior minimum at all, hence the
  sentinel; measuring it showed that guess wrong, so the test pins the
  measured constant instead of the guess.)

### A3. Against the GPL-3.0 reference, every window of six frames — see §P

**0 of 8,400 disagree.** This section exists separately from §P because
§P is opt-in and this repository's CI does not run it; §A1/§A2 are the
ungated correctness evidence, §P is the (measured, not assumed)
confirmation that the definition was read correctly.

## B. Gate B — causality

### B1. The real module

Future-perturbation sweep: replace every close from bar J on with a
×1000 jump, and no bar before J may move. 43 offsets per frame:

| frame | leaking offsets |
|---|---|
| walk, tick-rounded, penny, ar1, cosine, student-t | **0 / 43** each |

### B2. One mutant, read off this module's source, edited and exec'd in memory

| mutant | edit | walk | cosine |
|---|---|---|---|
| `write-back-dated` | `out[length + a:length + b] = vals` → one bar earlier | 43 / 43 | 43 / 43 |

The pytest module (`tests/test_c22_acf_first_min.py`) runs the same
mutant on a 16-offset sweep (`OFFSETS = range(130, 600, 30)`) and gets
the matching result: 0 real leaks, 16 of 16 mutant leaks.

### B3. A bad tick

A ×1000 close at bar 300 changes the returns at bars 299 and 300, which
only the windows ending at bars 300..400 can hold. Measured: the moved
bars are a (non-empty) subset of that range, and every bar outside it is
bit-identical to the unperturbed column — not every window in the range
changes VALUE (a single huge return deep in a 100-lag window often does
not move which lag is the first local minimum), which is why the test
bounds the moved set rather than pinning its size: that count is decided
by float comparisons the CI CPU dispatch can move.

## C. Gate C — reachability

1,500-bar synthetic frames, 100-bar warm-up:

| frame | fired | distinct | range | median | sentinel (== 100) |
|---|---|---|---|---|---|
| walk | 1,400 / 1,500 | 6 | 1 .. 7 | 2 | 0 |
| tick-rounded | 1,400 | 5 | 1 .. 5 | 2 | 0 |
| penny | 1,400 | 5 | 1 .. 5 | 2 | 0 |
| ar1 | 1,400 | 12 | 3 .. 14 | 6 | 0 |
| cosine (period 20) | 1,400 | **1** (constant 10) | 10 .. 10 | 10 | 0 |
| student-t | 1,400 | 5 | 1 .. 5 | 2 | 0 |

Every bar with a full window fires. **The sentinel is never reached on
any of these six frames** (0 of 8,400 bars) — real BIST data, where a
fifth of the returns on a low-priced stock can be exactly 0.00%, is
unmeasured here and is the launcher's Gate E run's job to surface if it
changes this.

## D. Gate D — scale-free

### D1. Exact binary rescales — bit-identical

| cell | result |
|---|---|
| six frames × (×8, ×64) | 12 of 12 **bit-identical** |

By construction: the price enters only as `close[t] / close[t-1]`, and
`8a / 8b` is the same double as `a / b`.

### D2. Inexact rescale

| frame | ×10 |
|---|---|
| all six | 0 bars moved |

Not promised by the arithmetic — the output is an integer decided by
float comparisons — and the test bounds it (≤ 1% of fired bars) rather
than pinning 0.

### D3. `0 < fires < n`, and not constant

`0 < 1,400 < 1,500` on the AR(1) frame (12 distinct values); the cosine
frame is constant at 10 **by construction** (§A2-equivalent: a clean
periodic signal has one dominant interior minimum), which is the feature
working rather than a dead column.

## E. Gate E — run by the launcher, 2026-11-21

Run `is131-c22_acf_first_min-7c74208a`, module `pandas_ta.statistics.c22_acf_first_min`,
89 ALTPORT-1 BIST frames, 398,849 pooled bars, 329 + 358 = 687 comparators,
canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | per-frame against | verdict |
|---|---|---|---|---|---|---|
| `C22ACFFIRSTMIN_100` | 0.1058 | `Swing_Range_pct` (manifest) | 389,949 | 0.1030 | `natr` | **SHIP** |

0.1058 is well under the DISCLOSE floor (0.76), let alone the STRUCK line
(0.90 pooled or per-frame median) — **SHIP**, recorded in
`docs/gate_e_ledger.csv`.

`docs/C22PeriodicityMeasured.md` section E4 named this exact pair in
advance (`C22PERIODICITY_100` reads the same 100 returns' autocorrelation,
through a detrending spline this feature does not apply) with the rule
that a real strike against that pair would revert or waive one of the two.
Gate E's comparator set is the engine ∪ manifest, not sibling-to-sibling,
so this run does not directly test that pair; `C22ACFFIRSTMIN_100`'s own
max |ρ| (0.1058, a price-level column) clears independently of it.

### E1. A synthetic-frame advisory (NOT Gate E)

Spearman between `C22ACFFIRSTMIN_100` and `C22PERIODICITY_100` on the
same six synthetic frames (`docs/measure_c22_acf_first_min.py` section E):

| frame | walk | tick-rounded | penny | ar1 | student-t | pooled |
|---|---|---|---|---|---|---|
| Spearman | -0.2221 | -0.1167 | -0.3167 | +0.5817 | -0.4091 | +0.2762 |

Lower than `C22PeriodicityMeasured.md`'s own advance-warning PROXY figure
of +0.807 pooled — that proxy used a different autocorrelation spelling
(z-scored, no detrend, a different divisor) than either shipped column,
so the two numbers are not measuring the same comparison. ⚠ **This is a
synthetic-frame figure and is not Gate E.** The real question — real BIST
returns, 89 ALTPORT-1 frames, the `r3-perframe-0.90` bands — is the
launcher's to answer.

## F. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_c22_acf_first_min.py` | **31 passed** |
| the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_c22_acf_first_min_cpu.py`) | **31 passed** |
| `python docs/measure_c22_acf_first_min_cpu.py A B C D G` — re-measured under the disabled dispatch | every figure in §A, §B, §C, §D, §G identical, digit for digit, to the default-dispatch run |
| `python docs/measure_c22_acf_first_min_cpu.py P` — the GPL-3.0 black box re-measured under the disabled dispatch | 0 of 8,400 disagree, identical to the default-dispatch run |
| `python -m pytest -q tests/test_c22_acf_first_min.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **1,329 passed, 7 skipped** — `test_gate_e_ledger.py` now passes: the row recorded by `docs/gate_e_ledger.py record` on the launcher's run |

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring, all five touch points measured live

The module exists; it is exported from `pandas_ta.statistics`;
`"c22_acf_first_min"` is in `Category["statistics"]`;
`df.ta.c22_acf_first_min()` returns `C22ACFFIRSTMIN_100` bit-equal to the
function and forwards `length` and `offset`; `tests/test_c22_acf_first_min.py`
exists. README's three counts moved 363 → 364, 371 → 372 and
statistics 61 → 62; `CATEGORY_TOTAL` in `tests/test_altport2_ports.py`
moved 363 → 364; `docs/IndicatorDictionary.md` was regenerated by its own
generator (tagged `ORD`, warm-up 100).

## G. The floor, and what it buys

`NOISE_ULPS = 64`, relative to `max(|1 + r|)` over the window — the same
constant and the same relative scale `firstzero_ac` uses on the identical
window of returns.

| input | guarded fires | unguarded fires | differ |
|---|---|---|---|
| six realistic frames | 1,400 each | 1,400 each | **0** |
| price flat except ONE 1-ulp step (400 bars) | **0** | — | — |
| one 1-kurus tick per bar at 100 (a 1e-4 return, 300 bars) | **200** | — | — |
| 400 identical closes | **0** | — | — |

The one-ulp step and the flat frame are both below the floor on every
window that could hold them; the 1-kurus/100 frame is real variation
(2e-4 relative, far above the floor) and fires on every eligible window,
the same result `firstzero_ac` and `c22_ami2` report on close variants of
this same frame.

## H. Bad data

| input | behaviour |
|---|---|
| `close[150]` = NaN / ±inf / 0 / −1 / 1e−310 | exactly 101 bars blank, 150..250 (the bad close kills the returns on both sides of it) |
| `close[150]` = 1e−150 then `close[151]` = 1e150 — a finite return of ~1e300 whose SQUARE overflows | 100 bars blank, 151..250; bars 150 and 251 still fire (each reads only the one finite return into or out of the pair) |
| `n` = 100 | `None` — `length` returns need `length + 1` closes |
| `n` = 101 | 1 bar fires |
| `length` = None / 0 / 1 / 2 | falls back to 100 (`MIN_LENGTH` is 3: the scan needs `acf(0)`, `acf(1)`, `acf(2)` to test the first candidate lag) |
| `length` = 3 | 147 of 150 bars fire |
| chunk boundary (`CHUNK_CELLS` forced to 700) | bit-identical to the default budget |

## P. The reference implementation as a black box (GPL-3.0, opt-in)

`python docs/measure_c22_acf_first_min.py P`. Not run by a bare invocation,
and the module is not imported unless the section runs.

### P1. Shipped against `pycatch22.CO_FirstMin_ac`, every window of six frames

| frame | windows | disagree | Spearman |
|---|---|---|---|
| walk | 1,400 | 0 | +1.0000 |
| tick-rounded | 1,400 | 0 | +1.0000 |
| penny | 1,400 | 0 | +1.0000 |
| ar1 | 1,400 | 0 | +1.0000 |
| cosine | 1,400 | 0 | (constant, Spearman undefined) |
| student-t | 1,400 | 0 | +1.0000 |
| **TOTAL** | **8,400** | **0** | |

**This port's column is bit-equal to the GPL-3.0 reference's on every
window tried.** Re-run under `NPY_DISABLE_CPU_FEATURES="AVX512F
AVX512_SKX AVX2 FMA3"`: identical, 0 of 8,400 disagree.
