# TF-HIGUCHI-30 — `tf_higuchi_30`, measured

Issue #115 (`TF-HIGUCHI-30`), branch `issue-115-tf-higuchi-30`.
Source: **TSFEL** (Fraunhofer Portugal AICOS, BSD-3-Clause),
<https://github.com/fraunhoferportugal/tsfel>,
`tsfel/feature_extraction/features.py` `higuchi_fractal_dimension`.
Scale-free form: `k = 1..5`, the owner's screen prototype
`docs/issues/screen/ind_screen_r2.py:276-293` (candidate `tf_higuchi_30`;
`docs/issues/` is gitignored, so that path exists only on the owner's
machine).

One column: **`TFHIGUCHI_30`** — the Higuchi fractal dimension of the last 30
closes. 1 is a straight line, 1.5 a random walk, 2 a space-filling path.
Category `statistics`. Module `pandas_ta/statistics/tf_higuchi_30.py`.

Every figure below is printed by

```sh
python docs/measure_tf_higuchi_30.py            # every section
python docs/measure_tf_higuchi_30.py A1 D L4    # named sections
python docs/measure_tf_higuchi_30_cpu.py A1 D   # the same, AVX-512/AVX2/FMA3 off
python docs/measure_tf_higuchi_30_cpu.py        # the test module on that dispatch
```

with **four** exceptions, each flagged again where it appears:

1. **§F1's three pytest counts**, which `python -m pytest` prints and no
   section of either script does — §F1's own ⚠ says so.
2. **The Gate E block** (0.5231 vs `mad_pct_Pctl`, 0.5298 per frame, 0.5207,
   0.5015, 398,849 bars, 687 comparators), quoted from issue #115 and
   measured by the 2026-10-24 screen on the PROTOTYPE, not here. The launcher
   runs Gate E after this session — see **Gate E**.
3. **§F2's list of dispatchable features still enabled**, which
   `docs/measure_tf_higuchi_30_cpu.py` prints as its banner.
4. **Three `tf_dfa_100` figures quoted for contrast**, which come from
   `docs/TfDfa100Measured.md` on `dev` and not from any run here: its iid
   centre of 0.6289 / 0.6292 (§A4 of this document rounds it to 0.63;
   `TfDfa100Measured.md` §A5 and §A5b), the 0.3698 a time reversal moves it
   by (§L2 here; `TfDfa100Measured.md` §L5), and the 100 windows a zero close
   blanks in it (§G here; `TfDfa100Measured.md` §G, "101 for a NaN and 100
   for the rest").

**Verdict: SHIP, with one disclosure and one owed measurement.** The column
is correct against three independent spellings of Higuchi (1988), causal
under five mutants, bit-identical under an exact binary rescale of the price,
and it reads 1.0000000000000002, 1.5137 and 1.9978 against the textbook 1,
1.5 and 2.0 for a straight line, a Brownian path and iid noise — within
0.014 of the Brownian anchor and 0.0022 of the iid one, which is the
estimator's bias on a 30-bar window with `k ≤ 5` and is measured in §A4
rather than argued. The disclosure is its overlap with the fork's own
`vhf`, which Gate E's comparator set cannot see — §L4, and the **OWED** block
there.

---

## Gate A — correctness

### §A — what the source actually says, and what it does not

The issue quotes two lines of TSFEL:

```
features.py higuchi_fractal_dimension
(scale-free form: k = 1..5)
```

⚠ **That is the entire source text available in this worktree.** TSFEL is not
installed, `docs/pine/` does not carry it, and web access is unavailable:

```
`import tsfel` -> ImportError: No module named 'tsfel'
```

`tests/test_tf_higuchi_30.py::test_the_source_library_is_not_readable_here`
asserts that, so the limitation fails loudly if the environment ever changes.

What Gate A checks is therefore the quantity those lines **name** — Higuchi's
fractal dimension, T. Higuchi, *Approach to an irregular time series on the
basis of the fractal theory*, Physica D 31 (1988) 277–283 — and not TSFEL's
code. For a series `X(1) .. X(N)` and a spacing `k`, Higuchi builds `k`
interleaved sub-series starting at `m = 1 .. k`, each of length
`floor((N - m) / k) + 1`, and measures

```
L_m(k) = [ SUM_{j=1..floor((N-m)/k)} |X(m + jk) - X(m + (j-1)k)| ]
         * (N - 1) / (floor((N-m)/k) * k) / k
L(k)   = mean over m of L_m(k)
D      = OLS slope of log L(k) on log(1/k)
```

The module spells the same thing with 0-based offsets `m = 0 .. k-1` and the
interval count `len(range(m, N, k)) - 1`, which is the same integer
(§A5), and takes the logarithm of `L(k) / L(1)` rather than of `L(k)` — a
Gate D fix, §D.

### §A1 — the screen prototype

The expression the 2026-10-24 screen measured Gate E's 0.5231 on, retyped in
`docs/measure_tf_higuchi_30.py::_prototype` and in the test module, with the
screen's `_fin` (±inf → NaN) applied as `screen()` applies it.

Twelve 1,500-bar synthetic frames at the default length, default dispatch:

| frame | bars | both define | differ | max abs diff | NaN masks equal |
|---|---|---|---|---|---|
| walk | 1500 | 1471 | 598 | 6.661e-16 | yes |
| trend | 1500 | 1471 | 814 | 8.882e-16 | yes |
| range-bound | 1500 | 1471 | 681 | 6.661e-16 | yes |
| grid | 1500 | 1471 | 614 | 6.661e-16 | yes |
| heavy-tailed | 1500 | 1471 | 597 | 6.661e-16 | yes |
| jump | 1500 | 1471 | 566 | 6.661e-16 | yes |
| noise | 1500 | 1471 | 713 | 8.882e-16 | yes |
| smooth | 1500 | 1460 | 605 | 4.441e-16 | yes |
| line | 1500 | 1471 | 1471 | 2.220e-16 | yes |
| ramp | 60 | 31 | 28 | 3.997e-15 | yes |
| flat | 1500 | 0 | 0 | — | yes |
| alternating | 1500 | 0 | 0 | — | yes |

**6,687 of the 13,259 bars both define differ, by at most 3.997e-15** on the
default dispatch; **6,593 and 4.219e-15** with AVX-512/AVX2/FMA3 off. The
docstrings quote the AVX-disabled ceiling, which is the worse of the two, and
say "about 6,600" for the count, because the count is itself a count of last
bits (§F2).

**The difference is exactly two spellings.** A mutant of the shipped file
with `np.log(L(k) / L(1))` restored to `np.log(L(k))` *and* the summed dot
product restored to `@` is **bit-equal to the prototype on all twelve
frames**, under both dispatches. That is what makes the table above a
tolerance with nothing hiding in it: a drifted spacing, strand
normalisation, interval count or regressor would survive 1e-12 and fail
there.

At other lengths (walk / trend / heavy-tailed), masks equal throughout:

| length | 10 | 20 | 30 | 60 | 250 |
|---|---|---|---|---|---|
| max abs diff, default | 8.882e-16 | 8.882e-16 | 8.882e-16 | 8.882e-16 | 1.554e-15 |
| max abs diff, AVX off | 8.882e-16 | 8.882e-16 | 8.882e-16 | 8.882e-16 | 1.332e-15 |

### §A2 — Higuchi (1988) by scalar loops

A spelling that shares no numpy operation with the module: the paper's own
1-based indexing, its `floor((N - m) / k)` interval count, `math.fsum` for
every sum, the slope through the normal equations. 300-bar frames, lengths 10
and 30:

| frame | length 10 | length 30 |
|---|---|---|
| walk | 6.661e-16 | 6.661e-16 |
| trend | 4.441e-16 | 6.661e-16 |
| heavy-tailed | 6.661e-16 | 6.661e-16 |
| noise | 8.882e-16 | 8.882e-16 |
| smooth | 4.441e-16 | 4.441e-16 |
| line | 0.000e+00 | 3.331e-16 |

**Worst 8.882e-16**, NaN masks identical, and the same figure under both
dispatches. That the 1-based `floor((N - m) / k)` and the 0-based
`len(range(m, N, k)) - 1` agree is the point of this section: it is the one
index convention a port of this formula gets wrong.

### §A3 — the same quantity through `np.linalg.lstsq`

A third spelling, and the one the published implementations use: a design
matrix `[[log(1/k), 1]]` solved by `lstsq` instead of a centred closed form.
300-bar frames:

| frame | max abs diff, default | AVX off |
|---|---|---|
| walk | 1.554e-15 | 1.554e-15 |
| heavy-tailed | 1.554e-15 | 1.554e-15 |
| noise | 3.109e-15 | 2.442e-15 |
| smooth | 1.110e-15 | 1.110e-15 |
| grid | 1.554e-15 | 1.554e-15 |

**Worst 3.109e-15**, the default dispatch, which is the worse of the two here.

### §A4 — the anchors: what a KNOWN curve must read

This is the section that makes the port checkable against the **definition**
and not only against another implementation.

**A straight line reads 1, and the derivation is exact.** Every lag-`k`
difference of an arithmetic ramp is the same number `step * k`, so
`L(k) = step * (N - 1) / k` for every `m`, `log L(k) = const + log(1/k)`, and
the slope on `log(1/k)` is 1. Measured on the `line` frame: every one of the
1,471 readings is **1.0000000000000002** — one ulp above one, identical under
both dispatches, worst `|reading - 1|` **2.220e-16**. (0 bars read exactly
1.0; the last bit belongs to `log`.)

**A Brownian path reads 1.5 and iid noise reads 2.0**, over disjoint 30-bar
windows of 30,000 points:

| process | true D | measured mean | sd | windows |
|---|---|---|---|---|
| Brownian (cumsum of iid normal) | 1.5 | **1.5137** | 0.1453 | 1,000 |
| iid normal | 2.0 | **1.9978** | 0.0894 | 1,000 |

The same arithmetic on a 300-bar window with `k = 1 .. 20` (a mutant whose
`KMAX` is 20) tightens both: 1.5035 (sd 0.0620) and 1.9992 (sd 0.0098). So
the 30-bar / `k ≤ 5` ladder costs variance, not very much bias — unlike
`tf_dfa_100`, whose short-box ladder puts the iid centre at 0.63 instead of
0.5. Identical under both dispatches.

**The ordering the dimension exists for.** Median reading per 1,500-bar
frame:

| frame | median | min | max | fires |
|---|---|---|---|---|
| walk | 1.4725 | 1.0607 | 1.8910 | 1471 |
| trend | 1.3715 | 1.0606 | 1.8022 | 1471 |
| range-bound | 1.5741 | 1.2618 | 2.0047 | 1471 |
| grid | 1.5050 | 1.0993 | 2.0127 | 1471 |
| heavy-tailed | 1.4028 | 1.0838 | 1.9907 | 1471 |
| jump | 1.4392 | 1.0616 | 1.8425 | 1471 |
| noise | 1.9945 | 1.7031 | 2.1941 | 1471 |
| smooth | 1.0135 | 0.9458 | 1.9303 | 1460 |
| line | 1.0000 | 1.0000 | 1.0000 | 1471 |
| ramp | 1.5053 | 1.5053 | 1.5053 | 31 |

smooth 1.0135 < walk 1.4725 < noise 1.9945. ⚠ **The column is NOT bounded to
[1, 2]:** 0.9458 on the smoothed frame and 2.1941 on the iid one. A consumer
must not assume the nominal range.

⚠ A geometric `100 * 2**i` ramp reads a **constant** 1.5053: every window is
an exact scaled copy of the one before it and the dimension is scale-free, so
there is nothing left to vary. Its 31 readings are one distinct value.

### §A5 — the spacing ladder, and the points each strand drops

`length = 30`, `k = 1 .. 5`. "reaches" is the last index the strand touches,
"dropped" the closes after it that the strand never reads:

| k | m | points | intervals | reaches | dropped |
|---|---|---|---|---|---|
| 1 | 0 | 30 | 29 | 29 | 0 |
| 2 | 0 | 15 | 14 | 28 | 1 |
| 2 | 1 | 15 | 14 | 29 | 0 |
| 3 | 0 | 10 | 9 | 27 | 2 |
| 3 | 1 | 10 | 9 | 28 | 1 |
| 3 | 2 | 10 | 9 | 29 | 0 |
| 4 | 0 | 8 | 7 | 28 | 1 |
| 4 | 1 | 8 | 7 | 29 | 0 |
| 4 | 2 | 7 | 6 | 26 | 3 |
| 4 | 3 | 7 | 6 | 27 | 2 |
| 5 | 0..4 | 6 | 5 | 25..29 | 4..0 |

The minimum is **5** intervals, at `k = 5`. `k = 4` is the only spacing whose
strands differ in length — two of 7 intervals and two of 6 — which is exactly
what the `(N - 1) / (intervals * k)` factor exists to make comparable, and
why the count is taken per strand and not per spacing.

The regressor, derived from `KMAX` alone:

```
LOG_INV_K_CENTRED = [ 0.957498  0.264351 -0.141114 -0.428796 -0.65194 ]
sum = -2.220e-16   LOG_INV_K_SS = 1.6154889869425695
```

A mutant whose `KMAX` is 10 moves all 1,471 bars of the `walk` frame, by up
to **0.4190** — so the ladder is load-bearing and the regressor is not
stale.

`MIN_LENGTH = 2 * KMAX = 10`: at 10 closes the last strand (`k = 5, m = 4`)
still holds two points, and at 9 it holds one and has no interval at all.

### §A6 — the readings this port did NOT take

1. **TSFEL's own code.** Not readable here (§A). Nothing in this document is
   evidence about how TSFEL handles an edge the issue does not name.
2. **`kmax = 10`,** which published implementations default to. The issue's
   scale-free form says `k = 1..5` and that is what the screen measured, so
   that is what ships. What the wider ladder would buy is measured in §A4
   (less variance, little bias) rather than assumed.
3. **Real prices.** None are in this worktree. Gate C's real limb and Gate E
   come from the launcher's run.
4. **A `kmax` parameter.** `KMAX` is a module constant, like `tf_dfa_100`'s
   `BOXES`. Exposing it would make the column name ambiguous (`TFHIGUCHI_30`
   encodes the length only), and the issue names one ladder.

---

## Gate B — causality

Offsets swept on 1,500-bar frames: `[60, 265, 470, 675, 880, 1085, 1290,
1495]`. The first is 60 and not `LENGTH + 5` because the `smooth` frame's
first 40 bars are constant by construction and read NaN, so a prefix cut
below bar 40 holds no reading for a mutant to move. The `ramp` frame (60
bars) is out of the sweep: every offset but the first falls past its end, and
`_futures` would hand the same frame twice.

**The shipped module: caught 0 of 8 on all nine swept frames.** Prefix
truncation: equal at every offset on all ten firing frames.

**Four look-ahead mutants, read off disk, edited and `exec`'d in memory.**
Each is first checked LIVE (it must change the column) and then swept:

| mutant | what it does | live | caught |
|---|---|---|---|
| `close-lead` | `close.shift(-1)` before the windows | yes, 9/9 frames | 8/8 on every frame |
| `output-early` | writes each value one bar early | yes, 9/9 | 8/8 |
| `window-ahead` | `np.roll(c, -1)` under the window view | yes, 9/9 | 8/8 |
| `window-centred` | window centred on the current bar (the `bos` failure mode) | yes, 9/9 | 8/8 |

36 mutant × frame pairs, 288 catches, no misses.

### §B2 — the mutant the blind sweep cannot see

`defined = np.roll(np.isfinite(win).all(axis=1), -1)` back-dates the GAP MASK
by one bar. On a clean frame it is **not even live** — every window is
defined — and the sweep returns **0 of 8** on all nine frames. That is
exactly what `CLAUDE.md`'s Gate B says prefix work cannot see, so it is
pinned directly instead, by planting one NaN close:

| NaN at | real gap starts | mutant gap starts | real shifted one earlier ⊆ mutant |
|---|---|---|---|
| 150 | 150 | 149 | yes |
| 700 | 700 | 699 | yes |
| 1200 | 1200 | 1199 | yes |

### §B3 — prefix truncation across a chunk boundary

The sweep above runs on frames that fit in one chunk, so it says nothing
about the chunk loop. With `CHUNK_VALUES` cut to 30 and to 210 (one and seven
rows per chunk at the default length) the `walk` frame is split many times
over, and both limbs hold: equal to the default run, and prefix-equal at
every offset.

---

## Gate C — reachability

### §C1 — real data

⚠ **Owed.** No real prices are in this worktree, and `docs/issues/` carries
no frame. The real limb comes from the launcher's Gate E run, whose ledger
row records `pooled_bars`, `non_nan` and `non_zero` over the 89 ALTPORT-1
frames. The receipt session reads it off that row.

### §C2 — synthetic frames

1,500-bar frames, default length:

| frame | bars | fires | empty | distinct | min | max |
|---|---|---|---|---|---|---|
| walk | 1500 | 1471 | 29 | 1471 | 1.0607 | 1.8910 |
| trend | 1500 | 1471 | 29 | 1471 | 1.0606 | 1.8022 |
| range-bound | 1500 | 1471 | 29 | 1471 | 1.2618 | 2.0047 |
| grid | 1500 | 1471 | 29 | 1471 | 1.0993 | 2.0127 |
| heavy-tailed | 1500 | 1471 | 29 | 1471 | 1.0838 | 1.9907 |
| jump | 1500 | 1471 | 29 | 1471 | 1.0616 | 1.8425 |
| noise | 1500 | 1471 | 29 | 1471 | 1.7031 | 2.1941 |
| smooth | 1500 | 1460 | 40 | 1460 | 0.9458 | 1.9303 |
| line | 1500 | 1471 | 29 | **1** | 1.0000 | 1.0000 |
| ramp | 60 | 31 | 29 | **1** | 1.5053 | 1.5053 |
| flat | 1500 | 0 | 1500 | 0 | — | — |
| alternating | 1500 | 0 | 1500 | 0 | — | — |

The warm-up is **29 bars** — `length - 1`, a window of `length` CLOSES, not
of `length` returns — on every frame but `smooth`, whose first 40 bars are
constant after its back-fill and so have `L(k) = 0`. The shortest input that
produces a value is 30 closes (1 reading); 29 closes returns `None`.

`line` and `ramp` are constant by construction, which is why the
not-constant assertion runs on the other eight.

---

## Gate D — scale-free

### Exact binary factors: bit-identical

| factor | frames not bit-equal |
|---|---|
| ×8 | none |
| ×64 | none |
| ×2**-40 | none |
| ×2**40 | none |
| ×2**100 | none |

Ten firing frames each, under both dispatches. ×8 again at `length` 10, 20,
30, 60 and 250: none.

⚠ **This is what the `L(k) / L(1)` spelling buys, and it is the one
deliberate divergence from the prototype.** A power of two times a float is
exact, and so is a sum of exactly-scaled floats, so every `L(k)` scales by
exactly 8 under `close * 8` and the RATIO is unchanged bit for bit. The
prototype's `log L(k)` is not: `log(8 L)` is not `log 8 + log L` in floating
point and the leftover moves with `k`, so the centring cannot remove it.
Measured on the mutant with the prototype's spelling put back:
`raw(c)` and `raw(c * 8)` are **not** bit-equal, while agreeing to better
than 1e-12 — pinned by
`test_scale_the_prototype_spelling_would_only_be_a_tolerance`.

### Inexact factors: a tolerance

| factor | max abs diff, default | AVX off | masks equal |
|---|---|---|---|
| ×10 | 4.152e-14 | 4.019e-14 | yes |
| ×3.7 | 5.262e-14 | 5.196e-14 | yes |
| ×0.1 | **5.906e-14** | 5.751e-14 | yes |
| ×1.0000001 | 3.375e-14 | 3.331e-14 | yes |

Worst **5.906e-14**, the default dispatch.

### ⚠ A level shift is invariant too, so it cannot be the vacuity check

The column reads only DIFFERENCES of closes, so `close + s` is the same
quantity in exact arithmetic. Measured:

| shift | bars moved (of 1,471) | max abs diff |
|---|---|---|
| +1 | 30 (default) / 35 (AVX off) | 1.110e-15 / 1.554e-15 |
| +50 | 1,195 / 1,166 | 7.105e-15 / 7.550e-15 |
| +1e6 | 1,471 / 1,471 | **4.006e-11** |

Everything that moves is the rounding of `(c + s) - (c' + s)`. This is where
this port differs from its return-based siblings: `tf_dfa_100` asserts that a
shift MOVES its column, and uses that as the proof that its bit-identities
are not passing on a constant column. Here that proof has to come from
somewhere else.

### `0 < fires < n`, and the column is not constant

All ten firing frames satisfy `0 < fires < n`. On the eight VARYING frames
every fired bar is a distinct value (1,471 or 1,460 of them). The second half
of the anti-vacuity pair is
`test_a_different_path_is_a_different_reading`: a walk, a smoothed walk and
iid noise give three columns that differ on more than 300 bars each way.

---

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

Nothing in this document is a Gate E measurement. The harness
(`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.statistics.tf_higuchi_30`) is outside this worktree and this
session did not run it, read it, or write anything under `../Backtesting`.
`docs/gate_e_ledger.csv` therefore has **no row** for `tf_higuchi_30`, which
`tests/test_tf_higuchi_30.py::test_the_gate_e_row_is_owed_and_not_yet_recorded`
asserts; `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally until the receipt session records it, and CI skips it under
`GATE_E_PENDING_OK=1`.

For reference, and **measured on the prototype rather than on this port**,
the 2026-10-24 catalog screen (run `screen_r2_20261024`, 89 ALTPORT-1 frames,
398,849 bars, 329 + 358 comparators, canary bit-equal) read:

| limb | value |
|---|---|
| pooled max abs rho | **0.5231** vs `mad_pct_Pctl` (manifest), n = 391,017 |
| top-5 per-frame max median | **0.5298** |
| next comparators | `mad_pct` 0.5207, `mad_pct_State` 0.5015 |
| verdict | SHIP (`r3-perframe-0.90`, `< 0.76`) |

§A1 asserts this module equal to that prototype to 4.219e-15 with an
identical NaN mask, so the run on the port is expected to land on the same
figures — which is exactly why the receipt session must pin the row's
IDENTITY (its `run` field) and not only its arithmetic.

---

## Gate F — suites

PandasTa, this session:

* `python -m pytest tests/test_tf_higuchi_30.py -q` — see §F1.
* `python docs/measure_tf_higuchi_30_cpu.py` — the same module with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, the dispatch
  issue-solver re-runs port test modules under.
* `python -m pytest -q` — the full suite.

The Backtesting suite is the launcher's, in a clean worktree.

### §F1 — the runs

| run | result |
|---|---|
| `python -m pytest tests/test_tf_higuchi_30.py -q` | **326 passed** |
| `python docs/measure_tf_higuchi_30_cpu.py` (same module, AVX-512/AVX2/FMA3 off) | **326 passed** |
| `python -m pytest -q` | **2 failed, 11,147 passed, 85 skipped** |

⚠ These three cells are the one part of this document that no section of
`docs/measure_tf_higuchi_30.py` prints, so they go stale the moment a test is
added or parametrised **OR a document is added to the worktree** — several
suite guards scan every `.md` file in the fork, so a new receipt or review
record can turn the suite red on its own. All three happened during review:
324 → 325 when the ±inf fold test was parametrised (round 1), 325 → 326 when
the period-4 guard test was added (round 2), and
`tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
went red on a five-number interval list quoted into
`docs/reviews/auto-2026-11-15-tf-higuchi-30/01-tf-higuchi-30.md` (round 3,
fixed with that guard's own `<!--stale-by-design-->` marker).

**So: write the review folder and every doc FIRST, then run the three
commands above, then transcribe this table — last.**

The two failures are both expected and neither is this port's arithmetic:

* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  needs the sibling `../AlternativeRepos` checkout, which is not here; CI
  deselects it by name (`ci.yml`).
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  reports exactly `no Gate E ledger row for ['tf_higuchi_30']` — the owed
  row, which CI skips under `GATE_E_PENDING_OK=1` and the receipt session
  records.

The 85 skips were not itemised in this session; `CLAUDE.md` attributes 21 of
them to the upstream correlation suite, which `tests/config.py` skips at
import when the gitignored `data/SPY_D.csv` is absent.

### §F2 — which figures move between the two dispatches

Default = this machine's numpy 1.26.4 with AVX-512 available. "AVX off" =
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, which still leaves
`SSSE3 SSE41 POPCNT SSE42 AVX F16C AVX512CD AVX512_CLX AVX512_CNL AVX512_ICL`
enabled (the run prints the list, so the claim cannot drift).

⚠ **Scope.** The table below covers every figure that **MOVES** between the
two dispatches, plus the bit-equalities. Figures this document or a docstring
quotes that are **identical** on both dispatches, and are therefore not
listed row by row: §C's per-frame min and max (the 0.9458 .. 2.1941 range),
§L4's Spearman figures (-0.8901 pooled, 0.4721 .. 0.8284 per frame, 0.7151
median), §Z's two peaks (57.4 MB and 298.0 MB), §W's 133 and 17, and §A5's
0.4190 — each one checked under both dispatches. Nothing outside the table is
pinned as digits in a test.

| figure | default | AVX off | worse | quoted |
|---|---|---|---|---|
| §A1 worst prototype diff | 3.997e-15 | **4.219e-15** | AVX off | AVX off |
| §A1 bars that differ | 6,687 | 6,593 | — | "about 6,600" |
| §A1 length 250 | 1.554e-15 | 1.332e-15 | default | not quoted |
| §A1 both-spellings mutant | bit-equal | bit-equal | — | equality |
| §A2 worst loop diff | 8.882e-16 | 8.882e-16 | — | 8.882e-16 |
| §A3 worst lstsq diff | **3.109e-15** | 2.442e-15 | default | default |
| §A4 line reading | 1.0000000000000002 | same | — | both |
| §A4 Brownian / iid mean | 1.5137 / 1.9978 | same | — | both |
| §A4 per-frame medians | identical | identical | — | both |
| §D exact binary | bit-equal | bit-equal | — | equality |
| §D worst inexact | **5.906e-14** | 5.751e-14 | default | default |
| §D +1e6 shift | 4.006e-11 | 4.006e-11 | — | both |
| §D +1 bars moved | 30 | 35 | — | not pinned |
| §L ×3.7 on a window | 3.775e-15 | **3.997e-15** | AVX off | AVX off |
| §L ×-0.1 on a window | 2.887e-15 | 3.109e-15 | AVX off | AVX off |
| §L +1 on a window | 8.882e-16 | **1.332e-15** | AVX off | not quoted |
| §L +100 on a window | **1.354e-14** | 1.132e-14 | default | not quoted |
| §L -50 on a window | 0 | 0 | — | not quoted |
| §L time reversal | 4.441e-16 (59 windows) | **6.661e-16 (71)** | AVX off | AVX off |
| §L permutation / rotation | 1.0204 / 0.2771 | identical | — | both |
| §Z2 `@` rows moved at chunk 1 | 28 of 200 | 28 of 200 | — | not asserted |
| §Z2 shipped spelling | 0 of 200 | 0 of 200 | — | asserted |

Nothing in the test module pins a figure from the "—" rows as digits; the
counts that move (§A1's 6,687, §D's 30) are not asserted anywhere.

---

## §G — guards

### A window whose `L(k)` is zero at ANY spacing is a gap

**Three** different ways to reach it, and the module and the prototype agree
on all three:

| frame | `L(1..5)` of the first window | zero at | fires, module | fires, prototype |
|---|---|---|---|---|
| flat | `[0, 0, 0, 0, 0]` | every `k` | 0 | 0 |
| alternating (period 2) | `[29, 0, 3.222, 0, 1.16]` | `k = 2, 4` | 0 | 0 |
| period 4 (`100, 101, 103, 102`) | `[43, 14.5, 4.893, 0, 1.7168]` | `k = 4` only | 0 | 0 |

⚠ The last two rows are the cases a guard written as "`L(1) > 0`" alone would
have shipped as a reading: the path is anything but flat, and one or two of
its five curve lengths are still exactly zero. `log 0` has no slope, so the
window is a gap.

⚠ **And they are not the same case**, which an earlier draft of these
docstrings got wrong. On a period-4 path the lag-2 differences are `|c - a|`
and `|d - b|`, which do not vanish — only `L(4)` does. Both rows are
measured rather than inferred, the second by the `alternating` frame and the
third by
`tests/test_tf_higuchi_30.py::test_a_period_four_window_is_a_gap_but_for_a_different_reason`.

### A zero or negative close is a PRICE, not a gap

Nothing is divided by the close here, unlike every return-based port in this
family. Measured, one bad close planted at bar 150 or 700 of a 1,500-bar
walk:

| planted value | windows newly empty | bars moved before the plant |
|---|---|---|
| NaN | 30 | 0 |
| +inf | 30 | 0 |
| -inf | 30 | 0 |
| 0.0 | **0** | 0 |
| 1e-310 | **0** | 0 |

A negative close behaves the same: `fires` is unchanged at 1,471 and 30 bars
move. (`tf_dfa_100` blanks 100 windows for a zero close, because a zero
denominator makes its return infinite.)

### Floating-point error

Under `np.errstate(all="raise")` every one of the twelve frames is quiet.

**What the ±inf fold is for.** With `c = np.where(np.isfinite(c), c, np.nan)`
deleted:

| frame | mutant | where it lands |
|---|---|---|
| one inf close at bar 700 | **RAISED: invalid value encountered in divide** | `safe / safe[:, :1]` |
| two inf closes, bars 700 and 705 | **RAISED: invalid value encountered in subtract** | `win[:, k:] - win[:, :-k]` |

One infinite close is already enough. `inf - finite` is plain `inf`, so the
subtraction stays quiet, but every `L(k)` of that window is then `inf` and
the ratio is `inf / inf` — NaN *with* the invalid flag. ⚠ **That site exists
only because this port takes the logarithm of the RATIO:** the prototype's
`log L(k)` has no division there, so it is a raise the Gate D divergence
(§D) created and the fold pays for. Two infinite closes inside one 30-bar
window reach the flag one step earlier, at `inf - inf` in the subtraction
itself.

The shipped module is quiet on both, and the fold changes no value — the
rows it touches are blanked by the finiteness mask either way.
`test_the_infinity_fold_is_what_keeps_errstate_quiet` is parametrised over
both frames, so the weaker input is pinned too.

⚠ **An overflow IS reachable, at absurd magnitudes.** A frame of
`±1e307` closes is entirely finite, but `L(1)` of its first window is
1.75897e+308 — above `float64`'s maximum:

* under the default error state the column fires **0 of 300**: `inf / inf` is
  NaN and NaN propagates to the slope, so the overflow is a gap;
* an explicit `np.isfinite(curve)` limb would add nothing — a mutant with one
  fires 0 on the same frame — which is why the shipped guard is
  `curve > 0.0` alone;
* under `np.errstate(all="raise")` the frame **does** raise, at the strand
  sum and before any guard can act (`overflow encountered in reduce`).

So "no floating-point error is reachable" is a claim about ordinary price
magnitudes, which is how the test is named
(`test_no_floating_point_error_is_reachable_at_ordinary_magnitudes`).

### Degenerate frames and the argument guard

| frame | fires |
|---|---|
| all-NaN | 0 |
| all-zero | 0 |
| all-negative | 271 of 300 |
| all-inf | 0 |

`length` below `MIN_LENGTH = 10` falls back to the default: `None`, `0`, `1`
and `9` all give `TFHIGUCHI_30`; `10` gives `TFHIGUCHI_10` and `250` gives
`TFHIGUCHI_250`. The input series is not mutated.

---

## §L — what the column reads

Measured on 500 windows sampled from a synthetic 1,200-bar walk, through
`_higuchi_fd` — which
`test_the_row_helper_is_the_modules_arithmetic` pins to the shipped column
bit for bit on all ten firing frames, so these claims inherit that pin.

### §L1 — blind to the size and the sign of the window

| transform | max abs diff | bit-equal |
|---|---|---|
| ×-1 | 0 | yes |
| ×0.5 | 0 | yes |
| ×2 | 0 | yes |
| ×2**60 | 0 | yes |
| ×3.7 | 3.775e-15 (AVX off: 3.997e-15) | no |
| ×-0.1 | 2.887e-15 (AVX off: 3.109e-15) | no |
| +1 | 8.882e-16 (AVX off: 1.332e-15) | — |
| +100 | 1.354e-14 (AVX off: 1.132e-14) | — |
| -50 | 0 | — |

So it is not a volatility measure, and not a level measure either.

### §L2 — ⚠ time-reversal blind, and not order blind

| transform | max abs diff | median | windows moved |
|---|---|---|---|
| permutation | **1.0204** | 0.5355 | 500 of 500 |
| **time reversal** | **6.661e-16** | 0 | **71 of 500** |
| circular rotation | **0.2771** | 0.0613 | 500 of 500 |

(AVX off; the default dispatch reads 4.441e-16 and 59 windows for the
reversal, and the other two rows identically.)

Reversing a window maps each strand's multiset of lag-`k` differences onto
itself, so the reading is the same in exact arithmetic and the 71 movers are
the strand sums running backwards. ⚠ A reader coming from `tf_dfa_100` —
which a time reversal moves by up to 0.3698 — will not expect this. A
rotation splices the window's two ends together and the spliced jump is read
at every spacing, which is why it moves far more than the reversal and less
than a full permutation.

### §L4 — the overlap with the fork's own columns

⚠ **This is NOT Gate E.** Gate E compares against the ENGINE's 687
comparators (`compute_all` ∪ the `ml_features` manifest) over 89 real BIST
frames, and the launcher runs it. This section measures the FORK columns that
are nearest in meaning, on eight 1,500-bar synthetic frames, because three of
them landed **after** the 2026-10-24 screen whose stage-2 fork overlap the
issue quotes (`lean_hurst_100` 2026-11-11, `tf_dfa_100` and `tf_zero_cross_20`
2026-11-15).

Pooled over 12,000 bars, 11,757 of which `TFHIGUCHI_30` fires on:

| comparator | pooled rho | per-frame median abs rho |
|---|---|---|
| **`VHF_28`** | **-0.8901** | **0.7151** |
| `VHF_30` | -0.8861 | 0.7010 |
| (`TFHIGUCHI_100`) | 0.8210 | 0.4425 |
| `TS_CID_CE_20` | 0.6713 | 0.3448 |
| `TFDFA_30` | -0.6544 | 0.3236 |
| `LEAN_HURST_100` | -0.6418 | 0.1231 |
| `TFDFA_100` | -0.6221 | 0.1263 |
| `LEAN_HURST_30` | -0.3743 | 0.1462 |
| `TFSPECENTROPY_64` | 0.0761 | 0.0626 |
| `ENTROPY_10` | -0.0653 | 0.0161 |

`(TFHIGUCHI_100)` is this same column at another length — context, not a
shipped comparator.

**The leader is `vhf`, and the reason is structural.** `VHF_28` is
`(max - min) / sum|close diff|` over 28 bars, and `sum|close diff|` over the
window **is** this column's `L(1)`. Both are path-efficiency measures of the
same 28–30 bars, so the sign is negative: a rougher path (high dimension)
travels further per unit of range.

Frame by frame, because the pooled figure mixes eight different processes and
the between-frame spread inflates it:

| frame | rho vs `VHF_28` | rho vs `VHF_30` |
|---|---|---|
| walk | -0.6904 | -0.6798 |
| trend | -0.8284 | -0.8319 |
| range-bound | -0.6214 | -0.6149 |
| grid | -0.7230 | -0.7223 |
| heavy-tailed | -0.7073 | -0.6776 |
| jump | -0.7495 | -0.7418 |
| noise | -0.4721 | -0.4640 |
| smooth | -0.7490 | -0.7536 |

Per-frame |rho| runs **0.4721 .. 0.8284, median 0.7151** — below the owner's
0.90 line on every frame, and consistent with the screen's own stage-2 figure
of **0.6496** against `vhf:VHF_28` on 12 real frames. The column is **not** a
restatement of `vhf` at that line, and it is not a fork-overlap revert.

What it IS is a disclosure a miner has to see, which is why it appears in
five places: the module docstring, the 133-character dictionary cut, this
document, the test module's header and three tests
(`test_the_overlap_with_vhf_is_real_and_bounded_where_it_was_measured`,
`test_the_vhf_warning_survives_the_dictionary_cut`,
`test_the_vhf_overlap_measurement_is_still_owed_from_the_gate_e_run`).

#### OWED from the Gate E run

The receipt session must, before recording a verdict:

1. Check whether `vhf` is among the run's 687 comparators. The screen treated
   the fork overlap as a SEPARATE stage from Gate E, which says it is not —
   but that is the screen's arrangement, not a fact this worktree can read.
2. If it is not, measure Spearman rho of `TFHIGUCHI_30` against `VHF_28` over
   the same 89 ALTPORT-1 frames, pooled and per frame.
3. Read the result against the same **`r3-perframe-0.90`** band the ledger
   uses: STRUCK at pooled |rho| ≥ 0.90 or a per-frame median ≥ 0.90.
4. **revert `tf_higuchi_30` if it is** STRUCK on that comparison, exactly as
   a STRUCK Gate E row would be reverted; `docs/TfHiguchi30Measured.md` stays
   as the receipt either way.

`test_the_vhf_overlap_measurement_is_still_owed_from_the_gate_e_run` fails if
this block is dropped, so a green Gate E row cannot quietly settle it.

---

## §Z — cost, and the chunk budget

400,000 bars, default length, `tracemalloc` peak:

| budget | time ⚠ | peak | fires |
|---|---|---|---|
| shipped (`1 << 21`, 69,905 rows per chunk) | ~0.4–0.6 s | **57.4 MB** | 399,971 |
| unbounded (`1 << 40`) | ~0.6–0.8 s | 298.0 MB | 399,971 |

⚠ The time column is indicative and load-dependent — repeat runs on this
machine read 0.42 / 0.66 s and 0.61 / 0.74 s. The **peak** and the **fire
count** are the reproducible columns, and the peak is the figure that
justifies the budget; do not read a later wall-clock as a regression.

The budget cannot change a value: bit-equal at 1, 64, 999 and 10**9 rows.

### §Z2 — which step is sensitive to the block shape

| spelling | chunk 1 | 2 | 3 | 5 | 7 | 8 | 16 |
|---|---|---|---|---|---|---|---|
| shipped (summed dot product) | 0 of 200 | — | — | — | — | — | — |
| prototype's `@` | **28 of 200** | 0 | 0 | 0 | 0 | 0 | 0 |

Identical under both dispatches. With `@`, a row computed one per block
differs in its last bit from the same row inside the whole block, so a bar's
value would depend on how many bars came after it — which no causality sweep
over a single-chunk frame can see. Summing the five terms explicitly is
shape-stable and depends on no BLAS.

⚠ The `@` row is NOT asserted in the test module: it runs through BLAS, whose
dispatch is a property of the machine. What is asserted is the shipped
spelling's shape-stability (`test_the_arithmetic_does_not_depend_on_the_block_shape`),
which is plain numpy.

---

## §M / §W — the wiring and the generated docs

Five touch points, all present and pinned by
`test_the_five_wiring_touch_points`:

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/tf_higuchi_30.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .tf_higuchi_30 import tf_higuchi_30` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `"tf_higuchi_30"` |
| 4 | `pandas_ta/core.py` | `df.ta.tf_higuchi_30()` |
| 5 | `tests/test_tf_higuchi_30.py` | this port's suite |

Plus the documents the suite checks against the live package: `README.md`
(the `Category` headline, the `df.ta` count and the `statistics` list),
`docs/IndicatorDictionary.md` (regenerated by
`python docs/gen_indicator_dictionary.py`), `docs/MLCompanionContract.md`
(the ML-form counts, which `tests/test_ml_companions.py` compares to the
dictionary) and `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL`.

### §W — the dictionary cut

`docs/gen_indicator_dictionary.py::desc` squeezes the first paragraph after
the title and cuts it at **150** characters on a word boundary. Measured:

```
paragraph length: 133   slack: 17   truncated: False
How rough the last `length` closes are: 1 is a straight line, 1.5 a random
walk, 2 space-filling. ⚠ Near-restates `vhf` (|rho| 0.72).
```

Both things a dictionary reader must see fit inside the cut: what the number
means, and the `vhf` overlap. `desc` also rewrites `|` as `/` so the text
cannot break the markdown table it lands in, which is why the test compares
against `body.replace("|", "/")` rather than against `body`.
