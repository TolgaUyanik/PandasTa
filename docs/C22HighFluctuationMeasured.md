# `c22_high_fluctuation` — measured

PandasTa issue **#144** (C22-HIGH-FLUCTUATION), ported 2026-11-23 on branch
`issue-144-c22-high-fluctuation`.

| | |
|---|---|
| module | `pandas_ta/statistics/c22_high_fluctuation.py` |
| column | `C22HIGHFLUCT_100` (`SF`, share on `[0, 1]`) |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), `MD_pNN_pnn40` -- the `pnn40` member of the `MD_pNNx` family (an HRV pNNx generalisation: z-score the series, then the share of successive differences exceeding a fixed absolute threshold, here 0.04); reference code pycatch22 1.0.2 and hctsa are **GPL-3.0**, so this was ported from the published definition, never from that code |
| tests | `tests/test_c22_high_fluctuation.py` (87 tests) |
| harness | `docs/measure_c22_high_fluctuation.py` (sections gate_a, min_length, gate_b, noise_floor, gate_c_d, cost) |
| Gate A | 3 hand-derived windows match by construction; 1,400/1,400 fired bars on three frames (walk, tick-rounded, ar1) bit-equal to an independent spelling (Python stdlib `statistics.mean`/`statistics.stdev`, a different mean/variance algorithm than numpy's) sharing no array machinery with the module — §A |
| Gate B | real module leaks 0/34 offsets (8 random splices each) on three frames; four mutants (back-dated write, forward-shifted return, forward-shifted diff, forward-shifted standard deviation) are each caught on a strictly positive, pinned count of those 34 (6 to 15) — §B |
| Gate C | fires on every bar with a full window (1,400/1,500) on four frames; 7-27 distinct values per frame; the tick-rounded `penny` frame (>10% exactly-zero returns) fires everywhere with the MOST distinct values (27) of any frame, and the lowest minimum (0.697) — §C |
| Gate D | bit-identical (`==`, not a tolerance) under ×8/×64 price rescale, ×10/×3.7/×0.1 price rescale (not a power of two), ×10/×3.7/×0.1/×2.5 affine rescale of the RETURNS themselves (with and without a +0.01 shift), AND under a ×-1 (sign-flipping) rescale of the returns -- the share depends only on `\|diff(Z)\|`, so a negative rescale (which this fork's `c22_stretch_decreasing` is emphatically NOT invariant under) leaves it unchanged; `0 < fires < n` on all four frames — §D |
| Gate E | pending, run by issue-solver after this session |
| Gate F | targeted PandasTa run green except the expected Gate-E-owed failure: see §F below; full suites run by issue-solver in clean worktrees |

Every number below was produced by
`python docs/measure_c22_high_fluctuation.py` or by
`python -m pytest tests/test_c22_high_fluctuation.py`, on this machine
(numpy 1.26.4, pandas 2.3.3, Python 3.11).

---

## 0. What the column is

```
r[t]             = close[t] / close[t-1] - 1
X                = r[T-99 .. T]                       (the 100-return window)
Z                = (X - mean(X)) / sd(X, ddof=1)
d[i]             = Z[i] - Z[i-1],  i = 2 .. 100        (99 diffs)
C22HIGHFLUCT_100 = count(|d[i]| > 0.04) / 99
```

Unlike this fork's other return-based catch22 ports, the z-score is **not**
inert here: `c22_median_freq` divides the z-score's divisor out of a power
ratio, and `c22_stretch_decreasing` reads only each diff's SIGN (which a
positive affine map cannot flip); this feature compares the z-scored diff's
MAGNITUDE against the absolute constant 0.04, so the divisor convention
(`ZSCORE_DDOF = 1`, MATLAB's default) genuinely sets where that boundary
falls.

## 1. Attribution, and what it is NOT evidence of

catch22 is a 22-feature subset of hctsa selected for time-series
CLASSIFICATION performance across 93 problems (Lubba et al. 2019). That is
not return prediction, and nothing here tests it on BIST: its presence in
this fork is existence, not evidence.

## min_length. Why `MIN_LENGTH = 3`, not 2

Measured by `python docs/measure_c22_high_fluctuation.py min_length`:

| window size | random draws | distinct shares reached |
|---|---|---|
| 2 returns | 3,000 | `{1.0}` -- forced constant |
| 3 returns | 30,000 | `{0.5, 1.0}` -- genuinely data-dependent |

Z-scoring 2 values (ddof=1) always places them at exactly `-1/sqrt(2)` and
`+1/sqrt(2)`: the one diff is a forced `sqrt(2) ~= 1.4142`, always above
0.04, so every non-degenerate 2-return window reads a forced `1.0`
regardless of the data. 3 is the smallest window whose answer is genuinely
data-dependent, so it is the floor (`MIN_LENGTH`) rather than 2.

## A. Gate A — correctness

### A1. Three hand-derived windows

| returns | why | expected | got |
|---|---|---|---|
| `[0, 0, 0]` | constant: sd is 0, no z-score to take | NaN | NaN |
| `[0, 1, 2]` | strictly monotone: Z = [-1, 0, 1], both diffs exactly 1.0 | 1.0 | 1.0 |
| `[0, 1, 1.001]` | one big diff, one diff below threshold | 0.5 | 0.5 |

All three OK (`docs/measure_c22_high_fluctuation.py` §Gate A1).

### A2. Against an independent stdlib-`statistics` oracle, window by window

The oracle (`_oracle_share`/`_oracle_series`) shares no array machinery with
the module: `statistics.mean`/`statistics.stdev` (a different algorithm
than numpy's `.mean()`/`.std()`) in a plain Python loop over explicit
slices, mirroring the module's own `r[0] = NaN` sentinel for the undefined
first return (not Python's negative-index wraparound -- the `ssf` bug class
`CLAUDE.md` warns about).

| frame | windows | bit-equal | windows reaching the floor |
|---|---|---|---|
| walk | 1,400 | 1,400 | 0 |
| tick-rounded | 1,400 | 1,400 | 0 |
| ar1(+0.6) | 1,400 | 1,400 | 0 |

The floor never fires on these frames, so the agreement is evidence rather
than a shared branch.

## B. Gate B — causality

34 offsets, 8 independent random splices each, on three frames (`walk`,
`tick-rounded`, `ar1(+0.6)`):

| | walk | tick-rounded | ar1(+0.6) |
|---|---|---|---|
| real module | 0/34 | 0/34 | 0/34 |
| `write-back-dated` | 14/34 | 8/34 | 15/34 |
| `forward-return` | 14/34 | 8/34 | 15/34 |
| `forward-diff` | 14/34 | 8/34 | 15/34 |
| `forward-sd` | 8/34 | 6/34 | 9/34 |

The real module is clean on every frame; every mutant (each
`importlib`-read off this module's source and `exec`'d in memory, and
confirmed `live` -- it changes the output) is caught on a strictly
positive, pinned share of the 34 offsets. Unlike the tie-heavy run-length
statistics this fork has also ported (`c22_stretch_decreasing`'s own Gate B
needed a hand-engineered window because its sweep caught mutants on only
1-2/34), this continuous share statistic is caught at a materially higher
rate (6 to 15 of 34) by the generic sweep alone, so no engineered window
was needed here.

## The noise floor

An exactly geometric path (three ladders: +1%/bar, -0.5%/bar, a constant
×1.5/bar) has mathematically CONSTANT returns -- no z-score to take -- and
float64 gives each a window standard deviation of 1.2e-16 to 2.3e-16, all
below the 9.095e-13 floor, so every one of the 200 post-warm-up bars on
each ladder is NaN (0/300 fire). This is the same floor this fork's other
catch22-on-returns ports use.

## C. Gate C — reachability

| frame | fires | distinct | min | max |
|---|---|---|---|---|
| walk | 1,400/1,500 | 7 | 0.9394 | 1.0000 |
| tick-rounded | 1,400/1,500 | 7 | 0.9394 | 1.0000 |
| ar1(+0.6) | 1,400/1,500 | 8 | 0.9293 | 1.0000 |
| penny (>10% zero returns) | 1,400/1,500 | 27 | 0.6970 | 0.9596 |

On the continuous frames the column sits close to its ceiling: with
length-100 windows and the fork's synthetic daily-return volatilities
(1.0-1.5% a bar), most successive z-scored diffs clear 0.04 sd, so the
share is usually near 1.0 and distinguishes mainly through its lower tail.
The issue's own worry (BIST tick rounding) is directly addressed by
`penny`: many exactly-repeated (zero) returns shrink enough diffs below
0.04 that the column both fires everywhere AND is the most varied of the
four frames (27 distinct values, the widest range).

## D. Gate D — scale-free

Bit-identical (`==`), not a tolerance, on every cell tested:

| rescale | frames | result |
|---|---|---|
| price ×8, ×64 | walk, tick-rounded, ar1, penny | 1,400/1,400 bit-equal, all 8 cells |
| price ×10, ×3.7, ×0.1 (not a power of two) | walk, tick-rounded | 1,400/1,400 bit-equal, all 6 cells |
| returns ×10, ×3.7, ×0.1, ×2.5, with +0 and +0.01 shift | walk | 1,400/1,400 bit-equal, all 8 cells |
| returns ×-1 (negation) | walk | 1,400/1,400 bit-equal |

The returns-rescale result holds mathematically in real arithmetic for ANY
affine map `a*r + b` (the z-score cancels it exactly: `Z' = Z` for `a > 0`,
`Z' = -Z` for `a < 0`), but is NOT a float64 proof like the price-ratio
argument (mean/std/division each round independently on the rescaled
array) -- it is measured bit-identical here because the output is a COUNT
over a fixed grid (`k / 99`) that only moves if a diff crosses the 0.04
boundary, which none did on this frame at these factors. The negative-sign
result is the asymmetry this column has that `c22_stretch_decreasing` does
NOT: that column flips meaning under negation (falls become rises); this
one is unchanged, because it reads only `|diff(Z)|`. `0 < fires < n` holds
on every stochastic frame (1,400 of 1,500).

## E. Gate E — attribution

Pending: run by issue-solver after this session
(`gate_e_overlap.py run --module pandas_ta.statistics.c22_high_fluctuation`).
A later session records the `docs/gate_e_ledger.csv` row and fills this
section with the measured numbers.

## F. Gate F — suites

```
python -m pytest -q tests/test_c22_high_fluctuation.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

1,481 passed, 7 skipped, 1 failed
(`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
-- expected: it fails for `c22_high_fluctuation` until Gate E is run and the
ledger row is recorded, per `CLAUDE.md`'s "Owed, not failed" rule; the
failure names exactly `['c22_high_fluctuation']` as the only missing row).

Re-run under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
(this machine's own AVX512F/AVX512_SKX/AVX2/FMA3, confirmed present via
`numpy.core._multiarray_umath.__cpu_features__` before disabling) via
`python docs/measure_c22_high_fluctuation_cpu.py disable pytest`: all 87
tests in `tests/test_c22_high_fluctuation.py` pass unchanged. Unlike a pure
sign/comparison statistic, this module's mean/std/division genuinely can
move by a CPU kernel's last-bit rounding, but the shipped value is a count
over a fixed 1/99 grid, and no test here pins a Spearman value or a
bit-equal count near 1e-6 -- each Gate A/D number is either an exact
hand-derived integer, a bit-identical rescale (measured, not derived from
a float64 proof), or `== 0`/`> 0` leak counts, all of which held unchanged
under the disabled kernels.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Cost

At 400,000 bars: 804 ms wall, 1006.2 MB traced peak (a `(rows, length)`
windows view plus the `(rows, length)` z-score and `(rows, length - 1)`
diff matrices).
