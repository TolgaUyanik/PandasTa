# `c22_low_freq_power` — measured

PandasTa issue **#141** (C22-LOW-FREQ-POWER), ported 2026-11-22 on branch
`issue-141-c22-low-freq-power`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_low_freq_power.py` |
| column | `C22LOWFREQPOWER_100` (`SF`, power share in [0, 1]) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `SP_Summaries_fft_area_5_1`; pycatch22 1.0.2 and hctsa are **GPL-3.0**, and pycatch22 is not even installed in this environment (not a declared dependency of this fork), so this was ported from the published definition and checked against an independent direct-DFT oracle written for this port, never against the reference's output |
| tests | `tests/test_c22_low_freq_power.py` (113 tests) |
| harness | `docs/measure_c22_low_freq_power.py` (sections A, B, C, D, G, X) |
| Gate A | 1,200 of 1,200 sampled windows (every 7th window of six frames) agree with a direct-DFT oracle to < 1e-12 (worst observed gap 5.6e-16, float noise); a cosine at the cutoff bin (12 of 128) returns exactly 1.0, one bin above (13) returns ~1.3e-30 — §A |
| Gate B | causal; 0 of 43 offsets leak on six frames; all four mutants caught on 43 of 43 offsets each — §B |
| Gate C | fires on every bar with a full window (1,400 / 1,500) on all six frames; 1,400 distinct values on every stochastic frame; `penny` (21.68% zero returns) fires everywhere — §C |
| Gate D | ×8/×64 bit-identical on 12/12 cells; ×10/×3.7 price and ×10/×3.7 return rescales move 0 bars with matching NaN masks (one cell aside, a test-series artifact: §D2); `0 < fires < n` — §D |
| Gate E | max \|ρ\| 0.2764 vs `mad_pct` (manifest, n = 389,949); per-frame max median 0.2752, 89 frames, 0% ≥ 0.90 → **SHIP** |
| Gate F | targeted PandasTa run green (1,500 passed, 7 skipped) after the Gate E ledger row; full suites run by issue-solver |

Every number below was produced by `python docs/measure_c22_low_freq_power.py`
(wall 17.6 s, peak traced memory 4.6 MB) or by `python -m pytest
tests/test_c22_low_freq_power.py`, on this machine (numpy 1.26.4, pandas
2.3.3, scipy 1.13.0, Python 3.11.18). The targeted suite was also re-run
with `NPY_DISABLE_CPU_FEATURES=AVX512F AVX512_SKX AVX2 FMA3` (this
machine's detected set) via `docs/measure_c22_low_freq_power_cpu.py`: same
result, 1,491 passed / 7 skipped.

---

## 0. What the column is

```
r[t]   = close[t] / close[t-1] - 1
X      = r[T-99 .. T]                       (100 returns, closes T-100 .. T)
Z      = (X - mean(X)) / sd(X, ddof=1)
S_k    = |rfft(Z, 128)_k|^2,  k = 0 .. 64   (NFFT = 2^nextpow2(100) = 128)
j      = floor((128/2) / 5) = 12            (the band-1 cutoff bin)
C22LOWFREQPOWER_100 = (S_0 + .. + S_12) / sum(S)
```

Band 1 is the lowest fifth of the continuous frequency axis `[0, pi]`:
`[0, pi/5)`. High: the window's power sits at low frequencies (trending,
positively autocorrelated returns). Low: most power sits at higher
frequencies (mean reversion, noise).

Two choices the definition leaves open, made explicitly and stated in the
module docstring: the 5 bands are cut by EQUAL FREQUENCY WIDTH, not equal
bin count; and the spectrum is POWER `|Y|^2`. The first choice turns out to
be moot, derived (not merely checked) in the docstring: because `NBANDS` =
5 never divides the power-of-two `NFFT/2`, the equal-width cutoff bin and
the standard equal-bin-count cutoff bin are PROVABLY IDENTICAL at every
length this module can produce, not merely at the default. Neither choice
was checked against hctsa's source, which is GPL-3.0 and was not read, nor
against pycatch22's output, which is GPL-3.0 and not installed here.

The z-score's division by `sd` is inert in exact arithmetic: it scales
every bin by `1/sd^2`, which a power RATIO cannot see. Its mean removal is
not: with zero-padding (100 returns in 128 slots) a window's mean would
otherwise leak into the low bins, including the DC bin itself.

## 1. Attribution, and what it is NOT evidence of

catch22 was selected for time-series CLASSIFICATION across 93 problems; this
is one of its own 22 canonical features. Nothing here tests it as a return
predictor on BIST: existence, not evidence. The screen prototype
measurements in issue #141 (Gate E prototype 0.2757 vs `mad_pct`) are of the
prototype, not this port.

## A. Gate A — correctness

### A1. Against a direct-DFT oracle, every 7th window of six frames

The oracle (`direct_dft_low_freq_power`, in both the harness and the test
module) shares no code path with the module: explicit `math.cos`/`math.sin`
sums with the angle reduced modulo NFFT, every sum by `math.fsum`.

| frame | windows | agree (< 1e-12) | disagree |
|---|---|---|---|
| walk | 200 | 200 | 0 |
| tick-rounded | 200 | 200 | 0 |
| penny | 200 | 200 | 0 |
| ar1 | 200 | 200 | 0 |
| cosine | 200 | 200 | 0 |
| student-t | 200 | 200 | 0 |
| **total** | **1,200** | **1,200** | **0** |

Worst observed |shipped − oracle| on any sampled window: **5.551e-16**
(machine epsilon), not a tolerance being stretched.

Unlike `c22_median_freq`'s 65-level grid, this column's band-1 cutoff BIN is
fixed by `nfft` alone (`floor((nfft/2) / 5)`), never by the data, so there
is no boundary tie to be near in the first place -- `nfft/2` is always a
power of two and 5 never divides one.

### A2. Designed windows with a known answer

| window | shipped |
|---|---|
| pure cosine at bin 1, length 128 | 1.0 |
| pure cosine at bin 12, length 128 (the cutoff bin itself) | 1.0 |
| pure cosine at bin 13, length 128 (one above cutoff) | 1.3411846941776792e-30 |
| pure cosine at bin 20, length 128 | 1.0811381616355606e-30 |
| pure cosine at bin 63, length 128 (Nyquist) | 2.6364492173183147e-29 |
| +1/−1 alternation, 100 samples (all power at Nyquist) | 0.0006039488147608784 |

A single-bin cosine at exactly the cutoff bin (12) has its WHOLE power in
band 1 (shipped 1.0); one bin above (13) is excluded and reads ≈0. That is
the sharpest possible confirmation of where the boundary actually falls.

### A3. Direction on AR(1) returns (seed 3, 1,400 bars each)

| φ | −0.6 | −0.3 | 0.0 | 0.3 | 0.6 |
|---|---|---|---|---|---|
| median | 0.0500 | 0.1046 | 0.1917 | 0.3353 | 0.5648 |
| mean | 0.0531 | 0.1084 | 0.1930 | 0.3305 | 0.5548 |

Monotone RISING with φ -- more positive return autocorrelation puts more
power at low frequency. This is the opposite direction from this fork's
`c22_median_freq`, which FALLS with φ (a higher median frequency means less
low-frequency power, so the two columns move opposite ways on the same
data by construction).

## B. Gate B — causality

### B1. The real module

Future replaced by an independent random path from offset `j` on (43
offsets, 130..1390 step 30): **0 / 43 leaking offsets** on each of walk,
tick-rounded, penny, ar1, cosine, student-t.

### B2. Mutants, read off this module's source, edited and exec'd in memory

| mutant | leaking offsets (walk) |
|---|---|
| write-back-dated (output one bar early) | 43 / 43 |
| window-one-ahead | 43 / 43 |
| chunk-wide-mean (one mean across the chunk) | 43 / 43 |
| chunk-wide-total (one total power across the chunk) | 43 / 43 |

Every mutant is caught at every probed offset: unlike `c22_median_freq`'s
65-level grid output, this column is a continuous power ratio, so a
one-bar look-ahead is visible almost everywhere rather than only where a
grid value happens to change. The test module runs the same four plus
`window-ten-ahead`, `returns-rolled`, and a bad-return mask mutant (dead on
a clean frame, caught on all 12 of 12 NaN-injected offsets, the first moved
bar always `j − 1`).

## C. Gate C — reachability

| frame | fired | distinct | range | median |
|---|---|---|---|---|
| walk | 1,400 / 1,500 | 1,400 | 0.0657 .. 0.3587 | 0.1844 |
| tick-rounded | 1,400 / 1,500 | 1,400 | 0.0515 .. 0.3353 | 0.1807 |
| penny | 1,400 / 1,500 | 1,400 | 0.1219 .. 0.3689 | 0.2158 |
| ar1 (φ 0.6) | 1,400 / 1,500 | 1,400 | 0.3495 .. 0.7093 | 0.5779 |
| cosine (period 20) | 1,400 / 1,500 | 98 | 0.9778 .. 0.9976 | 0.9877 |
| student-t | 1,400 / 1,500 | 1,400 | 0.0838 .. 0.3168 | 0.1881 |

A continuous power ratio: every stochastic frame reads essentially as many
distinct values as bars fired. The cosine frame is near-constant (98
distinct of 1,400) because a period-20 cycle's fundamental sits well inside
band 1 at the default length -- almost all of its power reads as
low-frequency.

### C1. The issue's own worry: tick-rounded data

`penny` (a 2-lira series on a 1-kuruş tick) has **21.68%** exactly-zero
returns and still fires on every eligible bar with the full 1,400 distinct
values, range 0.1219 .. 0.3689 -- similar in shape to the unrounded `walk`
frame (0.0657 .. 0.3587). Whether BIST tick rounding drives the column is a
Gate C question for real data and goes with Gate E (top comparator a price
level or `Volume` would point at it); synthetic frames cannot answer it.

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
bar is then correctly bad data -- the same artifact `c22_median_freq`'s
receipt documents. The test module rescales `walk` instead (×10, ×3.7, ×0.1:
0 moved, 0 NaN-mask diffs).

### D3. `0 < fires < n`, and not constant

1,400 of 1,500 on every stochastic frame, 1,400 distinct values each.

## E. Gate E — attribution

Run `is141-c22_low_freq_power-0d6288de`, `gate_e_overlap.py run --module
pandas_ta.statistics.c22_low_freq_power`, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 = 687 comparators, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS,
SASA.IS).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `C22LOWFREQPOWER_100` | 0.2764 | `mad_pct` | 389,949 | 0.2752 | **SHIP** |

0 of 89 per-frame medians reach 0.90. Pooled and manifest-only max agree
(`mad_pct` leads both); `compute_all`-only max is 0.2674 vs `BB_BWidth`. Well
under the 0.76 ship line and close to the screen prototype's own 0.2757 vs
the same comparator (issue #141) -- the port did not change what the column
is close to. Ledger row recorded 2026-11-22
(`python docs/gate_e_ledger.py record`).

## F. Gate F — suites

Targeted run (`tests/test_c22_low_freq_power.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py
tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`),
re-run in the receipt session after the Gate E ledger row was recorded:
**1,500 passed, 7 skipped**, no failures --
`test_every_indicator_that_needs_a_row_has_one` now passes with the row in
place. Prior to the ledger row the same run was 1,491 passed, 7 skipped,
with that test failing as expected (no row yet). Re-run with
`NPY_DISABLE_CPU_FEATURES=AVX512F AVX512_SKX AVX2 FMA3`
(`docs/measure_c22_low_freq_power_cpu.py`): same, **1,500 passed, 7
skipped**.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

### F1. Wiring

All five touch points are asserted by `test_the_five_wiring_touch_points`
and `test_the_accessor_forwards_its_parameters`. Package-wide counts read
back from the live package: `Category` 375 (statistics 69), `README.md`,
`CATEGORY_TOTAL`, `docs/IndicatorDictionary.md` (regenerated) and the
tagged-column line of `docs/MLCompanionContract.md` (719 → 720, `SF` 353 →
354; the diff of the regenerated dictionary adds one `SF` column and moves
no other tag) updated to match.

## G. The floor, and what it buys

| input | fires | max window sd |
|---|---|---|
| geometric ladder, step 0.01 | 0 | 1.46e-16 |
| ladder, step 0.001 | 0 | 1.51e-16 |
| ladder, step −0.005 | 0 | 1.20e-16 |
| 400 identical closes | 0 | — |

A geometric ladder's returns are constant up to rounding; without the
9.09e-13 floor (`no-floor` mutant) the ladder fires on rounding noise.

## X. Advance warning (NOT Gate E) — vs this fork's `c22_median_freq`

Per-frame Spearman ρ on the six synthetic frames only (cosine is `nan`,
`c22_median_freq` is constant there):

| frame | walk | tick-rounded | penny | ar1 | student-t |
|---|---|---|---|---|---|
| ρ vs `C22MEDFREQ_100` | −0.614 | −0.643 | −0.532 | −0.839 | −0.299 |

Strongly negative, as expected for two spectral-shape readouts of the same
window measured from opposite ends of the frequency axis -- not a
restatement check, and not Gate E. The real redundancy question is the
89-frame BIST attribution run.
