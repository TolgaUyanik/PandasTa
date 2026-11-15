# TS-ENERGY-LAST-20 — `ts_energy_last_20`, measured

PandasTa issue **#102** (parent #31 ALPHASETS, screen of 2026-10-24).
Module `pandas_ta/statistics/ts_energy_last_20.py`, column
**`TS_ENERGY_LAST_20_4`**. Tests `tests/test_ts_energy_last_20.py` (226).
Every number in §A1–§A6, §B, §C, §D, §G's default-run columns, §O's
synthetic tables, §S and §Z's traced peak is printed by
`python docs/measure_ts_energy_last_20.py` on this worktree
(**pandas 2.3.3, numpy 1.26.4** — which that script prints as its first
line, so this parenthesis is a quote and not a guess), section by
section. Those headings take
their letters from the script, with one join: the script's section **M**
(the mutant table) is printed here under §B, since it is Gate B's
evidence. §E and §F are headings of this file and not of the script.
What does NOT come from that command, each marked again where it
appears:

* **§G3's distinct count in brackets and §G4's reduced-CPU column**,
  which are `python docs/measure_ts_energy_last_20_cpu.py G`'s — the same
  sections with `AVX512F AVX512_SKX AVX2 FMA3` disabled;
* **§Z's milliseconds**, which that command does print but which are NOT
  a claim: they are this machine's and this run's, and four runs of that
  one section on this one worktree came out up to 40% apart and one of
  them out of ORDER. §Z gives them as two columns of a best-of-5 and
  states what survives a re-run instead — the flat traced peak, the
  monotone ordering of the minima and their ratio, each of which
  `section_Z` prints for itself;
* **§E and §E1**, which are the launcher's Gate E run on this module
  (`is102-ts_energy_last_20-3468c96b`, 2026-11-14), read out of that run's
  own `overlap_max.csv`, `top25.csv`, `perframe.csv`, `degenerate.csv` and
  `meta.json`;
* **§E0 and §O2's screen figures**, which are the 2026-10-24 screen's,
  measured on the PROTOTYPE and quoted from the issue;
* **§F**, which is pytest's own output.

    r            = close / close.shift(1) - 1
    x            = the window's `length` simple returns
    tail         = length // 4 = 5 at the default
    TS_ENERGY    = sum(x[-tail:] ** 2) / sum(x ** 2)

**Source.** tsfresh `feature_calculators.energy_ratio_by_chunks` (MIT),
as issue #102 states the formula: `energy_ratio_by_chunks(num_segments=4,
segment_focus=3) on 20 returns`. The published function is

    full = np.sum(x ** 2)
    NaN if full == 0 else
        np.sum(np.array_split(x, num_segments)[segment_focus] ** 2.0) / full

The screen prototype is `docs/issues/screen/ind_screen.py` candidate
`ts_energy_last_20`, `sdiv(tsum(ret(c) ** 2, 5), tsum(ret(c) ** 2, 20))`.
⚠ **tsfresh is not installed in this worktree and web access is
unavailable.** It is an ATTRIBUTION, not an oracle:
`tests/test_ts_energy_last_20.py::test_the_source_library_is_not_installed_here`
records that. What Gate A checks is the published definition quoted above
plus the issue's own line. The 20, the 4 and the 3 are the issue's
parameters.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS.** BIT-equal to an independent retyping of the source's own spelling (`np.array_split` + `np.sum`) on 1,480 of 1,480 bars of each of ten frames with identical NaN masks, and at `length` 4, 5, 7, 21, 40 and 250 — the script's §A sweep, which ends at 40 where §C's and §D's ends at 60; both sets are the sweeps those sections actually run, not a typo. Within 5 ulps of an exact rational oracle, and closer to it than the left-to-right spelling on 10 of 10 frames. |
| B Causality | **PASS.** 0 of 36 offsets leak on four frames and at `length` 4, 7, 60 and 250. Six mutants: five live and caught 36 of 36 on every frame, the sixth invisible to the blind sweep (0 of 36) and caught 12 of 12 on a designed frame, moving exactly bar J−1 at all twelve. |
| C Reachability | **PASS.** Fires 1,480 of 1,500 on each of ten synthetic frames; 1,480 distinct values on nine of them and a constant 0.25 (plus 1.2e-14 of rounding) on the two-point one. On the Gate E universe `0 < 397,069 < 398,849`, of which 396,809 are non-zero (§E1). |
| D Scale-free | **PASS.** x8/x64 bit-identical on 1,480/1,480 of each of ten frames, at `length` 4, 5, 7, 21, 60 and 250 (§C's and §D's sweep) and at price 1e-6, 1e+6 and 1e+100. x10 / x3.7 / x0.1 / x1.0000001: masks identical, max relative difference 4.6e-13. `0 < fires < n` on every frame. |
| E Attribution | **SHIP.** Run `is102-ts_energy_last_20-3468c96b`, 2026-11-14: pooled \|ρ\| **0.7020** vs `natr_Chg_5d` (manifest, n = 397,069), per-frame max median **0.7036** over 89 frames, 0 of 89 frames ≥ 0.90 and 0 ≥ 0.80 on any of the top five. The same comparator and the same two figures §E0's screen printed for the PROTOTYPE. |
| F Suites | This repo: 226 for the module, 226 again with AVX-512/AVX2/FMA3 disabled; full suite in §F. The Backtesting suite is the launcher's. |

---

## E0 — what the screen measured, and on what

Quoted from issue #102; measured 2026-10-24 on the **prototype**, not on
this module.

| what | figure |
|---|---|
| Gate E max \|ρ\| | **0.7020** vs `natr_Chg_5d` (manifest), n = 397,069 |
| top-5 per-frame max median | 0.7036 → **SHIP** |
| next comparators | `ATR_Ratio_5_20_Pctl` 0.5530, `ATR_Ratio_5_20` 0.5460 |
| run | `screen_20261024`, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal |
| fork overlap (stage 2, 12 frames, not Gate E) | max \|ρ\| 0.5795 vs `bbands:BBB_5_2.0`, per-frame max median 0.5866 |
| pre-flight (6 frames, `sanity.csv`) | prefix-causal, unchanged under price ×8 and volume ×8 |

⚠ The fork-overlap line cannot bound this port's two nearest in-fork
neighbours: it was taken **six days before** `tf_centroid_20` entered
`Category` (issue #116, merged 2026-10-30) and **three weeks before**
`ts_imq_20` (issue #99, merged 2026-11-14). §O measures both pairs on
synthetic frames, which is the only measurement of them that exists.

---

## A1 — BIT-equality against the source's own spelling, retyped

`_source_windowed` in the measurement script walks the frame one window
at a time, lets `np.array_split(w, 4)[3]` pick the chunk and `np.sum` do
both sums, and applies the source's `full == 0 → NaN` rule. It shares no
code with the module.

| frame | masks | shared | bit-equal | max \|diff\| |
|---|---|---|---|---|
| walk | True | 1480 | **1480** | 0.0 |
| tick-rounded | True | 1480 | **1480** | 0.0 |
| ar1+ | True | 1480 | **1480** | 0.0 |
| ar1- | True | 1480 | **1480** | 0.0 |
| heavy-tailed | True | 1480 | **1480** | 0.0 |
| right-skewed | True | 1480 | **1480** | 0.0 |
| left-skewed | True | 1480 | **1480** | 0.0 |
| two-point | True | 1480 | **1480** | 0.0 |
| trending | True | 1480 | **1480** | 0.0 |
| clustered | True | 1480 | **1480** | 0.0 |

At other lengths on a walk, all bit-equal with identical masks: `length`
4 → 1,496 of 1,496; 5 → 1,495; 7 → 1,493; 21 → 1,479; 40 → 1,460;
250 → 1,250.

**Why it is bit-equality and not a tolerance.** `sliding_window_view`
gives each row a stride of one double, so a row IS a contiguous run of
`length` doubles, and `ew.sum(axis=1)` therefore runs the same pairwise
reduction `np.sum` runs on the source's own `(length,)` array. The equality
is a property of the shape, not of the instruction set — and it survives
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (§F).
⚠ The first draft of this module accumulated the windows LEFT TO RIGHT
instead. That spelling is 3 to 4 ulps away from the source and was
replaced for that reason; §A2 and §A3 are what it costs.

---

## A2 — the left-to-right spelling, which this module does not use

| frame | shared | bit-equal | max ulp | mean ulp | Spearman |
|---|---|---|---|---|---|
| walk | 1480 | 923 | 3.00 | 0.4709 | 1.000000 |
| tick-rounded | 1480 | 880 | 4.00 | 0.5142 | 1.000000 |
| ar1+ | 1480 | 877 | 3.00 | 0.5297 | 1.000000 |
| ar1- | 1480 | 831 | 3.00 | 0.5743 | 1.000000 |
| heavy-tailed | 1480 | 862 | 4.00 | 0.5541 | 1.000000 |
| right-skewed | 1480 | 903 | 3.00 | 0.5000 | 1.000000 |
| left-skewed | 1480 | 899 | 4.00 | 0.5162 | 1.000000 |
| two-point | 1480 | 730 | 4.00 | 0.7959 | 0.999113 |
| trending | 1480 | 911 | 4.00 | 0.4986 | 1.000000 |
| clustered | 1480 | 872 | 4.00 | 0.5500 | 1.000000 |

The two spellings are rank-identical everywhere but on the two-point
frame, where the column is a constant and the correlation ranks the
rounding (§C).

---

## A3 — against an EXACT rational oracle, in ulps

Every return is a double, so a rational. `_exact` squares each one and
sums both subsets in `fractions.Fraction`, rounding exactly once at the
division.

| frame | bars | module bit-eq | module max | module mean | left-to-right bit-eq | max | mean |
|---|---|---|---|---|---|---|---|
| walk | 1480 | 645 | 3.00 | **0.662** | 572 | 4.00 | 0.784 |
| tick-rounded | 1480 | 616 | 5.00 | **0.706** | 580 | 5.00 | 0.774 |
| ar1+ | 1480 | 610 | 3.00 | **0.705** | 586 | 4.00 | 0.769 |
| ar1- | 1480 | 627 | 4.00 | **0.728** | 528 | 4.00 | 0.851 |
| heavy-tailed | 1480 | 618 | 4.00 | **0.730** | 586 | 4.00 | 0.800 |
| right-skewed | 1480 | 619 | 4.00 | **0.713** | 558 | 5.00 | 0.813 |
| left-skewed | 1480 | 600 | 4.00 | **0.726** | 565 | 5.00 | 0.787 |
| two-point | 1480 | 485 | 4.00 | **0.868** | 259 | 5.00 | 1.418 |
| trending | 1480 | 570 | 4.00 | **0.755** | 526 | 6.00 | 0.832 |
| clustered | 1480 | 641 | 4.00 | **0.694** | 581 | 5.00 | 0.829 |

The shipped spelling is the more accurate one on **10 of 10** frames.
Being bit-equal to the source (§A1) and being closest to the correctly
rounded answer are the same choice here, which is why there is nothing to
trade off.

---

## A4 — the tail, the closed forms, and the bound

**The tail is `np.array_split`'s own last chunk.** For every `length`
from 4 to 240, `len(np.array_split(range(length), 4)[3]) == length // 4`
and that chunk is exactly `range(length - length // 4, length)` — 0
exceptions on either count. numpy hands the LONGER chunks out first,
which is why the last one is the short one and why `length // 4` is the
source's arithmetic rather than a simplification of it.

**Three closed forms**, each measured at `length` 4, 8, 20 and 60:

| window | reads | exact |
|---|---|---|
| oldest `length - tail` returns exactly zero | **1.0** | yes |
| newest `tail` returns exactly zero | **0.0** | yes |
| every return the same MAGNITUDE | **`tail / length`** (0.25) | yes |

**The bound [0, 1], and why it is measured rather than proved.** `num`
and `den` are reduced over DIFFERENT subsets of the window and rounded
independently, so `num <= den` is exact arithmetic and not a float
theorem.

| universe | min | max | outside [0, 1] |
|---|---|---|---|
| the ten frames | 0.000113 | 0.997972 | **0 of 14,800** |
| `length` 4 | 2.086e-09 | 0.99388442883263628 | 0 of 1,496 |
| `length` 5 | 1.081e-09 | 0.92531607758227596 | 0 of 1,495 |
| `length` 7 | 6.875e-10 | 0.85099630649768732 | 0 of 1,493 |
| `length` 21 | 5.029e-03 | 0.69567138600790501 | 0 of 1,479 |
| `length` 40 | 2.615e-02 | 0.64957287938289832 | 0 of 1,460 |
| `length` 250 | 1.638e-01 | 0.38340728502010496 | 0 of 1,250 |
| 2,000 windows built to straddle 1.0 (a tail carrying all the energy, a body too small to change the total) | — | exactly **1.0** | 0 escaped |

---

## A5 — the readings the issue's line leaves open, priced

1. **Simple vs LOG returns.** The issue says "returns" and the module
   reads SIMPLE returns, which is the prototype's reading. Masks
   identical, **0** of 1,480 bars bit-equal, max \|diff\| 1.372e-02,
   Spearman **0.999572**.
2. **Squares vs absolute values.** Energy is the SQUARE. The same
   expression over \|r\| reads Spearman **0.963759** with values up to
   0.2589 apart — close enough to be mistaken for this column and not the
   same column.
3. **Other segment counts**, all at the last chunk, against the issue's
   4: 2 → 0.606122 (mean 0.501083), 5 → 0.870457 (0.201581),
   10 → 0.566516 (0.100687), 20 → 0.364284 (0.050323). Each one's mean is
   its tail's share of the bars. `SEGMENTS` is a module constant for this
   reason: changing it changes the column.
4. **The other three chunks of the SAME split**, i.e. `segment_focus`
   0/1/2: **-0.357832 / -0.359016 / -0.239524**. The four shares sum to
   1, so they are negatively related rather than restatements.
5. **The SIGN of the returns, which the column cannot see** — it reads
   `r * r`. A random sign flip of every return: max \|diff\| 5.440e-15,
   Spearman 1.000000. The right- and left-skewed frames, whose returns
   are exact negatives of each other: max \|diff\| 1.782e-14, Spearman
   1.000000.
   ⚠ Neither is bit-equality, and the reason is the FRAME and not the
   column: a sign-flipped frame has to be rebuilt from closes, which
   re-rounds every return. That the sign cannot reach the output is read
   in the code, not measured.
6. **The `length` the issue gives, against its neighbours**: 10 →
   0.390559, 16 → 0.823056, 40 → 0.480495, 60 → 0.181208. A 20-bar window
   is a month of trading and the issue's own parameter.

---

## A6 — the screen prototype: rank-identical, not bit-equal

| frame | masks | shared | bit-equal | max \|diff\| | max ulp | Spearman |
|---|---|---|---|---|---|---|
| walk | True | 1480 | 323 | 3.469e-16 | 127 | 1.000000 |
| tick-rounded | True | 1480 | 274 | 3.886e-16 | 128 | 1.000000 |
| ar1+ | True | 1480 | 369 | 4.025e-16 | 89 | 1.000000 |
| ar1- | True | 1480 | 350 | 3.886e-16 | 173 | 1.000000 |
| heavy-tailed | True | 1480 | 21 | 1.746e-14 | 7023 | 1.000000 |
| right-skewed | True | 1480 | 208 | 6.661e-16 | 41 | 1.000000 |
| left-skewed | True | 1480 | 174 | 5.621e-16 | 81 | 1.000000 |
| two-point | True | 1480 | 654 | 1.110e-16 | 4 | 0.998284 |
| trending | True | 1480 | 233 | 8.882e-16 | 64 | 1.000000 |
| clustered | True | 1480 | 276 | 3.386e-14 | **9170** | 1.000000 |

**Which of the two is out**, in ulps against the exact oracle of §A3:

| frame | module max | module mean | prototype max | prototype mean |
|---|---|---|---|---|
| walk | 3.00 | 0.662 | 128.00 | 2.496 |
| tick-rounded | 5.00 | 0.706 | 128.00 | 3.321 |
| ar1+ | 3.00 | 0.705 | 89.00 | 2.555 |
| ar1- | 4.00 | 0.728 | 174.00 | 2.218 |
| heavy-tailed | 4.00 | 0.730 | **7024.00** | 248.117 |
| right-skewed | 4.00 | 0.713 | 40.00 | 3.030 |
| left-skewed | 4.00 | 0.726 | 80.00 | 5.802 |
| two-point | 4.00 | 0.868 | **3.00** | **0.434** |
| trending | 4.00 | 0.755 | 65.00 | 3.956 |
| clustered | 4.00 | 0.694 | **9170.00** | 168.202 |

On nine of the ten frames it is the PROTOTYPE that is out, by 40 to 9,170
ulps, because `rolling().sum()` carries one running accumulator across
windows. ⚠ The two-point frame is the exception and is pinned as one: every
window there holds the same 20 squares, so a running accumulator has
nothing to drift against and the prototype is the closer of the two (3
ulps against 4, mean 0.434 against 0.868).

On the three frames built to break it the two agree on which bars fire:
flat 0 and 0, ladder 280 and 280 (128 bit-equal), quiet-1e-6 580 and 580
(74 bit-equal).

**Where they part company by design — the guards the screen has no need
of.** A bad close at bar 200 of a 400-bar walk:

| close at bar 200 | module fires | prototype fires |
|---|---|---|
| NaN | 359 | 359 |
| inf | 359 | 360 |
| zero | 359 | 360 |
| negative | 359 | 380 |
| subnormal 1e-310 | 359 | 360 |

Every extra bar the prototype reports is a window built on a close a
market cannot print. With a NaN close the two agree, because pandas
propagates it.

Because Gate E's statistic is a Spearman over the bars where both fire,
the screen's figures (§E0) were expected to carry over in rank, and §E
says they did: the run on this module reads 0.7020 pooled and 0.7036
per-frame max median against the prototype screen's 0.7020 and 0.7036,
against the same comparator and over the same n = 397,069.

---

## B — Gate B: the sweep and the six mutants

**The sweep on the real module.** Splice a different frame in from bar
`j` onward and check whether any bar before `j` moved. 36 offsets, from
bar 60 in steps of 40.

| frame | leaks |
|---|---|
| walk | **0 of 36** |
| tick-rounded | **0 of 36** |
| heavy-tailed | **0 of 36** |
| clustered | **0 of 36** |

And at other lengths on a walk: `length` 4 → 0 of 36 (first fired bar 4),
7 → 0 (bar 7), 60 → 0 (bar 60), 250 → 0 (bar 250).

**The mutants.** Each is the shipped module's own source, read with
`importlib`, edited in memory and `exec`'d — one write index or one read
moved, nothing else.

| mutant | what it moves | live | caught |
|---|---|---|---|
| `back_date_two` | the output Series `.shift(-2)` | yes | **36 of 36** on all four frames |
| `back_date_full` | `.shift(-(length - 1))` | yes | **36 of 36** on all four frames |
| `forward_return` | `px.shift(-1) / px` instead of `px / px.shift(1)` | yes | **36 of 36** on all four frames |
| `write_index_earlier` | `out[length - 2:-1]` instead of `out[length - 1:]` | yes | **36 of 36** on all four frames |
| `rolled_window` | `np.roll(r * r, -(length // 2))` | yes | **36 of 36** on all four frames |

**The sixth, and why prefix truncation is not a Gate B.** `forward_bound`
shifts the per-return bound's own index: bar T's return is kept or
dropped by whether bar T+1's return is in bound. That is a real
look-ahead, and the blind sweep catches it **0 of 36** times on each of
the four frames — on a frame where every return is in bound the only bar
it changes is the LAST one, which is never before an offset.

What it CAN move is derived, not searched: an out-of-bound return at J
spoils the return at J, so the shifted bound drops the return at J−1, and
the window ending at **J−1** is the only one before J that holds that
return without also holding J's. On a frame with an out-of-bound return
at each of 12 offsets (120 bars apart, which fires 1,240 of 1,500):

* the real module leaks **0 of 12**;
* the mutant is caught **12 of 12**;
* and the set of bars it moves is exactly `[J − 1]` at **all 12**
  offsets — 59, 179, 299, 419, 539, 659, 779, 899, 1019, 1139, 1259 and
  1379, printed one line per offset by the script and asserted one
  offset at a time by
  `test_gate_b_the_mutant_the_blind_sweep_cannot_catch`. "Moves" there is
  the UNION of mask flips and value changes, so the set is the one the
  sentence claims and not the subset a mask-only comparison would see.
  ⚠ Two review rounds went into that one line. Round 1 caught that the
  first draft printed one offset and tested eleven while claiming "each";
  round 3 caught that both were comparing NaN masks only. Both now cover
  all twelve offsets under the wider definition, and the answer did not
  change.

---

## C — Gate C: reachability

| frame | fires / n | distinct | min | median | max | > 0.25 |
|---|---|---|---|---|---|---|
| walk | 1480 / 1500 | 1480 | 0.005051 | 0.237177 | 0.696270 | 690 |
| tick-rounded | 1480 / 1500 | 1480 | 0.005079 | 0.236987 | 0.695348 | 691 |
| ar1+ | 1480 / 1500 | 1480 | 0.004426 | 0.220223 | 0.814448 | 652 |
| ar1- | 1480 / 1500 | 1480 | 0.002651 | 0.225590 | 0.781905 | 649 |
| heavy-tailed | 1480 / 1500 | 1480 | 0.000214 | 0.160986 | 0.993115 | 564 |
| right-skewed | 1480 / 1500 | 1480 | 0.022736 | 0.200833 | 0.786329 | 584 |
| left-skewed | 1480 / 1500 | 1480 | 0.022736 | 0.200833 | 0.786329 | 584 |
| two-point | 1480 / 1500 | 111 | 0.250000 | 0.250000 | 0.250000 | 676 |
| trending | 1480 / 1500 | 1480 | 0.012659 | 0.230300 | 0.760062 | 649 |
| clustered | 1480 / 1500 | 1480 | 0.000113 | 0.190623 | 0.997972 | 615 |

⚠ The right- and left-skewed rows are identical because the column reads
squares: those two frames' returns are exact negatives of each other
(§A5.5).

⚠ **The two-point frame is a CONSTANT, and its 111 "distinct values" are
rounding.** Every \|return\| there is the same size, so the exact answer
is `tail / length` = 0.25 on every window: the 111 doubles span
**1.191e-14** and all sit within 6.134e-15 of 0.25. Its sample standard
deviation is 0.000000 (§S). Any rank statistic on that frame reads the
rounding, which is why §D treats it separately.

At other lengths on a walk:

| `length` (tail) | fires | distinct | range | median |
|---|---|---|---|---|
| 4 (1) | 1496 / 1500 | 1496 | [2.086e-09, 0.993884] | 0.162855 |
| 5 (1) | 1495 / 1500 | 1495 | [1.081e-09, 0.925316] | 0.121028 |
| 7 (1) | 1493 / 1500 | 1493 | [6.875e-10, 0.850996] | 0.079376 |
| 21 (5) | 1479 / 1500 | 1479 | [5.029e-03, 0.695671] | 0.225516 |
| 60 (15) | 1440 / 1500 | 1440 | [5.304e-02, 0.542782] | 0.240872 |
| 250 (62) | 1250 / 1500 | 1250 | [1.638e-01, 0.383407] | 0.252472 |

`0 < fires < n` on every frame and at every length. ⚠ These counts are
synthetic. The real-data counts (Gate C on the 89 ALTPORT-1 frames) are
**§E1**, from the Gate E run: 397,069 fired of 398,849 pooled bars, 396,809
of them non-zero.

---

## D — Gate D: scale-freedom

**x8 and x64 are bit-identical BY CONSTRUCTION.** Every input is a price
ratio and `8a / 8b` is the same double as `a / b`, so neither sum can
move.

| frame | masks | shared | x8 bit-equal | x64 bit-equal |
|---|---|---|---|---|
| walk | True | 1480 | **1480** | **1480** |
| tick-rounded | True | 1480 | **1480** | **1480** |
| ar1+ | True | 1480 | **1480** | **1480** |
| ar1- | True | 1480 | **1480** | **1480** |
| heavy-tailed | True | 1480 | **1480** | **1480** |
| right-skewed | True | 1480 | **1480** | **1480** |
| left-skewed | True | 1480 | **1480** | **1480** |
| two-point | True | 1480 | **1480** | **1480** |
| trending | True | 1480 | **1480** | **1480** |
| clustered | True | 1480 | **1480** | **1480** |

At x8 and other lengths, all bit-equal with identical masks: 1,496 /
1,495 / 1,493 / 1,479 / 1,440 / 1,250 at `length` 4 / 5 / 7 / 21 / 60 /
250. At price levels 1e-6, 1e+6 and 1e+100: 1,480 of 1,480 bit-equal at
each.

**x10 / x3.7 / x0.1 / x1.0000001 are NOT bit-identical by construction,
and are not in fact.** All 40 (frame, factor) pairs keep the NaN masks
exactly. The widest readings:

| reading | worst over the 40 pairs |
|---|---|
| max \|difference\| | 3.919e-14 (clustered, x0.1) |
| max RELATIVE difference | **4.63e-13** (clustered, x10) |
| Spearman, nine varying frames | 1.000000 everywhere |
| Spearman, two-point frame | 0.540626 / 0.572845 / 0.571894 / 0.611396 |

⚠ The two-point frame's 0.54 is **not** a scale failure. The column there
is a constant 0.25 plus 1.2e-14 of rounding (§C), so a rank correlation
ranks that rounding; the max \|difference\| on that frame is 7.244e-15 and
the relative difference is the reading that survives. The clustered
frame's relative figure is the largest only because its smallest value is
1.1e-04.

**`price ** 2` and `price ** 0.5` are not rescales**, and the column is
not invariant to them: 0 of 1,480 bars bit-equal, max \|diff\| 0.0139 and
0.0069. It nearly is in RANK — Spearman **0.999583** and **0.999885** —
and the reason is worth knowing: a power map scales every LOG return by
the power, so a ratio of squared LOG returns would be exactly invariant,
and simple returns approximate log returns.

---

## G — the guards, the floor this module does not have, and locality

### G1 — a bad close empties its windows and nothing earlier

A close that is not a finite, normal, positive float spoils the returns
at its own bar and at the next, so it empties the `length + 1` = 21
windows that hold either.

| bad value at bar 200 | windows emptied | earlier bars moved |
|---|---|---|
| NaN | 21 | **0** |
| inf | 21 | **0** |
| -inf | 21 | **0** |
| zero | 21 | **0** |
| negative | 21 | **0** |
| subnormal 1e-310 | 21 | **0** |

Over all **36** (value, position) pairs — those six values at bars 0, 1,
19, 200, 398 and 399 — the worst earlier-bar movement is **0**. Near
either end fewer windows exist to empty: a NaN close at bar 0 / 1 / 19 /
200 / 398 / 399 empties 1 / 2 / 20 / 21 / 2 / 1.

⚠ "Earlier" means every bar up to and NOT including `j`, the earliest
window that can see close `j` (bar T reads closes T − length .. T). The
bar at `j − 1` is INCLUDED, and it is the one that matters: an off-by-one
in the window-to-bar mapping would move it first. An earlier draft of
both the script and
`test_a_bad_close_empties_its_windows_and_nothing_earlier` sliced
`:max(j - 1, 0)` and so excluded exactly that bar; review round 3 caught
it, and the counts above come from the wider slice.

### G2 — the per-return bound, taken BEFORE the square

The ceiling is `sqrt(max / (2 * length))` = **2.1200e+153** at the
default: `length` squares of it sum to half the float maximum, so a
window's total is a number rather than an infinity. An infinite total
would make every ratio 0 or NaN instead of a share.

* a return of 4.240e+153 (twice the bound) at bar 200 of a 400-bar walk:
  fires 360 against the unspiked 380 — the 20 windows holding it, and
  nothing else;
* a return of 1.060e+153 (half the bound) there: all 380 still fire, and
  the bar reads exactly **1.0**, which is the right answer — that one
  return is the whole window's energy;
* a frame of nothing but out-of-bound returns: **0** numpy warnings and 0
  of 400 fired. Because the test is on the return and not on its square,
  the square cannot overflow.

### G3 — there is NO dispersion floor, and that is a decision

| frame | fires | distinct | range | max ulp vs exact |
|---|---|---|---|---|
| flat (300 identical closes) | **0** / 300 | — | — | — |
| 1%-a-bar ladder | 280 / 300 | 28 (27 under the reduced-CPU run) | [0.250000, 0.250000] | 3.00 |
| quiet, returns 1e-6 | 580 / 600 | 580 | [0.013227, 0.738832] | 3.00 |

⚠ That 28 is exactly the kind of count this repo's CI rule forbids
pinning: the ladder's returns are mathematically one number that float64
renders to rounding, so how many distinct doubles it renders depends on
the kernel. No test asserts it;
`test_there_is_no_dispersion_floor_and_this_is_what_that_buys` pins the
280 fired windows and that every one is within 1e-14 of 0.25.

The siblings `ts_binent_20` and `ts_aggac_60` refuse a degenerate window
at the same 4096 ulps but on DIFFERENT statistics of it — the return
RANGE (`ts_binent_20.py:75`) and the return SD (`ts_aggac_60.py:27`) —
because both read a spread whose own rounding the statistic then
amplifies. This one divides a window's energy by that window's own total,
so a degenerate window gives the RIGHT answer rather than a loud one: the
ladder's return is only *mathematically* constant and float64 renders it
only to rounding, yet all 280 windows read 0.25 within 1e-14 of it. Both
floors are priced, because the decision names both modules:

| frame | fired | the range floor would empty | the sd floor would empty |
|---|---|---|---|
| flat | 0 | 0 | 0 |
| 1%-a-bar ladder | 280 | **280** | **280** |
| quiet, returns 1e-6 | 580 | **0** | **0** |

Either floor is all cost and no benefit here.

The flat frame is EMPTY and not zero, which is the source's own rule:
`full_series_energy == 0` has no share to report. 21 identical closes are
the only way honest data reaches it.

### G4 — locality: a rolling sum carries a residue, this spelling does not

A 2,000-bar frame priced at 1e-198 with one return planted at bar 200 and
undone at bar 201. Bars from 222 on are windows the spike has LEFT.

Two runs of the same section: `python docs/measure_ts_energy_last_20.py
G` and `python docs/measure_ts_energy_last_20_cpu.py G`, the second with
`AVX512F AVX512_SKX AVX2 FMA3` disabled.

| spike | module, default run | module, reduced-CPU run | prototype, default run | prototype, reduced-CPU run |
|---|---|---|---|---|
| x1e+02 | **1778 of 1778** | **1778 of 1778** | 41 of 1778 | 1690 of 1778 |
| x1e+06 | **1778 of 1778** | **1778 of 1778** | 41 of 1778 | 1690 of 1778 |
| x1e+08 | **1778 of 1778** | **1778 of 1778** | 0 of 1778 | 0 of 1778 |
| x1e+100 | **1778 of 1778** | **1778 of 1778** | 0 of 1778 | 0 of 1778 |
| x1e+300 | **1778 of 1778** | **1778 of 1778** | 0 of 1778 | 1690 of 1778 |

⚠ **The prototype's two columns disagree, which is why the test pins only
"not all of them".** `np.exp` and `np.cumsum` are dispatched, so the
generated closes differ in their last bits between kernels, and whether a
Kahan-compensated running sum happens to recover its residue depends on
those bits: three of the five magnitudes move between the two runs. Every
cell is still short of 1,778, which is the claim —
`test_the_window_is_LOCAL_where_a_rolling_sum_is_not` asserts
`kept < n` and nothing finer.
The module's side is the structural claim and is pinned exactly, in both
runs: each window is reduced on its own, so there is nothing to carry.

### G5 — the other route to an empty window: UNDERFLOW

`sqrt(tiny)` = 1.4917e-154, and `(7.4583e-155) ** 2` is the subnormal
5.562684646268003e-309. Below that the square is exactly zero:

* 60 returns of 1e-200: fires **0 of 60** — every square underflows, so
  the window has no energy at all, and the source's `full == 0` rule
  applies;
* 40 of those followed by 20 honest ones: fires 20 of 60, reading
  [0.250000, 1.000000] — the mixed windows put every scrap of energy in
  the tail.

Honest market data cannot reach either case.

---

## O — overlap

### O1 — the two in-fork columns that ask the same question

`TFCENTROID_20` (TSFEL's temporal centroid, issue #116, merged
2026-10-30) is the energy-weighted MEAN position of the SAME 20 returns;
`TS_IMQ_20` (issue #99, merged 2026-11-14) is their absolute-mass MEDIAN
position. This column is their share in the last quarter.

| frame | TFCENTROID_20 | TS_IMQ_20 | TS_CID_CE_20 | TS_ABOVE_MEAN_20 | TS_MEDSKEW_20 |
|---|---|---|---|---|---|
| walk | 0.758975 | 0.591627 | 0.047072 | -0.015415 | 0.018405 |
| tick-rounded | 0.759114 | 0.591403 | 0.047311 | -0.010597 | 0.018237 |
| ar1+ | 0.767098 | 0.635847 | 0.002543 | 0.006847 | -0.023276 |
| ar1- | 0.721507 | 0.558757 | -0.034620 | 0.084148 | -0.074292 |
| heavy-tailed | 0.668790 | 0.534316 | -0.073762 | 0.047589 | -0.001598 |
| right-skewed | 0.695561 | 0.525749 | 0.012128 | 0.135158 | -0.014767 |
| left-skewed | 0.695561 | 0.525749 | 0.012128 | -0.135158 | 0.014767 |
| two-point | 0.725000 | 0.450092 | 0.040132 | -0.032842 | 0.069490 |
| trending | 0.727246 | 0.533141 | -0.150906 | -0.003070 | -0.003670 |
| **clustered** | **0.906556** | 0.881240 | 0.018321 | -0.034287 | 0.039067 |

| pair | pooled (n = 14,800) | per-frame median | max | ≥ 0.90 |
|---|---|---|---|---|
| vs `TFCENTROID_20` | **0.749306** | 0.7261 | **0.9066** | 1 of 10 |
| vs `TS_IMQ_20` | 0.609322 | 0.5465 | 0.8812 | 0 of 10 |

Under `r3-perframe-0.90` both of those figures put the `TFCENTROID_20`
pair in the **SHIP** band, not in DISCLOSE_GAP: the bands are STRUCK at
≥ 0.90, DISCLOSE_GAP 0.80 ≤ ρ < 0.90, DISCLOSE 0.76 ≤ ρ < 0.80 and SHIP
below 0.76, and pooled 0.7493 with a per-frame median of 0.7261 is under
the 0.76 line on both limbs. It is reported here anyway because the
per-frame MAX reaches 0.9066 on the adversarial `clustered` frame, which
no band reads but a reader should. Not STRUCK, explicitly: STRUCK needs
pooled ≥ 0.90 or a top-5 comparator's per-frame MEDIAN ≥ 0.90, and
neither limb is close.
⚠ An earlier draft of this paragraph called the pair DISCLOSE_GAP, which
is the label `docs/TsImq20Measured.md` carries correctly for its own
0.8466 / 0.8545. Copying a sibling's label onto this port's smaller
numbers was wrong, and round 1 of the review caught it.

⚠ The frame that reaches 0.9066 is `clustered`, which was written FOR
this receipt to make energy pile up at one end of a window — the
adversarial case for the pair. At the lengths the two columns share:
walk 0.7134 / 0.7590 / 0.7401 and clustered 0.8104 / 0.9066 / 0.4948 at
`length` 8 / 20 / 60.

⚠ **These are SYNTHETIC and they are the only measurement of either pair
that exists.** Gate E's 687 comparators are the engine's `compute_all`
and `ml_features` columns and hold no pandas_ta port, so the launcher's
run cannot see either pair; and the screen's fork overlap predates both
siblings (§E0). This is the same hole `docs/TsImq20Measured.md` §O
records for the `TS_IMQ_20` / `TFCENTROID_20` pair, which it measured at
pooled 0.8466. The fork now ships three readings of "where in the last 20
returns was the volatility", and if the owner reads any of them as a
restatement, the three figures to compare are 0.8466 (imq/centroid),
0.7493 (this/centroid) and 0.6093 (this/imq).

Against the fork's other 20-return statistics columns it is near zero:
per-frame \|ρ\| at most 0.1509 (`TS_CID_CE_20`), 0.1352
(`TS_ABOVE_MEAN_20`) and 0.0743 (`TS_MEDSKEW_20`).

### O2 — it is a RECENCY of volatility, not a level

| frame | NATR_20 | UI_20 | window return sd | close | natr Chg 5d\* | \|r\| 5/20\* |
|---|---|---|---|---|---|---|
| walk | 0.369259 | 0.019723 | -0.044589 | -0.017378 | 0.903892 | 0.963759 |
| tick-rounded | 0.369204 | 0.019827 | -0.044717 | -0.017452 | 0.903789 | 0.963746 |
| ar1+ | 0.356828 | -0.074218 | 0.027497 | 0.011286 | 0.868878 | 0.971846 |
| ar1- | 0.394694 | -0.031559 | -0.042436 | 0.027143 | 0.920215 | 0.966627 |
| heavy-tailed | 0.142769 | -0.106619 | -0.223120 | 0.002294 | 0.890614 | 0.967232 |
| right-skewed | 0.287923 | 0.151168 | -0.140877 | 0.034123 | 0.913503 | 0.955825 |
| left-skewed | 0.275847 | -0.234235 | -0.140877 | -0.022926 | 0.933295 | 0.955825 |
| two-point | 0.033790 | 0.042768 | -0.062762 | -0.006739 | -0.004615 | 0.998589 |
| trending | 0.384661 | -0.047101 | 0.001241 | 0.005586 | 0.923625 | 0.955806 |
| clustered | 0.236135 | -0.331222 | -0.051039 | -0.041263 | 0.921095 | 0.987902 |

A share cancels the window's overall size, so the column cannot see how
volatile the window was — only where in it the volatility sat.

⚠ **The last two columns are STAND-INS and not the engine's columns.**
`natr chg 5d` is this fork's `natr` over a synthetic ±0.4% high/low band
divided by its own value 5 bars earlier; `|r| 5/20` is the ratio of mean
\|return\| over 5 bars to mean \|return\| over 20, built from the same
closes. Both read 0.87 .. 0.999 here. The engine's real columns read **0.7020**
(`natr_Chg_5d`) and **0.5460** (`ATR_Ratio_5_20`) — the screen's figures on
89 REAL frames against the prototype, and §E's Gate E run on THIS module
reproduced both to every printed digit. The gap between 0.96
and 0.55 is the whole reason Gate E exists: a close-based stand-in built
from the same returns is a much nearer neighbour than a true-range
column, so these two rows are an upper bound on the fork's exposure and
not an estimate of the engine's.

---

## S — the statistic itself

**0.25 is the neutral reading, for any return law.** 20,000 INDEPENDENT
windows, so the relation is not an artefact of overlap:

| law | mean | sd |
|---|---|---|
| gaussian | 0.248785 | 0.129782 |
| student-t(2) | 0.247416 | 0.230899 |
| one-sided exponential | 0.250349 | 0.177301 |

The centre is `tail / length` whatever the shape — a share of an evenly
spread total does not care about it — and what the tails change is the
SPREAD, which nearly doubles from gaussian to student-t(2).

**Autocorrelation.** Windows one bar apart share 19 of their 20 returns.

| frame | lag 1 | lag 5 | lag 20 | lag 21 |
|---|---|---|---|---|
| walk | 0.785858 | -0.027806 | 0.000606 | 0.001186 |
| heavy-tailed | 0.757507 | -0.101709 | 0.041593 | 0.037266 |
| clustered | 0.902735 | 0.422692 | **-0.380409** | -0.403601 |

On an iid frame the column is a state for about `tail` bars and then
forgets. On the clustered frame the lag-20 sign is structural rather than
noise: a cluster that sat in the TAIL of window T sits in the BODY of
window T+20.

**One bar moves exactly `length` bars, and the SIGN says which sum it is
in.** A -50% bar at 700 moves bars 700..719 and nothing else — ×0.5
rather than ×0.8 so that every later ratio is the same double and the
count is exact. The move is POSITIVE on bars 700..704 (5 of 5), where the
bar is in both sums, and NEGATIVE on 705..719 (15 of 15), where it is
only in the denominator.

**What it is FOR.**

| frame | sd | p05 | p95 |
|---|---|---|---|
| walk | 0.132616 | 0.063064 | 0.493501 |
| clustered | 0.311280 | 0.001254 | 0.978721 |
| two-point | 0.000000 | 0.250000 | 0.250000 |

The column separates a frame whose energy clusters from one whose does
not, and reads a constant on one whose every move is the same size.

---

## E — Gate E

**Gate E: SHIP.** Run `is102-ts_energy_last_20-3468c96b`, measured
2026-11-14 by issue-solver on **this** module, not on the prototype.

| | |
|---|---|
| column | `TS_ENERGY_LAST_20_4` |
| pooled max \|ρ\| | **0.7020** (signed +0.7019760071757274) |
| against | `natr_Chg_5d`, from the `ml_features` manifest |
| n | **397,069** |
| per-frame max median \|ρ\| | **0.7036** (0.7035745545967381), also against `natr_Chg_5d` |
| frames at \|ρ\| ≥ 0.90 | **0 of 89** — and 0 of 89 at ≥ 0.80, on each of the top five |
| verdict | **SHIP** (`r3-perframe-0.90`; SHIP is < 0.76 pooled and < 0.90 per-frame median) |
| best `compute_all` comparator | `pvo_PVOh_12_26_9`, 0.3814323236250707, n = 396,624 |
| comparators | 687 = 329 `compute_all` + 358 manifest, 1 degenerate |
| universe | 89 frozen ALTPORT-1 BIST frames, 398,849 pooled bars |
| defaults | `kwargs: {}` — no non-default parameter |
| canary | AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal |
| versions | pandas 2.3.3 / numpy 1.26.4 |
| module sha1 | `e0baceb438b5056961ee928bd0183cbd5d59aeb2` |
| tree sha1 | `ffa0a50762394d9c74c82a02702ee60327fb6166` |

The one degenerate comparator is `squeeze_SQZ_NO` (manifest), constant over
the 397,069 shared bars.

The top five, pooled and per frame:

| against | set | pooled \|ρ\| | per-frame median | per-frame max | per-frame min |
|---|---|---|---|---|---|
| `natr_Chg_5d` | manifest | 0.7020 | 0.7036 | 0.7721 | 0.5729 |
| `ATR_Ratio_5_20_Pctl` | manifest | 0.5530 | 0.5480 | 0.5973 | 0.4288 |
| `ATR_Ratio_5_20` | manifest | 0.5460 | 0.5450 | 0.5923 | 0.4281 |
| `ATR_Ratio_5_20_State` | manifest | 0.5252 | 0.5241 | 0.5619 | 0.4304 |
| `Range_ATR` | manifest | 0.3926 | 0.3963 | 0.4781 | 0.3214 |

⚠ The single worst frame-and-comparator pair in the top five is **0.7721**,
which is ABOVE the 0.76 line — and it is a per-frame MAX on one of 89
frames, which neither limb of `r3-perframe-0.90` reads. The band is decided
on the pooled ρ (0.7020) and on a top-5 comparator's per-frame MEDIAN
(0.7036), both under 0.76, and the per-frame distribution against
`natr_Chg_5d` runs 0.5729 .. 0.7721 with 0 of 89 frames at or above 0.80.
The figure is reported because a reader should see it, not because it moves
the verdict; the next comparator's worst frame is 0.5973.

The whole top 25 is the `natr_Chg_5d` / ATR-ratio family and then volatility
and volume ratios: after `Range_ATR` come `Range_ATR_Pctl` 0.3851,
`pvo_PVOh_12_26_9` 0.3814 (the highest `compute_all` column), `Range_ATR_State`
0.3690 and the `THERMO_pct` trio at 0.3412 / 0.3277 / 0.3193. Nothing in the
687 reads the column as a price level: §O2's point that a share cancels the
window's size survives the real run.

Recorded with
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-14`;
`record` accepted it, which is what checks that the harness imported a
`pandas_ta` tree byte-identical to this one, that the parameters were the
defaults, that the universe was the 89 frames, that the comparator set was
687 and that the canary was bit-equal. The row is
`docs/gate_e_ledger.csv` line 97, with no waiver.
`tests/test_ts_energy_last_20.py::test_the_gate_e_row_is_this_ports_own_measurement`
pins the row's identity (run id, module, column, verdict); the porting
session's `test_the_gate_e_row_is_owed` is gone.

⚠ What the run does NOT settle is §O1: the 687 comparators are the engine's
`compute_all` and `ml_features` columns and hold no pandas_ta port, so the
pairs against the fork's own `TFCENTROID_20` (0.7493 pooled synthetic) and
`TS_IMQ_20` (0.6093) are still measured on synthetic frames only. SHIP here
is a verdict about the engine's columns, not about those two.

### E1 — Gate C on real data, from that run

The run's own counts over the 89 frames, 398,849 pooled bars:

| | bars |
|---|---|
| pooled | 398,849 |
| non-NaN (`TS_ENERGY_LAST_20_4` fires) | **397,069** |
| non-zero | **396,809** |
| NaN | 1,780 |
| exactly 0.0 | **260** |

So `0 < 397,069 < 398,849` on real data. The 1,780 empty bars are 20 warm-up
bars per frame (20 × 89 = 1,780), so the bad-close mask (§G1) and the
per-return bound (§G2) emptied **no** further real bar. That is a count, and
what it rules out is bounded: a bad close at any bar from 1 on would empty
windows the warm-up does not already cover, so no close after bar 0 of any
of the 89 frames is NaN, non-positive, subnormal or infinite, and no return
exceeded 2.1200e+153. A bad close at bar **0** of a frame would be invisible
to this count, since the only window it empties is one the warm-up empties
anyway.

The **260** bars that read exactly 0.0 are §A4's second closed form reached
on real prices. That the count is 260 is measured; what has to produce a
zero is read off the formula rather than counted per bar: the numerator is a
sum of five squares, so it is exactly zero only when each of the newest five
returns is, i.e. when the six closes ending at that bar are all equal — the
exact-tie behaviour BIST daily data is full of (the FVGDEAD note in
`CLAUDE.md` measured 21.17% of 408,253 bars closing exactly at an extreme).
The denominator cannot be zero on those bars, or the bar would be NaN
instead, so the older 15 returns carry energy. 260 of 397,069 is 0.065%, and
it is the end of the [0, 1] range the synthetic frames of §C never reach by
accident — their minimum is 1.1e-04, and §A4 reaches exactly 0.0 only by
construction. The other end, exactly 1.0, has no count here: the run records
non-zero and non-NaN, not a maximum.

⚠ Those are the Gate E universe's counts. Separately, the ledger row stores
an output fingerprint taken on `gate_e_ledger.py`'s own fixed 600-bar
tick-rounded frame —
`580;148.7631420052424;48.470026690154874;46230.23903319545`, i.e. finite
count, sum, sum of squares and index-weighted sum (`gate_e_ledger.py:148`) —
which is what `tests/test_gate_e_ledger.py` re-derives to catch a later edit
moving the output. 580 = 600 − 20, the same warm-up as above, and
148.763 / 580 = 0.2565 is a mean within a tenth of §S's neutral 0.25.

---

## F — Gate F: the suites

Re-run in the receipt session (2026-11-14), after the Gate E row was
recorded:

* `python -m pytest tests/test_ts_energy_last_20.py -q` → **226 passed**
  in 6.07 s, including the new
  `test_the_gate_e_row_is_this_ports_own_measurement`, which replaced the
  porting session's `test_the_gate_e_row_is_owed`. The count is unchanged
  because that was a one-for-one replacement.
* `python docs/measure_ts_energy_last_20_cpu.py` → the same **226
  passed** in 5.74 s with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX
  AVX2 FMA3"`; the run prints the dispatchable features still enabled
  (`SSSE3 SSE41 POPCNT SSE42 AVX F16C AVX512CD AVX512_CLX AVX512_CNL
  AVX512_ICL`) and refuses to report anything if the environment edit did
  not take. ⚠ That run is what turns §A1's reasoning into evidence: this
  module's Gate A is bit-equality between two `np.add.reduce` calls over
  the same bytes, and both are dispatched kernels. It is also what forced
  §G4's prototype column to be pinned as a bound rather than a count.
* `python -m pytest tests/test_ts_energy_last_20.py
  tests/test_gate_e_ledger.py -q` → **1 failed, 1,146 passed**: the 226
  above plus 921 ledger checks, the one failure being the owed-row test,
  which now reports **seven other** indicators — `['arch_lm',
  'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'lumpiness',
  'mtd_ret']`, all owed by someone else and none of them this port. Those
  921 are what re-derive this row's `module_sha1` and output fingerprint
  from the tree and check its verdict arithmetic.
* `python -m pytest -q` → **3 failed, 8,366 passed, 85 skipped** in
  213.00 s. The three are the ones a clean checkout of `dev` already
  carries, and `ts_energy_last_20` is in none of them:
  * `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
    — the CLAUDE.md *Known breaks* entry, owner's call;
  * `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
    — needs the sibling `../AlternativeRepos` checkout; CI deselects it
    by name;
  * `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
    — the seven indicators above, all owed by other issues. CI into `dev`
    sets `GATE_E_PENDING_OK=1` and skips it with a reason starting "Gate E
    owed".
* The porting session's own figure, kept for the record: `python -m pytest
  -q` → **3 failed, 8,359 passed, 85 skipped** (in 212.37 s; four
  full-suite runs that session read 221.53, 214.53, 212.38 and 212.37 s for
  the same three failures), where the third failure listed
  `ts_energy_last_20` as an eighth owed indicator. The 7 extra passes this
  session are `tests/test_gate_e_ledger.py`'s per-row parametrised checks
  over the row this session added.
* ⚠ One more failure appeared on the first full-suite run of this session
  and was FIXED, not excused:
  `test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
  reads any run of five or more slash-joined integers as a retyped
  verdict split, and this file's and `docs/MLCompanionContract.md`'s
  lists of the lengths Gate A and Gate D were measured at matched that
  shape. They are now written out with commas. The guard was right to
  fire on the shape even though the content was not a split — and it
  fired twice more in this run: on the first draft of this very bullet,
  which quoted the offending string in order to explain it (round 1 of
  the review caught that), and on round 3's verdict quoted into
  `docs/reviews/auto-2026-11-14-ts-energy-last-20/01-ts-energy-last-20.md`,
  where the reviewer's own summary slash-joined this port's five wiring
  counts. The first two were rewritten; the third is a quote the review
  protocol requires verbatim, so that line carries the guard's own
  `stale-by-design` marker with the reason beside it. All three are the
  same lesson: the shape is the rule, whatever the content.

The Backtesting suite is the launcher's to run.

---

## Z — cost

**The claim is the traced peak: 22.8 MB on 400,000 bars at each of
`length` 4, 20, 60 and 250.** Nothing allocated grows with `length` — the
tail slice is basic slicing, so it is a view, and both reductions produce
`(rows,)` arrays.

**The second claim is the SHAPE of the time, not its value: the
best-of-5 time grows monotonically with `length`, and `length` 250 costs
between 2.59x and 2.74x `length` 4** — because each window is reduced in
full rather than updated from its neighbour. That is the price of the
locality §G4 measures and of §A1's bit-equality. `section_Z` prints the
ordering and the ratio as the last two lines of its own output, so both
are read off a run rather than off this table. Seven best-of-5 runs on
this worktree — four in this session (2.66, 2.64, 2.74, 2.71) and three
in review round 4 (2.59, 2.62, 2.64) — were monotone in all seven and
span 2.59 .. 2.74, which is why the figure above is a RANGE: an earlier
draft said "about 2.7x", which is above five of the seven.

| `length` | best of 5 | worst of 5 | traced peak |
|---|---|---|---|
| 4 | 19.2 ms | 20.4 ms | 22.8 MB |
| 20 | 28.3 ms | 29.4 ms | 22.8 MB |
| 60 | 34.0 ms | 34.4 ms | 22.8 MB |
| 250 | 51.2 ms | 51.8 ms | 22.8 MB |

monotone: True · ratio best(250) / best(4): **2.66x**. An immediate
second run of the same section read 19.3 / 28.2 / 33.8 / 50.9 ms, True
and 2.64x.

⚠ **The milliseconds are not a claim, and this section took three review
rounds to say so.** The first draft quoted one run's four figures while
the header above promised every number in §Z was reproducible; round 1's
reviewer measured 20.4 / 29.6 / 35.9 / 52.3 and round 2's 26.8 / 37.1 /
43.1 / 63.8 on this same worktree — up to 40% apart — and round 2 called
the header. The replacement claimed monotone growth, and round 3 then
falsified THAT by re-running the section four times: one of the four read
18.6 / 38.0 / 34.1 / 51.1, with `length` 20 slower than `length` 60,
because the section timed each length exactly once. Hence
`TIME_REPEATS = 5` and the minimum: a competing process can only move a
minimum upward, so the ordering and the ratio of the minima are what
survive a re-run. The PEAK, which is flat at 22.8 MB, never moved in any
of those runs.
