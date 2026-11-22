# `c22_median_freq` — measured

PandasTa issue **#138** (C22-MEDIAN-FREQ), ported 2026-11-22 on branch
`issue-138-c22-median-freq`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_median_freq.py` |
| column | `C22MEDFREQ_100` (`SF`, radians per bar on (0, π], one of 65 grid values) |
| source | hctsa `SP_Summaries(y, 'fft')` output `wq_50` (`SP_Summaries_fft_wq_50`), screened with catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821); hctsa and pycatch22 1.0.2 are **GPL-3.0**, so this was ported from the definition. pycatch22 does not expose this feature (catch22 ships only the Welch `SP_Summaries` read-outs), so no black-box comparison was possible |
| tests | `tests/test_c22_median_freq.py` (114 tests) |
| harness | `docs/measure_c22_median_freq.py` (sections A, B, C, D, G, X) |
| Gate A | 1,200 of 1,200 sampled windows (every 7th window of six frames) agree EXACTLY (`==`) with a direct-DFT oracle (no FFT, `math.fsum`); smallest tie margin seen 2.1e-6; designed cosines at bins 5/20/40/63 return exactly `π·k/64`, a ±1 alternation returns `π` — §A |
| Gate B | causal; 0 of 43 offsets leak on six frames; four mutants caught on 14, 14, 40 and 43 of 43 offsets — §B |
| Gate C | fires on every bar with a full window (1,400 / 1,500) on all six frames; 15–24 distinct values on the five stochastic frames; `penny` (21.68% zero returns) fires everywhere with 19 distinct values — §C |
| Gate D | ×8/×64 bit-identical on 12/12 cells; ×10/×3.7 price and ×10/×3.7 return rescales move 0 bars with matching NaN masks (one cell aside, a test-series artifact: §D2); `0 < fires < n` — §D |
| Gate E | **owed**: not run here, no ledger row — §E |
| Gate F | targeted PandasTa run green (1,385 passed, 8 skipped, Gate E owed skip among them); full suites run by issue-solver — §F |

Every number below was produced by `python docs/measure_c22_median_freq.py`
(wall 165.9 s, peak traced memory 19.9 MB) or by `python -m pytest
tests/test_c22_median_freq.py`, on this machine (numpy 1.26.4, pandas
2.3.3, scipy 1.13.0, Python 3.11.18).

---

## 0. What the column is

```
r[t]   = close[t] / close[t-1] - 1
X      = r[T-99 .. T]                       (100 returns, closes T-100 .. T)
Z      = (X - mean(X)) / sd(X, ddof=1)
S_k    = |rfft(Z, 128)_k|^2,  k = 0 .. 64   (NFFT = 2^nextpow2(100) = 128)
w_k    = π k / 64
C22MEDFREQ_100 = w_j, j = first k with S_0 + .. + S_k > 0.5 · ΣS
```

Low: the window's power sits at low frequencies (trending, positively
autocorrelated returns). High: it alternates bar to bar (mean reversion).
White noise reads ≈ π/2.

Two choices the definition leaves open, made explicitly and stated in the
module docstring: the spectrum is POWER `|Y|²` (the feature's name), and the
crossing is the first bin whose running sum STRICTLY exceeds half. Any
constant normalisation of `S` cannot move a quantile and is left out.
Neither choice was checked against hctsa's source, which is GPL-3.0 and was
not read. §A1's tie margin (2.1e-6 at its smallest) says the strict-vs-
non-strict choice decided none of the 1,200 sampled windows.

The z-score's division by `sd` is inert in exact arithmetic. Its mean
removal is not: with 100 returns zero-padded to 128 slots, a window mean
leaks into the low bins.

## 1. Attribution, and what it is NOT evidence of

catch22 was selected for time-series CLASSIFICATION across 93 problems; this
feature is from hctsa, catch22's parent library, and came in through the
owner's catch22 screen, round 3. Nothing here tests it as a return
predictor on BIST: existence, not evidence. The prototype measurements in
issue #138 (Gate E 0.2169 vs `Swing_Range_pct`) are of the prototype, not
this port.

## A. Gate A — correctness

### A1. Against a direct-DFT oracle, every 7th window of six frames

The oracle (`direct_dft_median_freq`, in both the harness and the test
module) shares no code path with the module: explicit `math.cos`/`math.sin`
sums with the angle reduced modulo NFFT, every sum by `math.fsum`.

| frame | windows | exact agree | disagree |
|---|---|---|---|
| walk | 200 | 200 | 0 |
| tick-rounded | 200 | 200 | 0 |
| penny | 200 | 200 | 0 |
| ar1 | 200 | 200 | 0 |
| cosine | 200 | 200 | 0 |
| student-t | 200 | 200 | 0 |
| **total** | **1,200** | **1,200** | **0** |

Smallest |running power − half| / total on any sampled window: **2.143e-6**.
Exact agreement means something only because no sampled window was near a
grid boundary; the test asserts the margin `> 1e-9` on every window it
compares.

### A2. Designed windows with a known answer

| window | shipped | expected |
|---|---|---|
| pure cosine at bin 5, 128 samples | 0.2454369260617026 | π·5/64, equal |
| bin 20 | 0.9817477042468103 | π·20/64, equal |
| bin 40 | 1.9634954084936207 | π·40/64, equal |
| bin 63 | 3.0925052683774528 | π·63/64, equal |
| +1/−1 alternation, 100 samples | 3.141592653589793 | π (oracle agrees) |

### A3. Direction on AR(1) returns (seed 3, 1,400 bars each)

| φ | −0.6 | −0.3 | 0.0 | 0.3 | 0.6 |
|---|---|---|---|---|---|
| median | 2.6016 | 2.1598 | 1.5708 | 1.0308 | 0.5400 |
| mean | 2.5992 | 2.1402 | 1.5743 | 1.0160 | 0.5244 |

Monotone, and white noise sits at π/2 = 1.5708.

## B. Gate B — causality

### B1. The real module

Future replaced by an independent random path from offset `j` on (43
offsets, 130..1390 step 30): **0 / 43 leaking offsets** on each of walk,
tick-rounded, penny, ar1, cosine, student-t.

### B2. Mutants, read off this module's source, edited and exec'd in memory

| mutant | leaking offsets (walk) |
|---|---|
| write-back-dated (output one bar early) | 14 / 43 |
| window-one-ahead | 14 / 43 |
| chunk-wide-mean (one mean across the chunk) | 40 / 43 |
| chunk-wide-total (one total power across the chunk) | 43 / 43 |

The one-bar mutants are caught on only 14 of 43 single splices because the
output is a 65-level grid value: back-dating by one bar moves the visible
prefix only where bar `j−1`'s grid value changes. The test module tries up
to 8 independent splices per offset and requires ≥ 10 offsets caught; it
also runs `window-ten-ahead`, `returns-rolled`, and the bad-return mask
mutant (dead on a clean frame, caught on 12 of 12 NaN-injected offsets,
the first moved bar always `j − 1`).

## C. Gate C — reachability

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 19 | 1.1290 .. 2.0126 | 1.5708 |
| tick-rounded | 1,400 / 1,500 | 24 | 1.0308 .. 2.1598 | 1.5708 |
| penny | 1,400 / 1,500 | 19 | 1.0308 .. 1.9144 | 1.4726 |
| ar1 (φ 0.6) | 1,400 / 1,500 | 15 | 0.2454 .. 0.9327 | 0.4909 |
| cosine (period 20) | 1,400 / 1,500 | 1 | 0.2945 | 0.2945 |
| student-t | 1,400 / 1,500 | 18 | 1.1781 .. 2.0126 | 1.7181 |

The cosine frame is constant by construction: 0.2945 = π·6/64, the grid bin
nearest its own 2π/20.

### C1. The issue's own worry: tick-rounded data

`penny` (a 2-lira series on a 1-kuruş tick) has **21.68%** exactly-zero
returns and still fires on every eligible bar with 19 distinct values. Its
median (1.4726) sits one grid step below the unrounded frames' 1.5708.
Whether BIST tick rounding drives the column is a Gate C question for real
data and goes with Gate E (top comparator a price level or `Volume` would
point at it); synthetic frames cannot answer it.

## D. Gate D — scale-free

### D1. Exact binary rescales

×8 and ×64 price: **bit-identical on all 12 cells** (six frames × two
factors). The test module adds ×2⁻⁴⁰ and ×2⁴⁰ (24 cells, all bit-identical).

### D2. Inexact rescales

| rescale | frames | bars moved | NaN-mask diffs |
|---|---|---|---|
| price ×10 | all six | 0 | 0 |
| price ×3.7 | all six | 0 | 0 |
| returns ×10 | five of six | 0 | 0 |
| returns ×3.7 | all six | 0 | 0 |

The sixth returns ×10 cell (`student-t`) shows 1,183 NaN-mask diffs. That
comes from the test series, not the indicator: the frame clips returns to
±0.5, one return is ≤ −0.1, so `1 + 10 r ≤ 0` and the rescaled TEST price
goes non-positive from there on (measured: 1 such return). Every later
bar is then correctly bad data. The test module rescales `walk` (×10, ×3.7,
×0.1: 0 moved, 0 NaN-mask diffs).

### D3. `0 < fires < n`, and not constant

1,400 of 1,500 on every stochastic frame, 15–24 distinct values each.

## E. Gate E — attribution

**Owed.** Not runnable here (private engine, BIST cache); no row in
`docs/gate_e_ledger.csv`. `tests/test_gate_e_ledger.py` reports it as the
"Gate E owed" skip under `GATE_E_PENDING_OK=1`.

### E1. Advance warning on synthetic frames — NOT Gate E

`docs/C22PeriodicityMeasured.md` §E4 sets an owed rule: when #138 is ported,
measure it against `C22PERIODICITY_100`. On the six synthetic frames only
(section X, per-frame Spearman ρ; cosine is `nan`, the column is constant
there):

| comparator | walk | tick-rounded | penny | ar1 | student-t |
|---|---|---|---|---|---|
| `C22PERIODICITY_100` | −0.154 | +0.045 | +0.004 | −0.337 | +0.209 |
| `TS_AC1_60` | −0.619 | −0.641 | −0.570 | −0.704 | −0.663 |
| `DIFF2ACF1_100` | −0.250 | −0.767 | −0.465 | −0.255 | −0.831 |
| `C22ACFFIRSTMIN_100` | −0.353 | −0.727 | −0.433 | −0.492 | −0.741 |
| `FIRSTZEROAC_100` | +0.351 | +0.434 | +0.278 | −0.589 | +0.525 |
| `TFSPECENT_64` | −0.034 | −0.120 | +0.132 | +0.588 | −0.156 |
| `TFAUTOCORR1E_60` | +0.045 | +0.082 | +0.059 | +0.244 | +0.015 |

The largest single cell is −0.831 (`DIFF2ACF1_100`, student-t), under the
0.90 strike line but inside the 0.80–0.90 DISCLOSE_GAP band if it held on
BIST. The §E4 rule itself, and the real bands, are for the 89-frame Gate E
run.

## F. Gate F — suites

Targeted run (`tests/test_c22_median_freq.py tests/test_altport2_ports.py
tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py
tests/test_readme_counts.py tests/test_wiring_accessors.py`): **1,385
passed, 8 skipped**, one skip being "Gate E owed: no Gate E ledger row for
['c22_median_freq']". The full suite is run by issue-solver.

### F1. Wiring

All five touch points are asserted by `test_the_five_wiring_touch_points`
and `test_the_accessor_forwards_its_parameters`. Package-wide counts read
back from the live package: `Category` 368 (statistics 66), `df.ta`
accessors 376; `README.md`, `CATEGORY_TOTAL`,
`docs/IndicatorDictionary.md` (regenerated) and the tagged-column line of
`docs/MLCompanionContract.md` (712 → 713, `SF` 347 → 348; the diff of the
regenerated dictionary adds one `SF` column and moves no other tag) updated
to match.

## G. The floor, and what it buys

| input | fires | max window sd |
|---|---|---|
| geometric ladder, step 0.01 | 0 | 1.39e-16 |
| ladder, step 0.001 | 0 | 1.44e-16 |
| ladder, step −0.005 | 0 | 1.26e-16 |
| 400 identical closes | 0 | — |

A geometric ladder's returns are constant up to rounding; without the
9.09e-13 floor (`no-floor` mutant) the ladder fires on rounding noise.
