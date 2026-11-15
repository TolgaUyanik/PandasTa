# TF-DFA-100 — `tf_dfa_100`, measured

PandasTa issue [#112](https://github.com/TolgaUyanik/PandasTa/issues/112).
Source: **TSFEL** (Fraunhofer Portugal AICOS, BSD-3-Clause),
`tsfel/feature_extraction/features.py` `dfa`.
Module: `pandas_ta/statistics/tf_dfa_100.py` · column **`TFDFA_100`**
(statistics, scale-free) · tests: `tests/test_tf_dfa_100.py` ·
every number here is printed by `python docs/measure_tf_dfa_100.py`, except
§E's and §C1's, which come from the Gate E run `is112-tf_dfa_100-da670816`.

`TFDFA_100` is the DFA-1 exponent of the last 100 simple returns: cumulate
the mean-centred returns into a profile, remove a straight line from each
non-overlapping box of 4, 5, 6, 8 and 10 bars, take the root mean square of
what is left at each box size, and fit a straight line through the five
`(log s, log F(s))` points. The slope is the column.

**Two things a consumer must be told, and both are measured below.**

1. **0.5 is not the neutral point on this ladder** (§A5, §A5b). Uncorrelated
   returns read **0.6289**, not 0.5, because DFA-1's finite-box bias is large
   at boxes of 4 .. 10 bars. The same arithmetic on boxes of 50 .. 320 reads
   0.4997.
2. **The column is not bounded** (§C). Over eight 1,500-bar synthetic frames
   it runs **-0.2197 .. 2.3288**; the negative end is a frame with one 50%
   price gap in it.

Gate E is **SHIP** (§E): max |ρ| **0.0979** against the manifest's
`Swing_Range_pct` over n = 389,949, top-five per-frame max median **0.0996**
over the 89 frames, run `is112-tf_dfa_100-da670816` of 2026-11-15 on this
module. Gate C's real-data limb comes off the same run and is in §C1.

---

## Gate A — correctness

### §A — what the source actually says, and what it does not

The whole of the source text available in this worktree is the two lines
issue #112 quotes:

> **What:** detrended fluctuation analysis exponent of returns (100). Source:
> TSFEL (BSD-3-Clause) — `features.py dfa`.
> Prototype: `docs/issues/screen/ind_screen_r2.py`, candidate `tf_dfa_100`
> (scale-free form: boxes 4..10 (TSFEL: up to n/10, with a plateau cut)).

TSFEL is **not installed** here, `docs/pine/` does not carry it, and web
access is unavailable, so Gate A does **not** read TSFEL's own code.
`tests/test_tf_dfa_100.py::test_the_source_library_is_not_readable_here`
asserts `import tsfel` raises, so the limitation fails loudly rather than
rotting into a docstring that is quietly wrong.

What Gate A checks instead is the quantity those lines name — the DFA-1
exponent of Peng et al. 1994 — spelled three independent ways and compared
against the module:

| oracle | what makes it independent | §  |
|---|---|---|
| the screen prototype | the owner's own expression, the one Gate E's 0.0979 was measured on | A1 |
| a scalar loop | running sum for the profile, the normal equations per box, `math.fsum` throughout; shares no numpy operation with the module | A2 |
| `np.polyfit` | both least squares solved by `lstsq` instead of a closed form | A3 |

Three oracles, and that count is the same here and in the test module. §A4's
two variants — every integer box 4..10, and a forward+backward pass — are
**not** a fourth and a fifth oracle: they are the readings this port did not
take, and they produce different columns.

⚠ Nothing here is evidence about TSFEL's **"plateau cut"**, which the issue
mentions in passing. The prototype does not implement one and neither does
this port: all five box sizes always enter the fit.

### §A1 — the screen prototype

`docs/issues/screen/ind_screen_r2.py:255-273`, retyped in `_prototype()`.
1,500-bar frames; `ramp` is 200 bars.

```
frame           bars both  differ   max |diff| only module only proto
walk                 1400     399    2.220e-16           0          0
trend                1400     377    2.220e-16           0          0
range-bound          1400     410    2.220e-16           0          0
grid                 1400     385    2.220e-16           0          0
heavy-tailed         1400     428    2.220e-16           0          0
jump                 1400     435    4.441e-16           0          0
persistent           1400     398    2.220e-16           0          0
mean-reverting       1400     377    1.110e-16           0          0
flat                    0       0          nan           0          0
ramp                    0       0          nan           0          0
TOTAL bars both define: 11200, differing: 3209
```

⚠ **The `differ` column is a count of last bits and does not reproduce
across CPU dispatches**: 3,209 here, **3,161** with AVX-512/AVX2/FMA3
disabled. Per frame, in the table's order, that run reads 379, 385, 398,
415, 382, 388, 368 and 446, against the 399, 377, 410, 385, 428, 435, 398
and 377 above. `max |diff|`, the 4.441e-16 ceiling and the zero mask
divergence DO reproduce under both, and those are what the docstrings quote.
See §F2.

(Slash-joined, those two would read as a verdict split and trip
`tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`,
which is why they are commas. Measured, not guessed: that test failed on the
first draft of this paragraph.)

**Not bit-equal, and that is deliberate.** About 3,200 of the 11,200 bars
differ, by at most **4.441e-16**, and the NaN masks are identical everywhere
(`only module` and `only proto` are 0 on every frame, including the two that
fire nowhere). The whole of the difference is the spelling of the final dot
product — see §Z2 for why this port does not use the prototype's `@` — and
that is pinned rather than asserted: a mutant of the **shipped file** with
`@` put back is bit-equal to the prototype on all ten frames.

```
walk            `@` mutant == prototype, bit for bit: True
trend           `@` mutant == prototype, bit for bit: True
range-bound     `@` mutant == prototype, bit for bit: True
grid            `@` mutant == prototype, bit for bit: True
heavy-tailed    `@` mutant == prototype, bit for bit: True
jump            `@` mutant == prototype, bit for bit: True
persistent      `@` mutant == prototype, bit for bit: True
mean-reverting  `@` mutant == prototype, bit for bit: True
flat            `@` mutant == prototype, bit for bit: True
ramp            `@` mutant == prototype, bit for bit: True
```

At other lengths (walk / trend / heavy-tailed):

```
length bars both  differ   max |diff| mask differs `@` == proto
    20      4440    1270    4.441e-16            0         True
    32      4404    1250    4.441e-16            0         True
    64      4308    1228    2.220e-16            0         True
   100      4200    1204    2.220e-16            0         True
   250      3750    1044    2.220e-16            0         True
```

⚠ This table moves with the dispatch too, in both columns: AVX-disabled it
reads `differ` 1,290 / 1,220 / 1,246 / 1,146 / 1,085 and a length-20 ceiling
of 3.331e-16 rather than 4.441e-16 (the 32, 64, 100 and 250 ceilings are
unchanged, and `mask differs` is 0 and `@` == proto True under both). §F2.

The `ramp` frame exists because a window of EQUAL returns is the only
non-flat way to reach zero fluctuation, and "a geometric ramp" is not enough
on its own — the step has to be a power of two:

```
          step   fires      of
  2.0000000000       0     100
  1.5000000000     100     100
  1.0010000000     100     100
  1.0000000001      24     100
```

### §A2 — the formula by scalar loops

200-bar frames: the oracle is `O(rows * length)` in Python.

```
frame           length bars both      max rel      max abs
walk                20       180    6.350e-15    1.554e-15
walk                32       168    4.422e-15    1.443e-15
walk               100       100    2.837e-15    1.443e-15
trend               20       180    1.006e-13    1.443e-15
trend               32       168    5.773e-15    1.554e-15
trend              100       100    2.403e-15    1.443e-15
heavy-tailed        20       180    3.615e-14    1.776e-15
heavy-tailed        32       168    2.456e-14    1.554e-15
heavy-tailed       100       100    2.371e-15    1.332e-15
persistent          20       180    2.697e-15    1.554e-15
persistent          32       168    2.096e-15    1.998e-15
persistent         100       100    1.511e-15    1.554e-15
mean-reverting      20       180    1.670e-14    1.332e-15
mean-reverting      32       168    6.623e-15    1.332e-15
mean-reverting     100       100    4.960e-15    1.166e-15
worst relative difference: 1.006e-13
```

⚠ Read the **absolute** column. The exponent passes close to zero on some
windows, and a relative figure there is a division by almost nothing: the
worst relative difference is 1.006e-13 while the worst absolute one is
**1.998e-15**. Agreement to a tolerance rather than to the bit is the finding
and not a weakness — a different summation order rounds differently.

⚠ Both figures are the DEFAULT dispatch, and both are the worse of the two
here: AVX-disabled the same run reads worst rel 1.254e-14 and worst abs
1.665e-15 (§F2). The test quotes 2.0e-15 for that reason.

### §A3 — the same quantity through `np.polyfit`

Default dispatch:

```
frame           bars both      max rel      max abs
walk                  100    5.716e-15    2.831e-15
trend                 100    6.414e-15    2.887e-15
heavy-tailed          100    6.938e-15    2.887e-15
persistent            100    2.656e-15    2.331e-15
mean-reverting        100    7.970e-15    2.776e-15
worst relative difference: 7.970e-15
```

`python docs/measure_tf_dfa_100_cpu.py A3`, i.e. with `AVX512F AVX512_SKX
AVX2 FMA3` disabled — **the worse of the two, and the one the quoted bound
comes from**:

```
frame           bars both      max rel      max abs
walk                  100    4.958e-15    2.887e-15
trend                 100    5.465e-15    3.109e-15
heavy-tailed          100    4.536e-15    2.665e-15
persistent            100    2.479e-15    3.109e-15
mean-reverting        100    1.271e-14    2.720e-15
worst relative difference: 1.271e-14
```

So the polyfit oracle agrees to **3.109e-15** absolute, not to the
2.887e-15 of the default run. §F2 lists every BOUND and every headline
figure that moves between the two dispatches, and names the six sections
whose per-cell figures move as well.

### §A4 — the readings this port did NOT take

```
frame            (a) max |d|   (a) rho  (b) max |d|   (b) rho
walk                  0.1169    0.9496       0.0781    0.9788
trend                 0.1142    0.9429       0.0880    0.9737
range-bound           0.1239    0.9529       0.0712    0.9770
grid                  0.1090    0.9603       0.0794    0.9776
heavy-tailed          0.4129    0.8942       0.3350    0.9566
jump                  0.9173    0.9360       0.7191    0.9686
persistent            0.2060    0.9328       0.1279    0.9768
mean-reverting        0.0698    0.9596       0.0500    0.9808
```

(a) every integer box 4..10 rather than the prototype's `(4, 5, 6, 8, 10)`.
(b) the standard forward **and** backward pass, which covers the tail that
the forward-only pass drops (§A7).

Both are different columns, correlated with this one at ρ 0.89 .. 0.98 and
apart by up to 0.92 on a single bar. The prototype's reading is the one that
ships, because the prototype is the expression the 2026-10-24 screen
measured.

### §A5 — the anchors: what a KNOWN process must read

The only external checks available without the source code. 40,000-point
processes, disjoint 100-point windows.

```
process                   windows     mean       sd      p05      p95
iid normal                    400   0.6289   0.1201   0.4361   0.8121
iid student-t(3)              400   0.6332   0.1485   0.4240   0.8914
AR(1) phi=+0.6                400   1.1060   0.1735   0.8219   1.3752
AR(1) phi=-0.6                400   0.2836   0.0719   0.1817   0.4104
alternating +-1 + noise       400   0.0897   0.0068   0.0793   0.1009
integrated (cumsum)           400   1.4785   0.1843   1.1712   1.7696
```

The **ordering** is what the exponent is for and it holds: anti-persistent
below, iid in the middle, persistent above, an integrated series above that.
Two warnings sit in this table:

* **The sd is the estimator's own noise.** 0.12 at 100 points and five
  boxes, against a between-process gap of 0.5 — a SINGLE reading is not a
  confident verdict about one window, it is a feature.
* **The iid mean is 0.6289, not 0.5.** §A5b is where that comes from.

### §A5b — why iid reads above 0.5: the ladder, not the code

A linear detrend removes both a box's starting offset and any constant
drift, so for iid returns the boxes are independent draws and `E[F(s)^2]` can
be measured with no window and no port in the way. 200,000 independent boxes
per size:

```
ladder (4, 5, 6, 8, 10)       implied alpha of iid noise: 0.6292
    E[F(s)]: s=4:0.447 s=5:0.529 s=6:0.596 s=8:0.707 s=10:0.799
ladder (10, 16, 25, 40, 64)   implied alpha of iid noise: 0.5106
    E[F(s)]: s=10:0.799 s=16:1.025 s=25:1.287 s=40:1.631 s=64:2.065
ladder (50, 80, 125, 200, 320) implied alpha of iid noise: 0.4997
    E[F(s)]: s=50:1.826 s=80:2.308 s=125:2.883 s=200:3.651 s=320:4.616
```

0.6292 from the Monte Carlo against 0.6289 measured through the module on iid
returns: the bias is fully accounted for by the box sizes.

The same thing through the SHIPPED arithmetic rather than a re-implementation
of it — `_dfa_alpha` out of a mutant whose `BOXES` is the wider ladder, over
disjoint windows of the same 40,000 iid normal returns:

```
ladder                    window  windows     mean       sd
(4, 5, 6, 8, 10)             100      400   0.6289   0.1201
(10, 16, 25, 40, 64)         128      312   0.4902   0.1144
(50, 80, 125, 200, 320)      640       62   0.4928   0.1059
```

These sit a little below the Monte Carlo's implied values (0.5106, 0.4997)
because a window of only two boxes at the top size fits a noisier line; the
point they carry is the same, and this is the limb
`test_the_iid_centre_is_not_one_half` asserts, so a regression in the per-box
detrend fails it. Through the prototype expression on a 20,000-bar iid frame:

```
length   100 ladder (4, 5, 6, 8, 10)       mean  0.6232  median  0.6191  n 19900
length  1000 ladder (10, 16, 25, 40, 64)   mean  0.5028  median  0.4998  n 19000
length  1000 ladder (20, 32, 50, 80, 100)  mean  0.4909  median  0.4900  n 19000
```

**This is a disclosure, not a defect.** The ladder is the prototype's, the
prototype is what Gate E measured, and a wider ladder would be a different
column. What must not happen is a consumer reading 0.5 as the neutral point:
on this column that misreads half of a random walk as trending.

### §A6 — the return spelling

`close.pct_change(fill_method=None)` is bit-identical to
`close / close.shift(1) - 1` on all eight firing frames.

### §A7 — the tail each box drops

```
 box s  k = n//s  covered  dropped
     4        25      100        0
     5        20      100        0
     6        16       96        4
     8        12       96        4
    10        10      100        0
```

Taking the LAST `k*s` points instead of the first reads the same window but
weights its end, and is a different column:

```
frame             max |diff|       rho
walk                  0.1454    0.9182
heavy-tailed          0.5092    0.8401
persistent            0.2107    0.9107
```

### §A8 — centring, which is a no-op on paper

Subtracting the window mean before the cumulative sum adds a straight LINE to
the profile, and every box removes its own line, so the step cannot change
the exponent in exact arithmetic. In floating point it moves the last bits,
and it is kept because it is the prototype's expression:

```
frame           bars both  differ   max |diff|      max rel
walk                 1400     582    1.221e-15    2.317e-15
trend                1400     619    1.554e-15    2.726e-15
range-bound          1400     589    1.665e-15    2.552e-15
grid                 1400     604    1.499e-15    4.187e-15
heavy-tailed         1400     635    1.998e-15    3.303e-15
jump                 1400     615    1.554e-15    4.538e-14
persistent           1400     642    1.554e-15    1.720e-15
mean-reverting       1400     553    1.554e-15    8.715e-15
```

⚠ Dispatch-dependent, both columns. AVX-disabled the `max |diff|` ceiling
falls to 1.554e-15 (so the 1.998e-15 quoted in `_dfa_alpha`'s comment is the
worse, default run) while `jump`'s `max rel` RISES to 1.302e-13 from
4.538e-14; the `differ` counts move too (609 / 607 / 581 / 597 / 601 / 583 /
611 / 604). §F2.

The same algebra is why the column cannot see a constant drift in the
returns at all (§L3).

---

## Gate B — causality

Eight offsets, `[105, 304, 502, 701, 899, 1098, 1296, 1495]`. At each one the
frame is perturbed two ways from that bar onward and the prefix below it is
compared bit for bit. `caught` counts the offsets at which the prefix moved.

```
frame             real     return-lead    output-early    window-ahead  window-centred   mask
walk                 0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
trend                0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
range-bound          0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
grid                 0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
heavy-tailed         0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
jump                 0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
persistent           0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
mean-reverting       0      8/8 live=1      8/8 live=1      8/8 live=1      8/8 live=1      0
```

Five mutants, each read off the shipped file, edited and `exec`'d in memory:

| mutant | edit | result |
|---|---|---|
| `return-lead` | `close.shift(-1).pct_change(...)` | live, caught 8/8 on every frame |
| `output-early` | writes to `length - 2 + a` | live, caught 8/8 on every frame |
| `window-ahead` | `sliding_window_view(np.roll(r, -1), length)` | live, caught 8/8 on every frame |
| `window-centred` | window centred on the bar (the `bos` failure mode) | live, caught 8/8 on every frame |
| `mask` | `np.roll(defined, -1)` | live, caught **0/8** — see §B2 |

### §B2 — the mutant the blind sweep cannot see

`np.roll(defined, -1)` back-dates the GAP MASK by one bar. The bars it moves
do not depend on the future, so the sweep is blind to it, which is exactly
what CLAUDE.md's Gate B says prefix work cannot see. It is pinned directly
instead: plant one NaN close and read where the gap lands.

```
    at  real first gap  mutant first gap
   200             200               199
   600             600               599
  1000            1000               999
```

### §B3 — prefix truncation across a chunk boundary

⚠ The sweep above runs on frames that fit in ONE chunk, so on its own it says
nothing about the chunk loop — and the chunk loop is the one place where a
bar's value could start depending on how many bars came after it (§Z2). With
the budget cut, the same frame is split many times over:

```
budget    100 (   1 rows per chunk): prefix-stable True, equals the default run True
budget    700 (   7 rows per chunk): prefix-stable True, equals the default run True
budget   9700 (  97 rows per chunk): prefix-stable True, equals the default run True
```

Plain prefix truncation at the default budget is unchanged at every offset on
all eight firing frames.

---

## Gate C — reachability

### §C1 — real data

**Closed**, off the Gate E run of 2026-11-15 (`is112-tf_dfa_100-da670816`,
§E), whose ledger row carries the counts:

```
pooled bars over the 89 BIST frames   398,849
fired (non-NaN)                       389,949
empty                                   8,900  = 89 * 100 exactly
fired bars reading exactly 0.0              0  (non_zero == non_nan)
```

So `0 < fires < n` holds on real data and not only on §C2's synthetic
frames. The 8,900 empty bars are `89 * 100` with nothing left over — §C2's
constant 100-bar warm-up, on real prices, on every one of the 89 frames;
`tests/test_tf_dfa_100.py::test_the_gate_e_run_closes_gate_c_on_real_data`
pins that as `empty == n_frames * LENGTH`, which a data-dependent warm-up or
a warm-up of any other length could not satisfy.

⚠ Two things the row cannot show. The warm-up arithmetic assumes every frame
is longer than 100 bars, and the row carries only the pooled total (4,481.4
bars per frame on average). And the row records no minimum or maximum, so
§C2's measured range — and the ⚠ below it — stays synthetic-only evidence:
what the run adds is that `non_zero` equals `non_nan`, i.e. not one of the
389,949 fired real bars read exactly 0.0.

### §C2 — synthetic frames

```
frame             bars  fires distinct       min    median       max
walk              1500   1400     1400    0.3075    0.6444    1.0620
trend             1500   1400     1400    0.2851    0.6288    1.0213
range-bound       1500   1400     1400    0.2903    0.6413    0.9948
grid              1500   1400     1400    0.2812    0.6127    1.0249
heavy-tailed      1500   1400     1400    0.2259    0.6354    1.3612
jump              1500   1400     1400   -0.2197    0.7054    2.3288
persistent        1500   1400     1400    0.5154    1.0580    1.5602
mean-reverting    1500   1400     1400    0.0815    0.2913    0.5504
flat              1500      0        0         -         -         -
ramp               200      0        0         -         -         -
```

Every firing frame fires on 1,400 of 1,500 bars — the constant 100-bar
warm-up, no more — with 1,400 distinct values, so no bit-identity in Gate D
can pass by the column being constant. The first fired bar is bar 100, not
99: 100 returns need 101 closes.

⚠ **The range.** `jump` reaches -0.2197 and 2.3288, outside everything the
other seven frames occupy. There is no bound to quote.

---

## Gate D — scale-free

### Exact binary factors: bit-identical

```
frame                     x8          x64       2**-40        2**40       2**100
walk                    True         True         True         True         True
trend                   True         True         True         True         True
range-bound             True         True         True         True         True
grid                    True         True         True         True         True
heavy-tailed            True         True         True         True         True
jump                    True         True         True         True         True
persistent              True         True         True         True         True
mean-reverting          True         True         True         True         True
```

And x8 at `length` 20, 32, 64, 100 and 250: bit-identical on every firing
frame. `(k*a) / (k*b)` is exactly `a / b` for a binary `k`, so not one input
bit changes.

### Inexact factors: a tolerance

```
frame                                x10                     x3.7                     x0.1               x1.0000001
walk              9.616e-15 /  5.440e-15   9.142e-15 /  6.106e-15   1.102e-14 /  6.217e-15   9.108e-15 /  5.218e-15
trend             1.573e-14 /  7.994e-15   1.044e-14 /  6.772e-15   1.320e-14 /  6.994e-15   1.379e-14 /  6.106e-15
range-bound       4.984e-15 /  2.776e-15   4.350e-15 /  2.776e-15   5.120e-15 /  3.553e-15   5.032e-15 /  3.109e-15
grid              1.065e-14 /  5.329e-15   9.406e-15 /  5.329e-15   7.695e-15 /  4.663e-15   1.232e-14 /  6.994e-15
heavy-tailed      1.035e-14 /  4.663e-15   8.047e-15 /  4.996e-15   8.010e-15 /  4.441e-15   9.173e-15 /  4.219e-15
jump              7.295e-13 /  4.330e-15   3.310e-14 /  5.773e-15   4.310e-13 /  6.550e-15   6.635e-14 /  8.105e-15
persistent        8.367e-15 /  7.550e-15   4.980e-15 /  4.885e-15   6.171e-15 /  5.995e-15   6.432e-15 /  6.883e-15
mean-reverting    1.840e-14 /  4.996e-15   1.406e-14 /  4.163e-15   1.891e-14 /  3.442e-15   1.234e-14 /  4.274e-15
worst relative: 7.295e-13, worst absolute: 8.105e-15
```

⚠ Default dispatch. AVX-disabled the same run reads worst relative
**8.952e-13** and worst absolute 7.994e-15, so the two limbs are worse on
different CPUs: the ABSOLUTE bound to quote is the default run's 8.105e-15
(which the module docstring and the scale test do) and the RELATIVE figure
to quote is the disabled run's 8.952e-13. §F2.

Relative / absolute per cell. The NaN masks match exactly in all 32 runs
(asserted inside the measurement). The test bands the **absolute**
difference, for the reason §A2 gives.

### `0 < fires < n`, and the column is not constant

1,400 of 1,500 with 1,400 distinct values on each of the eight firing frames.

### A level shift is not a rescale, and it moves the column

```
+1            bars moved  1400, max |diff| 1.0148e-03
+50           bars moved  1400, max |diff| 2.4842e-02
+1e+06        bars moved  1400, max |diff| 4.7726e-02
```

---

## Gate E — attribution

**Gate E: SHIP.** Measured 2026-11-15 on **this module** by run
`is112-tf_dfa_100-da670816`
(`gate_e_overlap.py run --module pandas_ta.statistics.tf_dfa_100`), recorded
in `docs/gate_e_ledger.csv` by
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-15`.

| column | max \|ρ\| | against | set | n | per-frame max median | over | verdict |
|---|---|---|---|---|---|---|---|
| `TFDFA_100` | **0.09794533770230351** | `Swing_Range_pct` | manifest | 389,949 | **0.09958028098681403** | 89 frames, `Swing_Range_pct` | **SHIP** |

Under `r3-perframe-0.90` that is the `< 0.76` band on both limbs, so no
disclosure and no waiver (only STRUCK needs one). `verdict_pooled_only` is
the same SHIP, so neither limb carried the other, and unlike #111 **both
limbs read the same comparator**, `Swing_Range_pct`.

### §E1 — the run

```
run                is112-tf_dfa_100-da670816      measured 2026-11-15
module             pandas_ta.statistics.tf_dfa_100   fn tf_dfa_100
kwargs             {}  (defaults)                 end  none, no column excluded
frames             89 ALTPORT-1 BIST frames       pooled bars 398,849
comparators        687 = 329 compute_all + 358 manifest
degenerate         1 dropped: squeeze_SQZ_NO (manifest), constant
canary             AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal
versions           pandas 2.3.3, numpy 1.26.4
module sha1        654c61f85635bd4900a7b52f84fbbba12778fca0
pandas_ta src sha1 665b891c182f2675333f83fb9ba54a3508eda051
schema             r3-perframe-0.90
```

Per comparator set, the strongest in each:

```
set           max |rho|   against            n
manifest        0.0979    Swing_Range_pct    389,949
compute_all     0.0955    BB_BWidth          389,949
```

The module sha1 is the sha1 of `pandas_ta/statistics/tf_dfa_100.py` as the
harness imported it, so **the module file must not be edited in this receipt
session**: a one-character docstring change would move the hash and
`tests/test_gate_e_ledger.py` would read the row as a measurement of code
that no longer exists.

### §E2 — the screen's prototype figures, and why the agreement is expected

The 2026-10-24 catalog screen measured the PROTOTYPE expression over the same
89 frames and read max |ρ| 0.0979 vs `Swing_Range_pct`, per-frame max median
0.0996, with `mad_pct` 0.0958 and `BB_BWidth` 0.0955 behind it. This run
reproduces the comparator, its set, its rank order and all four figures to
four decimals:

```
                      screen (prototype)   this run (the module)
pooled max |rho|       0.0979              0.09794533770230351
  against              Swing_Range_pct     Swing_Range_pct (manifest)
  n                    389,949             389,949
per-frame max median   0.0996              0.09958028098681403
mad_pct                0.0958              0.09583975797143650
BB_BWidth              0.0955              0.09550381722685773
```

That is the agreement §A1 predicts — the module matches the prototype to
4.441e-16 with identical NaN masks on all ten synthetic frames, differing
only in the spelling of the final dot product — and **an expected agreement
is the easiest kind of row to copy over by mistake**, which is why
`tests/test_tf_dfa_100.py::test_the_gate_e_row_is_this_ports_own_measurement`
pins the row's own run id and not only its arithmetic.

⚠ The pooled `n` being identical, 389,949 on both, is *consistent with* the
two sharing a NaN mask on real data but is not proof of it: `n` is the
pairwise-complete count against one comparator, and §A1's mask measurement
was made on synthetic frames. What this run does establish about the mask is
in §C1: the 8,900 empty bars are `89 * 100` exactly.

### §E3 — what the verdict does not read

**The overlap is low everywhere, but not uniformly low per frame.** Across
the top five comparators the per-frame figures are

```
against            median   mean     max      min      >=0.90   >=0.80
Swing_Range_pct    0.0996   0.1099   0.3736   0.0003      0.0      0.0
mad_pct            0.0963   0.1036   0.3645   0.0013      0.0      0.0
BB_BWidth          0.0948   0.1013   0.3636   0.0015      0.0      0.0
ui                 0.0804   0.0891   0.3047   0.0017      0.0      0.0
natr               0.0836   0.1096   0.3871   0.0013      0.0      0.0
```

so the worst SINGLE frame of the five reaches 0.3871 (`natr`) and no frame
reaches any disclosure band on any of them.
⚠ `perframe.csv` covers the **top five comparators only**, so the other 682
are bounded by their pooled figures alone.

**What the column most resembles.** The whole top-25 spans 0.0433 .. 0.0979
— rank 25 is `natr_Chg_5d` — and 16 of the 25 are positive. By name, 12 of
the 25 read a range or a dispersion width (`Swing_Range_pct`, `mad_pct`,
`BB_BWidth`, `ui`, `natr`, `Stop_2ATR_pct`, `BB_Squeeze_Age`,
`squeeze_SQZ_OFF`, `squeeze_SQZ_ON`, `Pivot_Range_pct`, `pdist_pct`,
`natr_Chg_5d`) and 8 are a distance to an extreme (`dist_from_high_60`,
`Dist_to_BB_Upper_pct`, `Dist_from_High_252_pct`, `dist_low_60`,
`Dist_to_BB_Lower_pct`, `dist_from_high_20`, `dist_low_20`,
`ha_HA_high_DIST_PCT`); the remaining five are `ICHI_CLOUD_THICK`,
`Cloud_Thickness_pct`, `DMN`, `chop` and `Supertrend_Flip_Age`. The nearest
thing the engine has to this column is therefore volatility width, and it
resembles it at |ρ| ≤ 0.0979 — which is the point of the column, since §L3
measures it blind to the size of the returns altogether.

Three pairs inside that top-25 are near-duplicates of each other rather than
of this column: `natr` and `Stop_2ATR_pct` agree to all 16 digits
(0.08341328218741646), `ICHI_CLOUD_THICK` and `Cloud_Thickness_pct` to 11
(0.0684173278…), and `squeeze_SQZ_OFF` / `squeeze_SQZ_ON` are exact
negatives — the two comparator sets overlap in content, which is why 687 is a
count of columns and not of distinct quantities.

### §E4 — the fork-overlap stage, which is the screen's and not this run's

The 2026-10-24 screen also ran a stage-2 fork overlap (12 frames, scale-free
`Category` outputs at defaults): max |ρ| 0.1102 vs
`equal_highs_lows:EQH_DIST_5_5`, per-frame max median 0.1310. **That is not
Gate E** and was not re-run here; Gate E is the engine's 687 comparators over
the 89 frames, above.

⚠ That fork-overlap stage predates `lean_hurst_100` (#85), which is now
shipped and is the closest thing in the fork to this column. §L4 measures it
here, on synthetic frames.

---

## Gate F — suites

* `tests/test_tf_dfa_100.py`: **281 passed**, re-run in the receipt session
  (280 in the porting session, 277 before review round 2 added the three
  `test_the_infinity_fold_is_what_keeps_errstate_quiet` cases; the receipt
  session dropped `test_the_gate_e_row_is_owed_and_not_yet_recorded` and
  added `test_the_gate_e_row_is_this_ports_own_measurement` and
  `test_the_gate_e_run_closes_gate_c_on_real_data`, so the count moved by
  one).
* The same 281 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
  FMA3"`, via `python docs/measure_tf_dfa_100_cpu.py`, which refuses to run
  unless the four features really are off and prints the ones still enabled.
  One assertion had to be loosened for that run and the loosening is in the
  test: `LOG_BOX_CENTRED.sum()` is 2.220e-16 with the default dispatch and
  1.110e-15 without it, so the bound is now `len(BOXES) * eps * max|log s|`
  rather than a `1e-15` literal.
* Full suite: **3 failed, 10,274 passed, 85 skipped** (399 s), re-run on the
  tree this commit ships (the porting session read 3 failed, 10,266 passed,
  85 skipped). The three failures are
  the two CLAUDE.md clean-checkout breaks —
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` and
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  both of which CI deselects by name — and Gate E rows owed by seven OTHER
  indicators, `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife',
  'lumpiness', 'mtd_ret']`. `tf_dfa_100` is no longer in that list and is
  named in none of the three.
* ⚠ Pre-existing, outside this issue's scope and already recorded by #100,
  #101, #102, #103, #111 and #118: `pandas_ta/core.py:453` hands out the live
  `Category[name]` list and `core.py:692` removes names from it, so running
  `tests/test_wiring_accessors.py` BEFORE `tests/test_altport2_ports.py` in
  one process fails the pinned `CATEGORY_TOTAL`. Alphabetical collection — a
  plain `pytest -q` — hides it.

### §F2 — which figures move between the two dispatches

Every section above that `docs/measure_tf_dfa_100.py` produces was run twice
— §E and §C1 are not among them, being the single Gate E run of 2026-11-15 —
once with the default numpy dispatch and
once under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, which
is what the launcher re-runs port test modules under and the closest thing
here to a GitHub runner. This table is that comparison. It exists because
round 1 of the review caught a bound quoted from one dispatch and exceeded by
the other, and round 2 caught the same thing one section away.

| § | figure | default | AVX-512/AVX2/FMA3 off | worse | quoted where |
|---|---|---|---|---|---|
| A1 | bars differing from the prototype, ten frames | 3,209 | 3,161 | — (a count, not a bound) | §A1 and, as "about 3,200", the two docstrings |
| A1 | max abs vs the prototype, ten frames | 4.441e-16 | 4.441e-16 | same | module docstring, test item 2 |
| A1 | five-length table, `differ` | 1,270 / 1,250 / 1,228 / 1,204 / 1,044 | 1,290 / 1,220 / 1,246 / 1,146 / 1,085 | — (counts) | §A1 only |
| A1 | five-length table, length-20 ceiling | 4.441e-16 | 3.331e-16 | **default** | §A1 only; the 32/64/100/250 ceilings do not move |
| A2 | loop oracle, worst abs | 1.998e-15 | 1.665e-15 | **default** | test item 2 (2.0e-15) |
| A2 | loop oracle, worst rel | 1.006e-13 | 1.254e-14 | **default** | §A2 only |
| A3 | polyfit oracle, worst abs | 2.887e-15 | **3.109e-15** | **AVX off** | test item 2 and the polyfit test (3.109e-15) |
| A3 | polyfit oracle, worst rel | 7.970e-15 | **1.271e-14** | **AVX off** | §A3 only |
| A8 | centring, max abs | 1.998e-15 | 1.554e-15 | **default** | `_dfa_alpha`'s comment |
| A8 | centring, `jump` max rel | 4.538e-14 | **1.302e-13** | **AVX off** | §A8 only |
| D | inexact rescale, worst abs | **8.105e-15** | 7.994e-15 | **default** | module docstring, the scale test |
| D | inexact rescale, worst rel | 7.295e-13 | **8.952e-13** | **AVX off** | §D and the scale test, both naming both |
| L3 | return rescale, x2\*\*60 | 7.772e-15 | **8.771e-15** | **AVX off** | module docstring, ML contract |
| L3 | drift, max abs | 1.443e-15 | **1.554e-15** | **AVX off** | module docstring |
| L3 | return rescale, x0.5 | 1.332e-15 | 1.221e-15 | **default** | §L3 only |
| L3 | return rescale, x2 | 1.332e-15 | 1.221e-15 | **default** | §L3 only |
| L3 | return rescale, x-0.1 | 1.443e-15 | 1.332e-15 | **default** | §L3 only |
| Z | the `@` variant's budget column | unstable at 1 row per chunk only | unstable at 1, 2, 5, 7 and 8 rows per chunk | **AVX off** | §Z and §Z2 |
| Z2 | `alpha matmul` rows differing from the 1-row run | 7 of 60 | 8 of 60 | — (a count, and the point is that it is not 0) | §Z2 only |

What was compared and came back equal, digit for digit, on both dispatches:
**§A4, §A5, §A5b, §A6, §A7** (both of its tables), **§C**, **§D**'s
bit-identity, fire counts and level-shift limbs, **§G** (every line,
including the two block-constant constructions), **§L**'s distribution
table, **§L2**, **§L4**, **§L5**, **§W**, **§Z**'s `peak MB`, and **§Z2**'s
fourteen other steps. **§B** and **§Z**'s timings are the two that were not
re-run under the disabled dispatch: §B is a two-minute run of booleans with
no last-bit figure in it, and §Z's `seconds` does not reproduce under the
SAME dispatch (see §Z).

⚠ What this table is, exactly: every BOUND quoted anywhere in this repo for
this column, plus every headline figure of a section, measured on both
dispatches. It is NOT every cell of every table — the per-cell last-bit
figures inside §A1, §A2, §A3, §A8, §D and §L3 move as well, and those six
sections carry an in-place ⚠ saying so. The rule a maintainer needs is the
one above the table: a bound is quoted at its worse dispatch, and a count
that moves is flagged where it appears.

**Wherever this document or a docstring states a BOUND, it states the worse
of the two columns above**, and says which dispatch that is. The counts that
move are flagged where they appear instead of being quoted as if stable.
This section is the one round 2 of the review asked for and round 3 filled
in: five rows above were missing from the first draft, which claimed
"everything else reproduced" without running §Z2, §A1's second table, §A2's
relative column, §A8's `jump` or §D's relative column.

---

## §G — guards

One bad close, on a 1,500-bar walk:

```
     value     at  newly empty  moved before
       nan    200          101             0
       nan    600          101             0
       nan   1000          101             0
       inf    200          100             0
       inf    600          100             0
       inf   1000          100             0
      -inf    200          100             0
      -inf    600          100             0
      -inf   1000          100             0
         0    200          100             0
         0    600          100             0
         0   1000          100             0
    1e-310    200          100             0
    1e-310    600          100             0
    1e-310   1000          100             0
```

**101 for a NaN and 100 for the rest**, and the asymmetry is worth knowing: a
NaN close spoils the return INTO that bar and the one OUT of it, while an
infinite close leaves `close[T+1] / inf - 1 = -1`, a perfectly finite return,
and a zero close leaves `0 / close[T-1] - 1 = -1`. Nothing before the bad bar
moves, in any of the 15 runs.

**Can a window be blanked without its returns being equal?** On paper yes —
`mean_square` is the mean over the boxes of ONE size, so any window whose
profile is exactly straight inside every box of one size would go. Two
constructions were tried and NEITHER reaches it:

```
4-block random   bars  1600 windows  1500 fires  1500 blank     0  distinct returns  838
4-block dyadic   bars   241 windows   141 fires   141 blank     0  distinct returns    2
```

The second holds the returns at exactly 1.0 and exactly 3.0 in aligned
four-bar blocks (a price path whose ratio is 2 for four bars and 4 for the
next four), so the blocks really are bit-equal — and the window still fires,
because the window MEAN is not dyadic and the cumulative sum of the centred
returns is therefore not exactly straight. So the only blanking measured
here is the all-equal window, and that is what the docstrings claim; the
wider case is left open rather than asserted either way.

**The `inf` fold.** `r = np.where(np.isfinite(r), r, np.nan)` is the line
that keeps `errstate(all="raise")` quiet: `inf - inf` at the centring step
is NaN WITH the invalid flag. Pinned by
`test_the_infinity_fold_is_what_keeps_errstate_quiet`, which runs the
shipped module on a frame carrying an infinite return under
`errstate(all="raise")` and requires a mutant with the fold deleted to raise
`FloatingPointError` on the same frame — and requires the two to be
bit-equal with the error state off, because the fold must not change a
value.

A negative close is a PRICE and not a gap: the column still fires on 1,400
bars and 101 of them move. Degenerate frames, under `errstate(all="raise")`:

```
all-nan         fires     0 of  1500
all-zero        fires     0 of  1500
all-negative    fires  1400 of  1500
flat            fires     0 of  1500
x2 ramp         fires     0 of   200
```

No floating-point error is reachable on any of the ten frames. The shortest
input that produces a value is `length + 1` closes (one reading); at `length`
closes the module returns `None`. A `length` below `MIN_LENGTH` (20) falls
back to the default: `None`, 0, 1 and 19 all give `TFDFA_100`, and 20 gives
`TFDFA_20`. The input series is not mutated.

---

## §L — what the column reads

```
frame                mean        sd       p01       p50       p99       min       max
walk               0.6471    0.1201    0.3930    0.6444    0.9305    0.3075    1.0620
trend              0.6322    0.1102    0.3865    0.6288    0.8905    0.2851    1.0213
range-bound        0.6427    0.1114    0.3767    0.6413    0.8891    0.2903    0.9948
grid               0.6172    0.1265    0.3364    0.6127    0.9042    0.2812    1.0249
heavy-tailed       0.6455    0.1338    0.3692    0.6354    1.0126    0.2259    1.3612
jump               0.7218    0.1967    0.4067    0.7054    1.3495   -0.2197    2.3288
persistent         1.0598    0.1660    0.6892    1.0580    1.4361    0.5154    1.5602
mean-reverting     0.2978    0.0682    0.1663    0.2913    0.4744    0.0815    0.5504
```

### §L2 — the ordering the exponent is for

`mean-reverting 0.2913 < walk 0.6444 < persistent 1.0580`, by median.

### §L3 — blind to the size and the sign of the returns

Scaling the whole return window by `k` multiplies every `F(s)` by `|k|`,
which shifts every `log F(s)` by the same constant and cancels in the slope.
Measured on 500 windows sampled from a synthetic 1,500-bar walk (no real
data appears anywhere in this document), through the module's own
`_dfa_alpha`
(re-checked bit-equal to the shipped column first):

```
x-1         bit-identical: True, max |diff| 0.000e+00
x0.5        bit-identical: False, max |diff| 1.332e-15
x2          bit-identical: False, max |diff| 1.332e-15
x1.15292e+18 bit-identical: False, max |diff| 7.772e-15
x3.7        max |diff| 1.443e-15
x-0.1       max |diff| 1.443e-15
```

⚠ **The last-bit figures here move with the CPU dispatch, and this is one of
six sections where they do — §F2 is the list.**
`python docs/measure_tf_dfa_100_cpu.py L`, i.e. with `AVX512F AVX512_SKX
AVX2 FMA3` disabled, reads x0.5 1.221e-15, x2 1.221e-15, **x2\*\*60
8.771e-15**, x3.7 1.443e-15 and x-0.1 1.332e-15. x-1 is bit-identical under
both. So the invariance budget to quote is **8.771e-15**, not the 7.772e-15
of the default dispatch; the module docstring and
`docs/MLCompanionContract.md` state 8.771e-15 for that reason, and the test
bands it at 1e-12.

⚠ x-1 is bit-identical and x2 is not, which looks backwards for a binary
factor. It is the logarithm: `log(4m)` is not `log 4 + log m` in floating
point, while negating the window leaves `F(s)` on exactly the same numbers.

A constant added to every return — a drift — is removed by the per-box
detrend (§A8): max |diff| 1.443e-15 at +0.001, 1.110e-15 at +0.05 and
1.110e-15 at +1.0 with the default dispatch, and 1.554e-15 at all three with
AVX-512/AVX2/FMA3 disabled. **So this is not a volatility measure and not a
momentum measure: it carries neither the size, the sign, nor the drift of the
returns.**

### §L5 — what it is NOT blind to: the order

```
permutation   max |diff| 0.5157  median |diff| 0.1164
time reversal max |diff| 0.3698  median |diff| 0.0870
rotation      max |diff| 0.4282  median |diff| 0.0879
```

⚠ Worth stating because the fork's spectral features (`tf_centroid_20`,
`tf_spec_entropy_64`) ARE phase-blind and this one is not: a circular
rotation splices the window's two ends together and the profile jumps there.

### §L4 — against the fork's own persistence columns

Spearman |ρ| per frame, synthetic frames only.

```
comparator                     walk          trend    range-bound           grid   heavy-tailed           jump     persistent mean-reverting
lean_hurst_100               0.0189         0.0313         0.1407         0.1892         0.1529         0.0981         0.0679         0.0206
g191_165                     0.1640         0.0231         0.0585         0.1374         0.0371         0.0118         0.0432         0.0219
ts_ac1_60                    0.3578         0.3390         0.2963         0.4164         0.2605         0.3432         0.3681         0.4808
ts_aggac_60                  0.0493         0.1297         0.1710         0.1281         0.0141         0.0444         0.0114         0.0875
ts_cid_ce_20                 0.2612         0.1222         0.1293         0.1948         0.1046         0.2266         0.1884         0.2201
lean_momersion_20            0.1805         0.0406         0.0905         0.0505         0.1249         0.1374         0.1251         0.1849
```

The largest overlap anywhere in the table is **0.4808** (`ts_ac1_60` on the
mean-reverting frame), far below the 0.90 restatement line.
`lean_hurst_100` — the fork's other persistence exponent, and the one most
likely to be a restatement — reads 0.0189 .. 0.1892. The two estimate the
same idea through different machinery (lagged-difference standard deviations
over lags 2..20 against detrended fluctuations over boxes 4..10) and they do
not agree on these frames.

⚠ Synthetic frames, eight of them, and this is NOT Gate E: Gate E is the
engine's 687 comparators over 89 real BIST frames, and issue-solver runs it.

---

## §Z — cost, and the dot product

```
length     bars         budget  seconds   peak MB
   100   400000        2097152     3.79      78.0
   100   400000  1099511627776     5.37    1369.8
   250   400000        2097152     9.28      77.3
   250   150000        2097152     3.54      73.3
   250   150000  1099511627776     4.90    1265.4
```

⚠ `seconds` is ONE wall-clock run on the author's machine and does not
reproduce — a re-run during review read 3.83 / 5.51 / 12.18 / 4.64 / 7.50 for
the same five rows. `peak MB` is `tracemalloc` and does reproduce exactly.

Each row says how many bars it ran on. The two unchunked rows are not the
same size: `length` 250 unchunked on 400,000 bars traced 3,377.6 MB on the
first run here and was then OOM-killed on a repeat, so that comparison runs
on 150,000 bars.

### The budget cannot change a value — and why the line is a sum

Default dispatch:

```
      budget rows/chunk  shipped `sum`  the `@` variant
           1          1           True            False
          64          1           True            False
         100          1           True            False
         199          1           True            False
         200          2           True             True
         299          2           True             True
         500          5           True             True
         600          6           True             True
         700          7           True             True
         800          8           True             True
         999          9           True             True
  1000000000   10000000           True             True
```

`python docs/measure_tf_dfa_100_cpu.py Z`, with `AVX512F AVX512_SKX AVX2
FMA3` disabled:

```
      budget rows/chunk  shipped `sum`  the `@` variant
           1          1           True            False
          64          1           True            False
         100          1           True            False
         199          1           True            False
         200          2           True            False
         299          2           True            False
         500          5           True            False
         600          6           True             True
         700          7           True            False
         800          8           True            False
         999          9           True             True
  1000000000   10000000           True             True
```

**The shipped `sum` is True in all 24 cells.** The `@` variant is not, and
the disabled dispatch is far worse than the default one: unstable at 1, 2, 5,
7 and 8 rows per chunk while stable at 6 and at 9.

### §Z2 — which step is sensitive to the block shape

Every step run on the whole block and again on a one-row block, compared on
the same row, 60 rows of a walk:

```
step              rows that differ from the 1-row run
profile                                 0 of 60
slope s=4                               0 of 60
meansq s=4                              0 of 60
slope s=5                               0 of 60
meansq s=5                              0 of 60
slope s=6                               0 of 60
meansq s=6                              0 of 60
slope s=8                               0 of 60
meansq s=8                              0 of 60
slope s=10                              0 of 60
meansq s=10                             0 of 60
log_f                                   0 of 60
centred                                 0 of 60
alpha matmul                            7 of 60
alpha sum                               0 of 60
```

**One step, and it is the prototype's `@`.** A `(rows, 5) @ (5,)` product
dispatches differently at one row, and the last bit moves. The other
fourteen steps — the cumulative sum, each box's slope, each mean square, the
log, and the shipped `alpha sum` — read 0 of 60 here and 0 of 60 with
AVX-512/AVX2/FMA3 disabled. ⚠ The `alpha matmul` count itself is a count of
last bits and moves: **8 of 60** on that dispatch rather than 7 (§F2). What
does not move is that it is non-zero while every other step is zero.

⚠ **How reachable is it, honestly — and this paragraph has been wrong
twice.** It first said `@` needs `length > CHUNK_VALUES` (2,097,152), which
was the wrong inequality; round 3 corrected the algebra to
`length > CHUNK_VALUES // 2` (1,048,576) and round 4 pointed out that the
corrected sentence had still never been RUN on the other dispatch. Run, it
is not a threshold at all: with AVX-512/AVX2/FMA3 off the `@` variant is
unstable at 1, 2, 5, 7 and 8 rows per chunk and stable at 6 and 9, which is
not monotone in the row count and so admits no "needs a window longer than
N bars" rule. The honest statement is the empirical one: on at least one
dispatch `@` is unstable at every swept row count up to 8, which
`CHUNK_VALUES // length <= 8` reaches, i.e. any `length` above
`CHUNK_VALUES // 9 = 233,016` — still far beyond any frame anyone will run,
so the prototype is not wrong in practice, but the reason is "no real frame
is a quarter of a million bars per window", not "the kernel is stable above
two rows".

What the sum spelling buys is that the question does not have to be asked
at all: the shipped arithmetic is a pure numpy reduction over five numbers,
it touches no BLAS, and a bar's value provably cannot depend on how many
bars came after it. That property is asserted
directly in `test_the_arithmetic_does_not_depend_on_the_block_shape`, which
is phrased about the shipped code and not about `@` — `@`'s behaviour is a
property of the machine's BLAS and does not belong in a test suite that has
to pass on a GitHub runner.

---

## §M / §W — the wiring the generated docs carry

Five touch points: `pandas_ta/statistics/tf_dfa_100.py`,
`pandas_ta/statistics/__init__.py`, `Category` in `pandas_ta/__init__.py`,
the `df.ta.tf_dfa_100()` accessor in `pandas_ta/core.py`, and
`tests/test_tf_dfa_100.py`. `README.md` moves 349 -> 350 registered, 357 ->
358 callable and `statistics (51)` -> `(52)`;
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` moves 349 -> 350;
`docs/MLCompanionContract.md` moves 694 -> 695 tagged columns and 333 -> 334
`SF`; `docs/IndicatorDictionary.md` is regenerated.

The dictionary truncates the docstring's first paragraph at
`d[:150].rsplit(" ", 1)[0]`. This one is 144 characters with **6 characters
of slack** — tight on purpose: a longer sentence fails
`test_the_docstring_first_paragraph_survives_the_dictionary_cut` instead of
silently losing its end in the table. Both disclosures are inside the cut,
which is what the six characters were spent on: the dictionary row is the
first thing CLAUDE.md sends a reader to, and the first draft spent them on
the word "measured" and let "Unbounded" fall outside.
