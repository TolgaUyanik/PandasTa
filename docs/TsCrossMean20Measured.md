# TS-CROSS-MEAN-20 — `ts_cross_mean_20`, measured

PandasTa issue [#100](https://github.com/TolgaUyanik/PandasTa/issues/100)
(owner's local tracker `docs/issues/099-ts-cross-mean-20.md`, gitignored).
Parent: #31 ALPHASETS, screen of 2026-10-24.

Module `pandas_ta/statistics/ts_cross_mean_20.py`, one column
`TS_CROSS_MEAN_20`, tests `tests/test_ts_cross_mean_20.py` (205),
measurement script `docs/measure_ts_cross_mean_20.py`.

Everything below was produced by

```sh
python docs/measure_ts_cross_mean_20.py          # or: ... A B C D G O Z
python docs/measure_ts_cross_mean_20_cpu.py      # the same tests, AVX512/AVX2/FMA3 off
```

on numpy 1.26.4 / pandas 2.3.3. Where a number depends on the last bits of
a generated frame it is banded in the tests and quoted here as the figure
this machine produced. **No sentence here was written before its run.**

Unless a line says otherwise, a "frame" is one of nine 1,500-bar synthetic
closes — walk, tick-rounded, ar1+, ar1−, heavy-tailed, right-skewed,
left-skewed, two-point, trending — each of which fires on
**1,481 of 1,500** bars (20 closes, so the first value lands at bar 19).

---

## 0. What the column is, in one paragraph

`TS_CROSS_MEAN_20` counts how many of the 19 adjacent pairs inside a 20-bar
window of **log closes** sit on opposite sides of that window's own mean log
close. It is tsfresh's `number_crossing_m(x, m)` with `m` set to `mean(x)`.
A monotone window reads **1** whatever its slope; a perfectly alternating
one reads **19**. So it is a choppiness / mean-reversion-frequency reading
over the price path itself and not over the returns. It is the only
tsfresh port in this fork whose WINDOW holds a logarithm of the price
(`ts_perment_20` and `ts_binent_20` also call `np.log`, on probabilities,
which is a different thing): eight of them
(`ts_above_mean_20`, `ts_binent_20`, `ts_c3_20`, `ts_cid_ce_20`,
`ts_kurt_60`, `ts_ac1_60`, `ts_aggac_60`, `ts_medskew_20`) read returns,
and two (`ts_peaks_20`, `ts_perment_20`) read raw closes. That difference
is not cosmetic — it is why §3's D0 exists.

---

## 1. Gate A — correctness against the source formula

### A0 — what the oracle actually is

```
tsfresh is NOT installed here: No module named 'tsfresh'
```

`tests/test_ts_cross_mean_20.py::test_tsfresh_is_not_installed_here` records
that, so "checked against tsfresh" cannot creep in later. The formula under
test is issue #100's line —
`number_crossing_m(x, m=mean) on 20 log closes` — plus the published
definition of `feature_calculators.number_crossing_m`:

```python
positive = x > m
return np.where(np.diff(positive))[0].size
```

What tsfresh does that neither of those states (how it treats NaNs) is
**unverified here**. The window length 20 and the level `m = mean` are the
issue's own choices; the source function takes any level.

### A1 — the source applied window by window

A retype of `number_crossing_m` handed one window at a time, sharing no code
with the module (a Python loop, `np.mean`, and the source's own
`np.where(np.diff(positive))[0].size`). A count is either right or wrong, so
this is **bit-equality** and not a tolerance.

| frame | masks identical | shared | bit-equal | max difference |
|---|---|---|---|---|
| ar1+ | yes | 1,481 | 1,481 | 0 |
| ar1− | yes | 1,481 | 1,481 | 0 |
| heavy-tailed | yes | 1,481 | 1,481 | 0 |
| left-skewed | yes | 1,481 | 1,481 | 0 |
| right-skewed | yes | 1,481 | 1,481 | 0 |
| tick-rounded | yes | 1,481 | 1,481 | 0 |
| trending | yes | 1,481 | 1,481 | 0 |
| two-point | yes | 1,481 | 1,481 | 0 |
| walk | yes | 1,481 | 1,481 | 0 |

### A2 — against a `math.fsum` scalar loop

A different logarithm (`math.log`, the C library's, not numpy's ufunc) and a
sum that is exact up to one final rounding: bit-equal on 1,481 of 1,481 bars
of the walk, the tick-rounded frame and the heavy-tailed frame, masks
identical.

### A3 — against an oracle that rounds nowhere near a double

This column's arithmetic can get exactly one thing wrong: decide which side
of the mean a log close falls on. Only an oracle far more precise than a
double can see that, so the check is `decimal.Decimal.ln()` at **60
significant digits** — about 44 beyond a double — with the mean and every
comparison decided at that precision.

| frame | masks identical | shared | bit-equal |
|---|---|---|---|
| walk | yes | 1,481 | 1,481 |
| tick-rounded | yes | 1,481 | 1,481 |
| two-point | yes | 1,481 | 1,481 |
| trending | yes | 1,481 | 1,481 |

### A3b — the same oracle where the cancellation is worst

`log c − mean` cancels hardest when `|log c|` is large and the window's
spread is tiny, i.e. a quiet frame at a price far from 1.0.

| frame | median log spread | floor | fired | bit-equal |
|---|---|---|---|---|
| price 1e+6, σ 1e-7 | 5.641e-07 | 1.257e-11 | 581 | 581/581 |
| price 1e+6, σ 1e-9 | 5.641e-09 | 1.257e-11 | 581 | 581/581 |
| price 1e-6, σ 1e-7 | 5.641e-07 | 1.257e-11 | 581 | 581/581 |

**Over the 5,924 + 1,743 windows A3 and A3b put to the 60-digit oracle,
float decided no comparison the wrong way.**

⚠ That number is the 60-digit oracle's alone, and the distinction is not
pedantry. A1 and A2 compare a double pipeline against another double
pipeline: if the double logarithm of a close sits on the wrong side of
the double mean, the module and both of those checks put it there
together. Their 13,329 and 4,443 windows measure that the module's
*formula* is right, not that its *comparisons* are. Five of the nine
frames — ar1+, ar1−, heavy-tailed, left-skewed and right-skewed — have
never been put to an exact oracle.

⚠ It is a scope and not a guarantee, and G3b is where the scope ends: on
the ramped-volatility frame built for that section, **one admitted window
in 351** — in the `[4096, 16384)` bucket at price 100, just above the
floor — is miscounted. The floor refuses the regime where float is badly
wrong; it does not make the arithmetic exact. See G3b.

### A4 — the range, which is [1, 19] and NOT [0, 19]

Derivation: the window mean lies strictly between the window's own minimum
and maximum unless every value is equal (and an equal window is refused by
the floor). So at least one close is above the mean and at least one is
not, and the boolean sequence must switch at least once. **A reading of 0 is
arithmetically impossible**, and so is 20.

Counted, over every window of every frame:

| frame | min | max | distinct | fired |
|---|---|---|---|---|
| ar1+ | 1 | 10 | 10 | 1,481 |
| ar1− | 1 | 14 | 14 | 1,481 |
| heavy-tailed | 1 | 10 | 10 | 1,481 |
| left-skewed | 1 | 12 | 12 | 1,481 |
| right-skewed | 1 | 12 | 12 | 1,481 |
| tick-rounded | 1 | 13 | 13 | 1,481 |
| trending | 1 | 11 | 10 | 1,481 |
| two-point | 1 | 16 | 16 | 1,481 |
| walk | 1 | 13 | 13 | 1,481 |

Minimum over all nine: **1**. Maximum over all nine: **16** — the two-point
frame. Both ends of the derived range are attained by construction instead:
a 40-bar monotone frame reads **1** on every window, and a frame
alternating between two log levels reads **19** on every window.

And the unguarded spelling *does* emit the impossible value: on a 300-bar
flat frame it reports **281 windows, all reading 0.0**. The reason is
arithmetic rather than conceptual — numpy's windowed sum of 20 copies of
`log(100)` divided by 20 is `4.60517018598809`, where the value itself is
`4.605170185988091`. Every close then sits on the same side of that
"mean", there is no switch, and the count is 0.

### A5 — four readings the one-line formula leaves open, priced

On the 1,500-bar walk.

| reading | Spearman | bit-equal | max difference |
|---|---|---|---|
| log closes **vs** raw closes | +0.990557 | 1,443/1,481 | 2 |
| 20 log closes **vs** 20 simple returns | +0.147259 | 35/1,481 | 14 |
| `>` **vs** `>=` | +1.000000 | 1,481/1,481 | 0 |
| `m = mean` **vs** `m = 0` on log returns | +0.176569 | 27/1,481 | 14 |
| the raw count **vs** the share `/(n−1)` | +1.000000 | — (exact rescaling) | — |

* **Log closes**, the issue's wording, so the threshold is the window's
  GEOMETRIC mean close. On the raw closes it is the arithmetic mean, a
  higher line: close but not the same column.
* **20 CLOSES, not 20 returns**, so the first value lands at bar 19 and not
  bar 20. On returns it is a different question entirely.
* **The output is the raw COUNT**, the source function's own return value.
  Dividing by `length − 1` is an exact rescaling and rank-identical, so it
  is the one choice a rank miner cannot see; the count was kept because it
  is what `number_crossing_m` returns and what the screen prototype
  measured.
* **The comparison is STRICT**, the source's `>`. See A5b.

### A5b — the strict comparison, pinned by construction

No frame here can price `>` against `>=`: a tie with a 20-way average does
not happen by accident, and the count is **0 exact ties in 88,860
window/close pairs** of three frames.

At `length` 3 a tie cannot separate the two spellings *at all*, and that is
a derivation rather than an observation: a tied value is not above the mean,
so for the two to disagree both its neighbours would have to be above — and
then they would sum to more than twice the tie, which the mean forbids.

`length` 4 is the smallest window where they can disagree, and the
construction is integral: closes `[a, k, b, d]` with `a·b·d = k³` have
`log(k)` as the exact mean of their four logs. Searching that family for
one where the mean is also **bit-equal** to `log(k)` gives

```
closes [12, 6, 18, 1]:  strict > reads 3,  >= reads 1
```

(12·18·1 = 216 = 6³.) `tests/test_ts_cross_mean_20.py` asserts the tie
itself (`x[1] == x.sum() / 4`) before asserting the two readings, so the
test cannot quietly stop testing anything.

### A7 — against the screen prototype: the same column, the same mask

The prototype is `docs/issues/screen/ind_screen.py`, candidate
`ts_cross_mean_20`: `roll(np.log(c), 20, w_crossings_mean)` with
`w_crossings_mean(W) = (s[:, 1:] != s[:, :-1]).sum(1)` over
`s = W > W.mean(1, keepdims=True)`. Same windows, same mean, same strict
comparison, same first fired bar — and, unlike the sibling ports, the same
spelling of the mean, so the two are expected to be bit-equal and are.

| frame | masks identical | shared | bit-equal | Spearman |
|---|---|---|---|---|
| all nine | yes | 1,481 | 1,481 | 1.000000 |

They part company **only** where a guard fires:

* 300-bar flat frame: this port reports 0 bars, the prototype 281, all
  reading the impossible 0.0;
* 300-bar constant-rate ladder: **both** report 281 bars, all reading 1.0.
  A ladder is a legitimate window here (its log closes are monotone), which
  is a real difference from the sibling return-based ports, where a ladder
  has constant returns and is refused;
* one NaN close at bar 200 of a 1,500-bar walk: the masks differ on **20
  bars** (this port empties 39 in total — 19 warm-up plus the 20 windows
  holding the bad close — where the prototype empties 19 and reads 0.0 on
  the other 20, because a NaN mean makes every comparison False).

Because Gate E's statistic is a Spearman over the bars where both fire, the
screen's figures were expected to carry over, and §E says they did: the run
on this module reads 0.5500 / 0.5495 against the prototype screen's
0.5500 / 0.5495.

---

## 2. Gate B — causality, by mutant

Each mutant is `importlib`-read from the shipped file and `exec`'d in
memory, so it is the real source with one line changed. The blind sweep
`_caught` replaces every close from bar J on with another frame's and looks
for any bar **before** J that moved; 37 offsets (40, 80, …, 1,480), three
frames.

**The real module leaks 0 of 37** on the walk, the tick-rounded frame and
the heavy-tailed frame, and 0 of 37 at `length` 5, 60 and 250 — where the
first fired bar is 4, 59 and 249 respectively.

| mutant | what it does | heavy-tailed | tick-rounded | walk |
|---|---|---|---|---|
| `back_date_full` | writes the values from bar 0 | 37 | 37 | 37 |
| `back_date_two` | writes them two bars early | 32 | 31 | 35 |
| `forward_window` | rolls the log closes one bar forward | 28 | 25 | 29 |
| `forward_close` | rolls the closes before the log | 28 | 25 | 29 |
| `future_mean` | the comparison level comes from the next window | 34 | 19 | 27 |

All five are LIVE on all three frames. `forward_close` and
`forward_window` score identically because rolling the closes before the
logarithm and rolling the log closes after it are the same edit in two
places; both are kept so that both **lines** are guarded.

### The sixth mutant: the floor's own index, and where the blind sweep fails

Rolling the floor's `hi`/`lo` by one window makes bar T's NaN mask read
window T+1 — a genuine look-ahead. On a clean frame it is **not merely
invisible: it is DEAD.** The floor reports on every window of a clean
frame, so the rolled mask reports too and the mutant's output is
bit-identical to the real module's. Measured on all three frames:
`live=False`, zero moved bars, sweep caught 0 of 37.

What *can* move is derived rather than guessed:

> Bar T's COUNT reads closes T−19..T, so a splice at J cannot touch it for
> T < J. Window T+1 holds a close at or after J only when T+1 ≥ J. So
> **bar J−1 is the only bar before J that can ever move**, and it moves
> only when the floor's verdict on window J flips.

A probe therefore has to put a floor-emptied window at exactly each offset.
The designed frame does: a walk in which the 20 closes ending at each of
the 37 offsets are held constant.

| frame | bars the floor empties | unguarded reports there | real module | shifted-floor mutant |
|---|---|---|---|---|
| designed (20-bar halt at each offset) | 37 | 37, all reading 0.0 | 0 of 37 | **37 of 37** |
| obvious (25-bar halts every 40 bars) | 138 | 138, all reading 0.0 | 0 of 37 | **3 of 37** |

and at the first offset (J = 40) the bar the mutant moves is exactly
**[39]**, which is J−1, with the real module moving none. The contrast is
the point: the obvious probe looks more thorough — 138 emptied bars against
37 — and proves almost nothing, because its halts start at bars 40, 105,
170, … while the sweep's offsets are multiples of 40, so hardly any offset
lands on a window the floor empties.

---

## 3. Gates C and D

### C — reachability (synthetic; the real-data counts are §E1)

| frame | fired | of | non-zero | distinct | min | max | modal (n) |
|---|---|---|---|---|---|---|---|
| ar1+ | 1,481 | 1,500 | 1,481 | 10 | 1 | 10 | 1 (656) |
| ar1− | 1,481 | 1,500 | 1,481 | 14 | 1 | 14 | 5 (263) |
| heavy-tailed | 1,481 | 1,500 | 1,481 | 10 | 1 | 10 | 1 (506) |
| left-skewed | 1,481 | 1,500 | 1,481 | 12 | 1 | 12 | 3 (374) |
| right-skewed | 1,481 | 1,500 | 1,481 | 12 | 1 | 12 | 3 (366) |
| tick-rounded | 1,481 | 1,500 | 1,481 | 13 | 1 | 13 | 1 (340) |
| trending | 1,481 | 1,500 | 1,481 | 10 | 1 | 11 | 1 (791) |
| two-point | 1,481 | 1,500 | 1,481 | 16 | 1 | 16 | 1 (261) |
| walk | 1,481 | 1,500 | 1,481 | 13 | 1 | 13 | 1 (339) |
| flat (300 bars) | **0** | 300 | — | — | — | — | — |
| ladder (300 bars) | 281 | 300 | 281 | 1 | 1 | 1 | 1 (281) |

`0 < fires < n` on every frame that fires, no zeros, and never a constant
column except on the ladder, where 1 is the right answer on every window.
The distinct-value counts are banded in the tests (5 ≤ n ≤ 19) rather than
pinned, because they depend on the last bits of a generated frame.

It is a **state, not an event flag** — neighbouring windows share 19 of
their 20 closes. Autocorrelation on the walk: **+0.8519** at lag 1, +0.3000
at lag 5, −0.0481 at lag 10, −0.0172 at lag 20.

### D0 — ⚠ nothing here is bit-identical BY CONSTRUCTION

The fork's eight RETURN-based tsfresh ports read price RATIOS, where
`8a / 8b` is the same double as `a / b` and a ×2^k rescale cancels exactly.
The two that read raw closes — `ts_peaks_20` and `ts_perment_20` — read
only the ORDER of those closes (`ts_peaks_20.py:56`: "Only comparisons are
read: no difference, no ratio, no sum"), which a rescale cannot change
either. **This column takes a LOGARITHM, and `log(8p)` is not
`log(8) + log(p)` in binary floating point.** Every rescale perturbs the
log closes in their last bits, so every bit-equality below is a
MEASUREMENT with a measured margin behind it (D3), not a guarantee. It is
the only port in the family where that sentence is needed.

### D1 — ×8 and ×64

Bit-equal on **1,481 of 1,481** bars with identical masks, on each of the
nine frames, at both ×8 and ×64. At other lengths on the walk: 1,498/1,498
at `length` 3, 1,496/1,496 at 5, 1,441/1,441 at 60, 1,251/1,251 at 250.

### D2 — ×10, ×3.7, ×0.1 and ×1.0000001

Not exact even nominally, and bit-equal anyway: 1,481/1,481 with identical
masks on all nine frames at every one of the four factors.

### D3 — the margin that makes D1 and D2 hold

A count moves only when a perturbation reorders a log close and its own
window mean, so the quantity to measure is `min |x − mean| / max|x|` over
every window.

| frame | smallest gap | median gap |
|---|---|---|
| ar1+ | 9.755e-07 | 1.254e-02 |
| ar1− | 9.506e-08 | 3.449e-03 |
| heavy-tailed | 8.923e-07 | 4.003e-03 |
| left-skewed | 2.249e-07 | 2.226e-03 |
| right-skewed | 1.903e-07 | 2.583e-03 |
| tick-rounded | 1.766e-07 | 3.554e-03 |
| trending | 4.771e-08 | 2.527e-03 |
| two-point | 5.453e-06 | 2.721e-03 |
| walk | 4.108e-07 | 3.555e-03 |

Over the **199,981 windows of a 200,000-bar walk** the smallest gap is
**6.927e-10**, against an ulp of 2.2e-16: six orders of magnitude. On that
frame ×8 and ×10 are bit-equal on all 199,981 windows, and on a 200,000-bar
tick-rounded copy of it (where closes repeat, so near-ties are commoner)
×8, ×64 and ×10 are bit-equal on all 199,981 too.

### D4 — stronger than a rescale: any monotone power of the price

The count reads only the ORDER of the log closes against their own mean,
and `x → a·x` preserves that order for `a > 0` and reverses all of it for
`a < 0` — which leaves the number of SWITCHES untouched. Measured on the
walk, bit-equal on 1,481 of 1,481 bars with identical masks and Spearman
1.000000 in each case:

| map | log closes become | bit-equal |
|---|---|---|
| `price ** 2` | `2·x` | 1,481/1,481 |
| `price ** 0.5` | `0.5·x` | 1,481/1,481 |
| `1 / price` | `−x` | 1,481/1,481 |

⚠ The invariance is exact in the reals and a MEASUREMENT in doubles, on
the same grounds as D0: `log(p**a)` is no more exactly `a · log(p)` than
`log(8p)` is `log(8) + log(p)`, so a near-tie could in principle reorder.
Three maps on one frame were measured; "any monotone power" is the
theorem, not the run.

---

## 4. The guards, each priced in both directions

There are two, and only two: a bad-close mask and a relative floor. The
derivation in G5 is why there is no third.

### G1 — what the floor costs

**0 bars** on each of the nine clean frames: the port and the unguarded
spelling both fire on 1,481 of 1,500.

### G2 — what it buys

A 300-bar flat frame: the port fires on 0 bars, the unguarded spelling on
281, every one of them reading the arithmetically impossible **0**. See A4
for the arithmetic.

### G3 — the floor is RELATIVE, and where that matters

`spread > 4096 · eps · max |log c|`, not the absolute `4096 · eps` that
`ts_c3_20`, `ts_binent_20` and `ts_cid_ce_20` use. On ordinary frames the
two are indistinguishable:

| frame | relative fires | absolute fires |
|---|---|---|
| flat | 0 | 0 |
| walk | 1,481 | 1,481 |
| ladder | 281 | 281 |
| patches | 1,343 | 1,343 |

They separate exactly where `|log c|` is far from 1, which is the whole
argument for the relative form:

| frame (600 bars) | median log spread | relative floor | absolute floor | relative fires | absolute fires | unguarded vs exact oracle |
|---|---|---|---|---|---|---|
| price ≈ 1.0, σ 1e-13 | 6.104e-13 | 1.496e-24 | 9.095e-13 | **581** | **44** | 581/581 |
| price 100, σ 1e-15 | 6.217e-15 | 4.188e-12 | 9.095e-13 | 0 | 0 | 284/581 |
| price 1e+6, σ 1e-15 | 5.329e-15 | 1.257e-11 | 9.095e-13 | 0 | 0 | 158/581 |

Row 1 is the cost of an absolute floor: at a price near 1.0 every
`|log c|` is tiny, so the error the floor must beat is tiny too, and the
relative floor reports 581 bars that the 60-digit oracle confirms exactly
while the absolute floor keeps 44 of them. Rows 2 and 3 are the mirror: a
spread of a few 1e-15 at price 100 or 1e+6 is *below* the relative floor
and *above* the absolute one — and there the unguarded count disagrees with
the exact oracle on 297 and 423 of 581 windows, so refusing is the right
answer and the absolute floor would be the one that is wrong.

### G3b — where the 4096 sits, measured on the floor's own axis

The floor thresholds `(hi − lo) / (eps · max |x|)`, so that is the axis the
calibration has to be measured on — **per window**, not per frame. A
6,000-bar frame whose per-bar volatility sweeps from 1e-18 to 1e-08 gives
5,981 windows spanning roughly 1 to 1e+08 ulps; each one's unguarded float
count is compared with the 60-digit exact one and the windows are bucketed
by their own ratio.

| bucket (ulps) | price 100: windows / exact / share | price 1e+6: windows / exact / share |
|---|---|---|
| [0, 16) | 2,059 / 1,169 / 0.5678 | 2,343 / 1,218 / 0.5198 |
| [16, 64) | 351 / 288 / 0.8205 | 336 / 285 / 0.8482 |
| [64, 256) | 361 / 336 / 0.9307 | 420 / 402 / 0.9571 |
| [256, 1024) | 425 / 417 / 0.9812 | 379 / 372 / 0.9815 |
| [1024, 4096) | 329 / 329 / 1.0000 | 320 / 317 / 0.9906 |
| **[4096, 16384)** | **351 / 350 / 0.9972** | **371 / 371 / 1.0000** |
| [16384, 1e+06) | 1,047 / 1,047 / 1.0000 | 1,088 / 1,088 / 1.0000 |
| [1e+06, 1e+08) | 1,058 / 1,058 / 1.0000 | 724 / 724 / 1.0000 |

Read it honestly in both directions. Below 16 ulps float gets **barely
half** the counts right, and the floor's job is to refuse that regime
entirely — it does, along with everything up to 4096. The floor admits the
last three rows of each column, six cells in all: the agreement is total in
**five of those six**, and **350 of 351** in the sixth. A window just above
the floor can still be miscounted, once in 351 here. **So the floor is a
strong filter and not a proof**, and the 4096 is the siblings' constant
placed where the error rate has already collapsed by two orders (0.4322
wrong below 16 ulps against 0.0028 at [4096, 16384), price 100) — not a
threshold measured to be exact.

What makes that residual irrelevant in practice is where real-shaped
windows actually sit on this axis. Min and median ulps per frame:

| frame | min | median |
|---|---|---|
| ar1+ | 5.19e+13 | 2.74e+14 |
| ar1− | 3.09e+13 | 7.98e+13 |
| heavy-tailed | 1.72e+13 | 8.33e+13 |
| left-skewed | 1.49e+13 | 4.70e+13 |
| right-skewed | 1.87e+13 | 5.47e+13 |
| tick-rounded | 2.49e+13 | 7.63e+13 |
| trending | 1.27e+13 | 5.26e+13 |
| two-point | 2.17e+13 | 5.87e+13 |
| walk | 2.49e+13 | 7.63e+13 |

The worst window of any of the nine is **1.27e+13 ulps**, nine orders above
the floor and five above the top bucket of the table, which holds 1,782
windows with zero disagreements. On those frames the two oracles are not
the same oracle, and the distinction matters: **A1** measures all nine
bit-equal against the source applied window by window (13,329 windows),
while **A3/A3b** put four of them plus three quiet 600-bar frames to the
60-digit oracle — 5,924 + 1,743 windows, 0 disagreements. ar1+, ar1−,
heavy-tailed, left-skewed and right-skewed have not been through the
60-digit oracle.

### G4 — a bad close empties exactly the windows holding it

A close that is NaN, infinite, zero, negative or subnormal is replaced with
NaN before `np.log` sees it. Its window then has a NaN range, `NaN > x` is
False, and the floor test empties it — the same single test that enforces
the dispersion floor, which is why
`test_a_bad_close_empties_its_windows` exists: the behaviour must not drift
to a silent count of 0.

| bad value at bar 200 of a 400-bar walk | bars emptied |
|---|---|
| `nan`, `inf`, `0.0`, `-1.0`, `1e-310` | 20 each |

and near either end, with a NaN:

| bar | 0 | 1 | 18 | 200 | 398 | 399 |
|---|---|---|---|---|---|---|
| bars emptied | 1 | 2 | 19 | 20 | 2 | 1 |

No earlier bar moves in any of these. A frame whose closes are all
non-positive produces no warning under `np.errstate(all="raise")` and fires
on 0 bars — there is no silenced `errstate` in the module.

### G5 — why there is no magnitude bound

`ts_above_mean_20` needs one because a price RATIO is unbounded and a window
sum of ratios can overflow. A logarithm cannot:
`log(2.23e-308) = −708.40` and `log(1.80e+308) = 709.78`, so every close
that survives the mask has `|log c| ≤ 709.79` and a window of 250 of them
sums to at most 1.8e+05. That is a derivation, and the guard it removes is
the difference between this module and its sibling.

Likewise there is no `isfinite` backstop on the output: the output is an
integer count and cannot be anything else.

### G6 — one enormous close stays LOCAL

A 2,000-bar walk with the close at bar 200 multiplied by `mag`:

| mag | bars 220.. bit-identical to the unspiked frame | the 20 windows holding it read |
|---|---|---|
| ×1e+02 | 1,780 / 1,780 | 1 or 2 |
| ×1e+06 | 1,780 / 1,780 | 1 or 2 |
| ×1e+08 | 1,780 / 1,780 | 1 or 2 |
| ×1e+100 | 1,780 / 1,780 | 1 or 2 |
| ×1e+300 | 1,780 / 1,780 | 1 or 2 |

Every window is reduced from its own 20 values by `sliding_window_view`, so
nothing accumulates across windows. ⚠ Unlike `ts_medskew_20`, this is **not
a difference from the prototype**: the prototype is the same windowed form
and is equally local (1,780/1,780 at ×1e+08). It is recorded because it is
a property worth keeping, not because it distinguishes anything.

---

## E. Gate E — attribution

**Gate E: SHIP.** Run `is100-ts_cross_mean_20-39bc2e49`, measured
2026-11-14 by issue-solver on **this** module, not on the prototype.

| | |
|---|---|
| column | `TS_CROSS_MEAN_20` |
| pooled max \|ρ\| | **0.5500** (signed −0.5500) |
| against | `BB_BWidth_Pctl`, from the `ml_features` manifest |
| n | **391,907** |
| per-frame max median \|ρ\| | **0.5495**, also against `BB_BWidth_Pctl` |
| frames at \|ρ\| ≥ 0.90 | **0 of 89** |
| verdict | **SHIP** (`r3-perframe-0.90`; SHIP is < 0.76 pooled and < 0.90 per-frame median) |
| best `compute_all` comparator | `BB_BWidth`, 0.5095, n = 397,158 |
| comparators | 687 = 329 `compute_all` + 358 manifest, 0 degenerate |
| universe | 89 frozen ALTPORT-1 BIST frames, 398,849 pooled bars |
| defaults | `kwargs: {}` — no non-default parameter |
| canary | AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal |
| versions | pandas 2.3.3 / numpy 1.26.4 |
| module sha1 | `6674bce4652cd5159e7b2db423a994179619e009` |
| tree sha1 | `af8be48618f43a6a4e5101678d23324dc2072b46` |

Recorded with
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-14`;
`record` accepted it, which is what checks that the harness imported a
`pandas_ta` tree byte-identical to this one, that the parameters were the
defaults, that the universe was the 89 frames, that the comparator set was
687 and that the canary was bit-equal. The row is
`docs/gate_e_ledger.csv` line 96, with no waiver.
`tests/test_ts_cross_mean_20.py::test_the_gate_e_row_is_this_ports_own_measurement`
pins the row's identity (run id, module, column, verdict); the old
`test_the_gate_e_row_is_still_owed` is gone.

### E1 — Gate C on real data, from that run

The run's own counts over the 89 frames, 398,849 pooled bars:

| | bars |
|---|---|
| pooled | 398,849 |
| non-NaN (`TS_CROSS_MEAN_20` fires) | **397,158** |
| non-zero | **397,158** |
| NaN | 1,691 |

So `0 < 397,158 < 398,849` on real data, and **not one fired bar reads 0** —
which is §A4's derivation holding on 397,158 real windows rather than on a
derivation alone. The 1,691 empty bars are 19 warm-up bars per frame
(19 × 89 = 1,691), so the floor and the bad-close mask emptied **no**
further real bar.

⚠ Those are the Gate E universe's counts. Separately, the ledger row stores
an output fingerprint taken on `gate_e_ledger.py`'s own fixed 600-bar
tick-rounded frame — `581;2315.0;11887.0;735979.0`, i.e. finite count, sum,
sum of squares and index-weighted sum (`gate_e_ledger.py:148`) — which is
what `tests/test_gate_e_ledger.py` re-derives to catch a later edit moving
the output. 581 = 600 − 19, the same warm-up.

### E0 — what the 2026-10-24 screen measured, on its PROTOTYPE

A prototype is not a port, and these numbers are recorded as the prior they
are. From `docs/issues/screen/candidates.csv` line 73 (owner's machine,
gitignored) and issue #100:

| measurement | value |
|---|---|
| Gate E max \|ρ\| | **0.5500** vs `BB_BWidth_Pctl` (manifest), n = 391,907 |
| per-frame max median | 0.5495 → **SHIP** |
| next comparators | `BB_BWidth` 0.5095, `chop` 0.4925 |
| fork overlap (stage 2, 12 frames) | 0.5684 vs `squeeze_pro:SQZPRO_ON_WIDE`, per-frame max median 0.5708 |
| pre-flight (6 frames, `sanity.csv`) | prefix-causal, unchanged under price ×8 and volume ×8 |
| run | `screen_20261024`, Backtesting `main` b2d94243, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal |

`docs/issues/screen/cand_pairs.csv` lists every candidate pair the screen
measured at \|ρ\| ≥ 0.8019 — 55 pairs, on lines 2–56 of the file.
**`ts_cross_mean_20` is in none of them.** (Read in full, 2026-11-13. The
file is on the owner's machine only; `docs/issues/` is gitignored.)

Since this port is bit-equal to that prototype on 1,481 of 1,481 bars of
each of nine frames with identical masks (A7), the screen's figures were
expected to carry over, and the run in §E shows they did: same comparator,
same n, 0.5500341832 pooled and 0.5494921049 per-frame max median against
the screen's printed 0.5500 and 0.5495, and the same `BB_BWidth` 0.5095 one
place down. The prototype was never a substitute for the run; it turned out
to be an accurate prior.

---

## O. In-fork overlap — what Gate E's 687 comparators cannot see

Gate E's comparator set is the engine's `compute_all` ∪ the `ml_features`
manifest. It holds **no pandas_ta port**, so it cannot see this column
against the fork's own choppiness family. Everything in this section is
SYNTHETIC — six 1,500-bar frames, with `chop` fed deterministic synthetic
high/low (`close × 1.004` and `close × 0.996`), since the frames carry
closes only. Read the run's real-frame figures in §E beside them.

### O1 — it is a CHOPPINESS reading

| frame | `chop` | `vhf` | `LEAN_MOMERSION_20` | `TS_PERMENT_20_3` | `TS_PEAKS_20_2` |
|---|---|---|---|---|---|
| walk | +0.5289 | −0.4813 | −0.1703 | +0.2674 | +0.2673 |
| tick-rounded | +0.5291 | −0.4814 | −0.1694 | +0.2621 | +0.2669 |
| heavy-tailed | +0.5738 | −0.5607 | −0.1852 | +0.2672 | +0.2165 |
| trending | +0.5776 | −0.5019 | −0.2895 | +0.4812 | +0.3540 |
| ar1+ | +0.5646 | −0.5167 | −0.2535 | +0.4066 | +0.3051 |
| ar1− | +0.6296 | −0.5522 | −0.2738 | +0.2171 | +0.2145 |

`chop` and `vhf` read choppiness with opposite signs, and this column
agrees with both. `TS_PERMENT_20_3` and `TS_PEAKS_20_2` are the two
shipped columns that read the **same 20 closes** and were therefore the two
most at risk of being restated; they are not, at +0.2171..+0.4812 and
+0.2145..+0.3540. Nothing here is within 0.25 of the 0.90 strike line.

### O2 — it is window DISPERSION upside down, and not volatility

On the walk, against statistics of the same 20-close window:

| statistic | Spearman |
|---|---|
| log-close standard deviation | **−0.6827** |
| realised volatility (sd of the 19 log returns) | +0.1045 |
| \|log close[T] − log close[T−19]\| | −0.3906 |
| signed drift over the window | −0.0530 |
| the close itself | −0.1178 |
| \|drift\| / realised volatility | −0.4053 |

This is the one number a consumer should read first. A window whose log
closes spread out is a window that trended, and a trending window crosses
its mean once — so the column is strongly *inverse* to the window's own
dispersion while being nearly blind to realised volatility and to the price
level. It is the SHAPE of the window that moves it, not the size.

That also explains Gate E's top real-frame comparator, the screen's and the
run's alike: `BB_BWidth_Pctl` at 0.5500 is a band-width percentile, i.e. a
dispersion reading — and the sign is negative (§E), the same direction as
the −0.6827 here.

### O3 — the level to expect, on INDEPENDENT windows

20,000 independent windows per row, so the figures are not an artefact of
overlap.

| windows of | mean | sd | min | max |
|---|---|---|---|---|
| iid gaussian log returns (a driftless walk) | 3.6674 | 2.2007 | 1 | 13 |
| the same with a +1 sd/bar drift | 1.1946 | 0.6461 | 1 | 9 |
| white-noise log closes (no walk at all) | 9.8399 | 2.1603 | 3 | 17 |

### O4 — coarse and heavily tied

19 possible values at `length` 20, of which a 1,500-bar walk shows 13, with
the value **1** taking 339 of 1,481 fired bars. A rank statistic over this
column carries many tied ranks by construction. `docs/IndicatorDictionary.md`
tags it `ORD` and not `SF` for that reason — the generator's rule is "at
most 12 distinct values on the probe and all integers" — which is the same
place `TS_PEAKS_20_2` lands.

---

## Z. Cost

400,000 bars, best of three after a warm-up call (without the warm-up an
ordered A/B on this machine reads backwards, whichever spelling goes
second — both orders were run). `peak` is `tracemalloc`'s peak for one
call. The alternative is the source's own two lines,
`above = windows > mean[:, None]` then `above[:, 1:] != above[:, :-1]`,
compared as a MODULE with those two lines swapped rather than as a bare
function, so that the mask, the output array and the Series are charged to
both.

| length | shipped ms | shipped peak MB | matrix ms | matrix peak MB | counts equal |
|---|---|---|---|---|---|
| 3 | 37.0 | 29.2 | 49.0 | 30.0 | 399,998/399,998 |
| 20 | 60.7 | 29.2 | 69.6 | 36.8 | 399,981/399,981 |
| 60 | 101.1 | 29.2 | 113.5 | 66.9 | 399,941/399,941 |
| 250 | 269.7 | 29.2 | 265.8 | 218.8 | 399,751/399,751 |

The shipped spelling's peak does not grow with `length`; the matrix form's
reaches 218.8 MB at `length` 250. The two agree on every count.

⚠ **The milliseconds are not a reason either way, and no claim is made
from them.** Five runs of this section happened on this machine during
this session — three mine, two the reviewers', the last two reporting
only the lengths their findings turned on:

| run | shipped ms (3 / 20 / 60 / 250) | matrix ms |
|---|---|---|
| 1 (mine, the table above) | 37.0 / 60.7 / 101.1 / 269.7 | 49.0 / 69.6 / 113.5 / 265.8 |
| 2 (round-2 reviewer) | 34.1 / 61.9 / 101.5 / 312.9 | 45.9 / 68.1 / 96.1 / 263.9 |
| 3 (mine) | 38.8 / 60.7 / 102.3 / 270.3 | 48.2 / 68.4 / 112.3 / 261.6 |
| 4 (round-3 reviewer, partial) | 33.5 at 3, 100.7 at 60 | 45.5 at 3 |
| 5 (round-4 reviewer, partial) | 101.3 at 60 | 95.8 at 60 |

**The winner at `length` 60 has gone both ways across the runs on
record** — runs 1 and 3 to the shipped spelling, runs 2 and 5 to the
matrix one — and the shipped figure at 250 moved by 16% between runs 1
and 2. **The peaks are the claim**; they reproduced to the digit in every
run that reported them, as did every "counts equal" cell.

For scale, the window-by-window oracle Gate A checks against is **about
two orders slower than the module**: every run recorded here put it
between 159.8 and 174.8 ms on 20,000 bars against the module's 2.8 to
3.5 ms. ⚠ Those are cold single calls — the oracle is the one timing in
this section the script does not warm up or take a best-of-three for — so
the gap is the claim and the endpoints are observations, not a band
anything should be checked against. It is why the oracle lives in
`docs/measure_ts_cross_mean_20.py` and not in the package.

---

## F. Gate F — suites

* `python -m pytest tests/test_ts_cross_mean_20.py -q` → **205 passed**
  in 3.22 s.
* `python docs/measure_ts_cross_mean_20_cpu.py` → the same **205 passed**
  with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, the
  script asserting that the dispatch took and printing the features that
  survive (on this machine `SSSE3`, `SSE41`, `POPCNT`, `SSE42`, `AVX`,
  `F16C`, `AVX512CD`, `AVX512_CLX`, `AVX512_CNL`, `AVX512_ICL`).
* `python -m pytest -q` → **3 failed, 7,521 passed, 85 skipped** in 187 s
  in the porting session, when the third failure was this port's own owed
  Gate E row.
* After the Gate E run was recorded (receipt session, 2026-11-14):
  `python -m pytest -q` → **3 failed, 7,911 passed, 85 skipped** in 200 s,
  and `ts_cross_mean_20` is in none of the three. They are: the `CLAUDE.md`
  Known break
  (`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`), the
  `../AlternativeRepos`-only test CI deselects by name
  (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`),
  and `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  which now reports **seven other** indicators —
  `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife',
  'lumpiness', 'mtd_ret']`, all of them owed by someone else.
  `python -m pytest tests/test_ts_cross_mean_20.py -q` → **205 passed** in
  3.08 s, including the new
  `test_the_gate_e_row_is_this_ports_own_measurement`; and
  `python docs/measure_ts_cross_mean_20_cpu.py` → the same **205 passed** in
  2.91 s with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.
* The Backtesting suite is the launcher's to run.

⚠ One pre-existing trap, recorded and not fixed (it is outside this issue):
`pandas_ta/core.py:453` hands out the live `Category[name]` list and
`core.py:692` removes names from it, so running
`tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py` in
one process fails the pinned `CATEGORY_TOTAL` (330 against 333).
Alphabetical collection hides it; a full `python -m pytest -q` is green on
that test.

---

## Wiring

| # | file | change |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_cross_mean_20.py` | new |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_cross_mean_20 import ts_cross_mean_20` |
| 3 | `pandas_ta/__init__.py` | `Category["statistics"]` += `"ts_cross_mean_20"` |
| 4 | `pandas_ta/core.py` | `AnalysisIndicators.ts_cross_mean_20` |
| 5 | `tests/test_ts_cross_mean_20.py` | new, 205 tests |

and the counts that move with it: `tests/test_altport2_ports.py`
`CATEGORY_TOTAL` 332 → 333, `README.md` 332 → 333 registered / 340 → 341
callable / statistics 41 → 42, `docs/IndicatorDictionary.md` regenerated
(334 → 335 probed, statistics 41 → 42), `docs/MLCompanionContract.md`
677 → 678 tagged columns and 52 → 53 `ORD`.

---

## Verdict

**Ship.** Gate E ran on this module on 2026-11-14 and came back **SHIP** at
pooled \|ρ\| 0.5500 against `BB_BWidth_Pctl` (n = 391,907), per-frame max
median 0.5495, 0 of 89 frames at or above 0.90 — a long way under the 0.76
ship line, so nothing is removed and nothing is waived. Every other gate was
clear before it: Gate A
bit-equal against three independent oracles including one at 60 significant
digits, Gate B 0 of 37 on the real module with six mutants of which the
hardest needed a derived probe, Gate C `0 < 1,481 < 1,500` with no zeros on
synthetic frames and `0 < 397,158 < 398,849` with no zeros on the real
universe (§E1),
Gate D bit-identical at ×8/×64 (measured, with a six-order margin) and
under any monotone power of the price, and the in-fork overlap topping out
at +0.6296 against `chop` on synthetic frames.

What would have reversed it: a Gate E run on this module at pooled
\|ρ\| ≥ 0.90, or a top-5 comparator's per-frame median ≥ 0.90. The run
measured 0.5500 and 0.5495, the same two figures the prototype screen
printed, so neither happened.

What is still open and is **not** this issue's to close: `docs/gate_e_ledger.csv`
owes rows for seven other indicators (§F), and the two pre-existing suite
failures recorded in `CLAUDE.md`.
