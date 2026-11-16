# J-SAFEZONE-DIST — `j_safezone_dist`, measured

PandasTa issue [#121](https://github.com/TolgaUyanik/PandasTa/issues/121):
*distance to Elder's SafeZone stop, long (22, 2.5, lookback 3)*.

```
pen[T]  = max(low[T-1] - low[T], 0)            a down-penetration
avg[T]  = sum(pen, 22) / count(pen > 0, 22)    mean over bars that HAD one
raw[T]  = low[T-1] - 2.5 * avg[T-1]
stop[T] = max(raw[T-2], raw[T-1], raw[T])
J_SAFEZONE_DIST_22_2.5_3[T] = (close[T] - stop[T]) / close[T]
```

**Source.** jesse indicators (MIT), `safezonestop.py`, as issue #121 quotes
it: *"safezonestop.py (Rust core; Elder's definition used): L1 -
2.5\*mean(down-penetrations, 22), max over 3"*. The underlying rule is
Alexander Elder's SafeZone stop.
⚠ **jesse is not installed in this worktree and web access is unavailable**,
so nothing here is evidence about jesse's code.
`tests/test_j_safezone_dist.py::test_the_source_library_is_not_installed_here`
records that as a test, so the claim cannot rot into "checked against
jesse". Gate A checks the formula the ISSUE quotes, spelled two independent
ways. The issue says of the library itself: *"existence, not evidence"*.
⚠ **The long stop only.** jesse's function takes a direction; issue #121
names the long side, and no short-side column was screened at Gate E.

Everything below is printed by

```sh
python docs/measure_j_safezone_dist.py              # every section
python docs/measure_j_safezone_dist.py A1 D         # named sections
python docs/measure_j_safezone_dist_cpu.py D        # AVX-512/AVX2/FMA3 off
```

with four exceptions, named here rather than left for a reader to find:

* §E's prototype figures, which are issue #121's and were measured on the
  PROTOTYPE by the 2026-10-24 screen;
* §F and §F1's suite counts, which are pytest's;
* §C3's running-maximum count, which comes from
  `tests/test_j_safezone_dist.py::test_the_missingness_is_not_missing_at_random`;
* §L's "701 tagged columns", which comes from `docs/MLCompanionContract.md`.

Two fenced blocks (§B and §G1) are ABRIDGED — the lines in them are the
script's own, with later rows cut and the cut stated as prose outside the
fence. §D3's fence is the table only, with the margin paragraph quoted
below it as prose rather than pasted inside it. Every other fence is a
transcript.

| gate | verdict |
|---|---|
| **A** correctness | **pass** — bit-equal to an independent bar-by-bar oracle on 1,475 of 1,475 fired bars of each of six frames, and bit-equal to the screen prototype on all eight |
| **B** causality | **pass** — module caught 0 of 36 on every frame; six look-ahead mutants live and caught 3 .. 36 of 36; and the sweep's blind spot measured, with five more mutants the ORACLE catches |
| **C** reachability | **pass on synthetic** — 1,475 of 1,500 on each of six frames, 1,471 .. 1,475 distinct values, 0 exactly 0.0. **Real-data counts OWED** with Gate E |
| **D** scale-free | **pass** — ×8/×64 bit-identical on all six and at three price levels; ×10/×3.7/×0.1/×1.0000001 within 4.091e-11 (6.546e-11 under reduced dispatch); `0 < fires < n`; a level shift moves every fired bar |
| **E** attribution | **pending, run by issue-solver after this session** — see §E |
| **F** suites | PandasTa measured here (§F); the parent repo's suite is the launcher's |

---

## §A1 Gate A — the issue's formula, spelled independently

The oracle in `docs/measure_j_safezone_dist.py` shares no code with the
module: its own penetration loop, its own 22-bar window sums over plain
Python slices, its own 3-bar max.

```
  frame           fired  oracle  bit-eq   max |rel|   max |abs|
  walk             1475    1475    True   0.000e+00   0.000e+00
  trend            1475    1475    True   0.000e+00   0.000e+00
  range-bound      1475    1475    True   0.000e+00   0.000e+00
  grid             1475    1475    True   0.000e+00   0.000e+00
  heavy-tailed     1475    1475    True   0.000e+00   0.000e+00
  jump             1475    1475    True   0.000e+00   0.000e+00

  and on the two degenerate frames, where both are all-NaN:
  flat                0       0    True
  rising              0       0    True
```

Identical under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.

⚠ **Bit-equality here is a property of these frames, not a theorem.**
`pen.rolling(22).sum()` is pandas' online add-and-remove sum and the
oracle's is a fresh `sum()` over a 22-element slice; the two are not
obliged to round the same way. The test therefore asserts a 1e-12 bound on
both the absolute and the relative difference, and reports the measured
0.0 rather than pinning it.

## §A2 Gate A — the screen prototype, bit for bit

This is the limb that ties the port to the 2026-10-24 screen's Gate E
figures: the prototype and the module share pandas' rolling operators, so
the same operations run in the same order and bit-equality is legitimate.

```
  frame           fired  proto  bit-equal
  walk             1475   1475       True
  trend            1475   1475       True
  range-bound      1475   1475       True
  grid             1475   1475       True
  heavy-tailed     1475   1475       True
  jump             1475   1475       True
  flat                0      0       True
  rising              0      0       True
```

The module adds two guards the prototype has not — the input sanitation and
the final finite mask. On a clean frame both are no-ops, which is what this
table says; §G measures what they buy on a frame that is not clean.

## §A3 the warm-up, bar by bar

```
  pen      first defined at index   1
  avg      first defined at index  22
  raw      first defined at index  23
  stop     first defined at index  25
  column   first defined at index  25

  MIN_BARS = 26 = PERIOD 22 + LOOKBACK 3 + 1, and the first fired index is 25.
  on 25 bars: None
  on 26 bars: fires on 1 bar(s)
```

`MIN_BARS` is a floor on the INPUT and the warm-up on a frame that has a
down-penetration in every window. It is **not** the warm-up in general —
§C1's `flat` and `rising` never fire at all.

## §A4 WHICH MEAN — `sum / count`, not `sum / 22`

The load-bearing reading of the issue's quote — not the only one it leaves
open; the second is whether `avg` is lagged with `L1`, priced in §B2 as
`today-avg` and logged in the decisions table. Elder averages the
penetrations themselves, over the bars that HAD one; the alternative
divides by 22 and
counts the quiet bars as zeros. The issue's prototype line says *"mean over
bars with a penetration"* and the module follows it.

```
  frame           shipped   per-22  shared      rho   max |abs|  ship>alt
  walk               1475     1475    1475   0.9626   2.433e-02      1475
  trend              1475     1475    1475   0.9378   2.239e-02      1475
  range-bound        1475     1475    1475   0.9579   5.832e-02      1475
  grid               1475     1475    1475   0.9614   2.400e-02      1475
  heavy-tailed       1475     1475    1475   0.9488   1.088e-01      1475
  jump               1475     1475    1475   0.9705   2.092e-02      1475
  rising                0     1475       0      nan         nan         0
```

Two differences, and the second is the sharper one.

* The per-22 mean is smaller on any window with a quiet bar, so the stop is
  HIGHER and the distance SMALLER — on **8,850 of 8,850** shared bars, every
  one, at Spearman 0.9378 .. 0.9705.
* The per-22 reading **never goes NaN**. On `rising` it answers on 1,475
  bars where this column correctly has none: there has been no
  down-penetration, so there is no average of them to take.

Identical under reduced CPU dispatch.

## §B Gate B — causality

Bar T reads `low` up to T − 1 and `close` at T. The sweep perturbs every
bar ≥ j by ×1.03 on BOTH series and asks whether any bar < j moved.

```
  the shipped module, against the blind suffix sweep:
    walk           caught  0 of 36
    trend          caught  0 of 36
    range-bound    caught  0 of 36
    grid           caught  0 of 36
    heavy-tailed   caught  0 of 36
    jump           caught  0 of 36
```

Six look-ahead mutants, read off `pandas_ta/trend/j_safezone_dist.py`,
edited and `exec`'d in memory. Every one is LIVE on every frame:

```
  mutant         frame            live   caught
  pen-lead-2     walk             True    11 of 36
  pen-lead-2     trend            True    21 of 36
  pen-lead-2     range-bound      True    13 of 36
  pen-lead-2     grid             True     9 of 36
  pen-lead-2     heavy-tailed     True    13 of 36
  pen-lead-2     jump             True    14 of 36
  avg-lead-2     walk             True     8 of 36
  avg-lead-2     trend            True     7 of 36
  avg-lead-2     range-bound      True    10 of 36
  avg-lead-2     grid             True     6 of 36
  avg-lead-2     heavy-tailed     True     8 of 36
  avg-lead-2     jump             True     3 of 36
  raw-lead       walk             True    36 of 36
  raw-lead       trend            True    36 of 36
  raw-lead       range-bound      True    33 of 36
  raw-lead       grid             True    35 of 36
  raw-lead       heavy-tailed     True    36 of 36
  raw-lead       jump             True    36 of 36
  stop-lead-2    walk             True    34 of 36
  stop-lead-2    trend            True    35 of 36
  stop-lead-2    range-bound      True    32 of 36
  stop-lead-2    grid             True    34 of 36
  stop-lead-2    heavy-tailed     True    34 of 36
  stop-lead-2    jump             True    35 of 36
```

Abridged: the script prints six more rows for `close-lead` and six for
`output-early`. The two it starts with are

```
  close-lead     walk             True    36 of 36
  [five rows cut: trend, range-bound, grid, heavy-tailed, jump]
  output-early   walk             True    36 of 36
  [five rows cut: trend, range-bound, grid, heavy-tailed, jump]
```

and every one of those ten cut rows is `True` and `36 of 36`.

⚠ **A count below 36 is the FORMULA's, not a gap in the mutant.**
`clip(lower=0)`, the mean over the hits and `rolling(3).max()` all discard
information, so raising a suffix by 3% moves the output only at the offsets
where the perturbed bar is one those three operators select. The gate is
"caught at least once on every frame", and the lowest count anywhere is
**3 of 36** (`avg-lead-2` on `jump`). The test asserts ≥ 1 for that reason.

Identical under reduced CPU dispatch.

### §B1 how LOUD each catch is

At the first caught offset: how many bars before it moved, and by how much.

```
  mutant         frame              j  moved   max |diff|
  pen-lead-2     walk            1467      1    5.144e-03
  pen-lead-2     heavy-tailed    1470      1    6.335e-03
  avg-lead-2     walk            1467      1    3.399e-04
  avg-lead-2     heavy-tailed    1469      1    1.330e-03
  raw-lead       walk            1464      1    2.996e-02
  raw-lead       heavy-tailed    1464      1    2.183e-02
  stop-lead-2    walk            1464      1    2.709e-02
  stop-lead-2    heavy-tailed    1464      1    1.780e-02
  close-lead     walk            1464      1    2.874e-02
  close-lead     heavy-tailed    1464      1    2.871e-02
  output-early   walk            1464      1    2.874e-02
  output-early   heavy-tailed    1464      1    2.858e-02
```

The smallest catch, 3.399e-04, is seven orders above the 6.5e-11 an inexact
rescale costs (§D2), so none of these is a rounding accident. The test
asserts 1e-5. Identical under reduced CPU dispatch.

### §B2 the sweep's BLIND SPOT, measured rather than left open

⚠ **This is the finding of this port's Gate B, and it is stated here rather
than left for a reader to work out.** Note before the table that
`today-avg` is not merely a wrong version: it is the issue's quote taken
LITERALLY, with the mean evaluated at T rather than lagged with `L1`. It
is in this table because it is causally wrong in the trading sense, and
the decisions table logs the choice that rejected it.
The stop carries TWO `shift(1)`s
between a penetration and the output. An edit that leads by ONE bar early
in the chain is absorbed by them: the output then reads bar T's OWN low —
wrong, because the stop a trader could have had in the market is
yesterday's — without reading any LATER bar. The suffix sweep is blind to
all five such edits, and is right to be: they are not look-aheads. Gate A's
oracle catches every one.

```
  mutant       frame               swept  vs oracle      rho   max |abs|
  pen-lead-1   walk             0 of 36      False   0.8492   2.305e-02
  pen-lead-1   heavy-tailed     0 of 36      False   0.6405   1.368e-01
  avg-lead-1   walk             0 of 36      False   0.9889   9.970e-03
  avg-lead-1   heavy-tailed     0 of 36      False   0.9829   9.389e-02
  stop-lead-1  walk             0 of 36      False   0.8206   3.484e-02
  stop-lead-1  heavy-tailed     0 of 36      False   0.7952   4.127e-01
  today-low    walk             0 of 36      False   0.8362   2.898e-02
  today-low    heavy-tailed     0 of 36      False   0.8295   3.188e-01
  today-avg    walk             0 of 36      False   0.9929   9.970e-03
  today-avg    heavy-tailed     0 of 36      False   0.9873   9.389e-02
```

`vs oracle = False` is a CATCH, not a failure: it is the oracle rejecting
the mutant. The counts are pinned in BOTH directions — a sweep that started
catching these would mean the module's shift structure had changed — and
this is why the §B mutants lead by two bars wherever the chain allows it.

## §C Gate C — reachability

### §C1 synthetic

```
  frame           fired    of  distinct        min        max     <0   ==0
  walk             1475  1500      1475    -0.0345     0.0506    222     0
  trend            1475  1500      1475    -0.0194     0.0521    107     0
  range-bound      1475  1500      1475    -0.1039     0.1234    203     0
  grid             1475  1500      1471    -0.0316     0.0576    175     0
  heavy-tailed     1475  1500      1475    -0.3262     0.1413    218     0
  jump             1475  1500      1475    -0.0410     0.3375    213     0
  flat                0  1500         0          -          -      0     0
  rising              0  1500         0          -          -      0     0
```

Over the 8,850 fired bars of the six varying frames: −0.3262 .. 0.3375,
negative on 1,138 of them, exactly 0.0 on none.

⚠ **`flat` and `rising` fire NOWHERE, and `rising` is the sharp one.**
`avg` is the mean over the bars that HAD a down-penetration, and neither
frame has one — but every bar of `rising` MOVES. So the missingness is not
"no data"; it is "no downside". §C3 states what that means for a consumer.

Identical under reduced CPU dispatch.

### §C2 real data — **OWED**

Gate E is run by issue-solver after this session, and its 89 ALTPORT-1 BIST
frames are where the real-data fired/non-zero counts come from. The receipt
session records them here together with the ledger row. Everything in this
document is synthetic until then.

### §C3 the missingness is INFORMATIVE, and that is a consumer contract

`avg` is NaN exactly when the last 22 bars hold no down-penetration at all,
so the column is blank **precisely where a long position has had an
unusually easy ride**. It is not missing at random, and the three obvious
treatments are three different decisions:

* drop the rows — drops the calmest advances out of the training set;
* forward-fill — carries a stale stop through exactly the stretch where the
  stop would have trailed up fastest;
* fill with a constant — asserts a distance the market never offered.

Measured, rather than argued: on `walk` the column fires on 1,475 of 1,500
bars; replace its lows with their own running maximum (the same path with
every drawdown removed) and it fires on **0**. That is
`test_the_missingness_is_not_missing_at_random`.

## §D Gate D — scale-free

### §D1 ×8 / ×64, bit-identical

```
  frame           fired         x8        x64
  walk             1475       True       True
  trend            1475       True       True
  range-bound      1475       True       True
  grid             1475       True       True
  heavy-tailed     1475       True       True
  jump             1475       True       True
```

By construction: every step up to `stop` is homogeneous of degree 1 in the
price, a ×2^k rescale is exact at every one of them, and the final division
cancels the factor. Identical under reduced CPU dispatch.

### §D2 ×10 / ×3.7 / ×0.1 / ×1.0000001, a tolerance

```
  frame                  x10        x3.7        x0.1  x1.0000001
  walk             3.290e-12   2.659e-12   2.751e-12   5.441e-12
  trend            3.769e-12   3.538e-11   4.091e-11   1.643e-11
  range-bound      9.638e-13   6.513e-13   5.013e-13   9.736e-13
  grid             3.070e-11   1.244e-11   6.395e-12   1.600e-11
  heavy-tailed     4.160e-12   4.486e-12   7.544e-12   7.492e-12
  jump             2.166e-12   8.278e-12   1.896e-11   3.001e-12

  worst cell: 4.091e-11   (the tests assert 1e-9)
```

⚠ **This is the only section whose numbers move between numpy dispatches,
§Z's wall-clock aside** — §Z's milliseconds move between any two runs on
either dispatch and disclaim themselves. Every other section above and
below was re-run with `AVX512F AVX512_SKX AVX2 FMA3` disabled and printed
the same cells. Here, disabled:

```
  frame                  x10        x3.7        x0.1  x1.0000001
  walk             3.290e-12   2.659e-12   2.751e-12   5.441e-12
  trend            6.546e-11   3.538e-11   4.091e-11   1.643e-11
  range-bound      4.820e-13   8.247e-13   1.205e-12   6.327e-13
  grid             3.070e-11   1.244e-11   6.395e-12   1.600e-11
  heavy-tailed     4.992e-12   3.262e-12   2.263e-11   7.492e-12
  jump             2.060e-12   8.278e-12   8.124e-12   7.830e-12

  worst cell: 6.546e-11   (the tests assert 1e-9)
```

Both worst cells are more than an order below the asserted 1e-9, which is
why the test pins the bound and this document carries the digits.

### §D3 extreme price levels

```
     level  fired       x8      x64    interm, x8   interm, x64
     1e-06   1475     True     True     8.024e-06     6.419e-05
     1e+06   1475     True     True     8.024e+06     6.419e+07
    1e+100   1475     True     True    8.024e+100     6.419e+101
```

and the margin, printed by the same section:

> The largest intermediate anywhere in the chain over all SIX cells is
> 6.419e+101, against DBL_MAX 1.798e+308 — a factor of 2.800e+206, so the
> rescale does not come near overflowing and the bit-identity is the same
> claim as §D1's.

⚠ Three review rounds built this one table, and each round's correction is
worth keeping visible. Round 2 found four prose surfaces asserting the
`x64` cells while only `x8` had been run at these levels. Round 3 found
the replacement sentence asserting "four orders inside DBL_MAX" when the
factor is 2.800e+206 — so the margin is PRINTED by
`_largest_intermediate()` now. Round 4 found that margin quoted "over
those six cells" when only the three `x64` ones had been walked, which is
why there are two `interm` columns.

### §D4 `0 < fires < n`, and a level SHIFT is not invariant

```
  frame           fires     n   0<f<n  shift +10 moves
  walk             1475  1500    True    1475 of 1475
  trend            1475  1500    True    1475 of 1475
  range-bound      1475  1500    True    1475 of 1475
  grid             1475  1500    True    1475 of 1475
  heavy-tailed     1475  1500    True    1475 of 1475
  jump             1475  1500    True    1475 of 1475
```

The shift column is what keeps the ×8 bit-identity from being vacuous: a
constant column would pass the rescale test too, and this one does not pass
the shift test.

## §E Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

`tests/test_j_safezone_dist.py::test_the_gate_e_row_is_owed_and_not_yet_recorded`
asserts that `docs/gate_e_ledger.csv` has no row for `j_safezone_dist`, and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports it as owed. The receipt session records the row, fills in §C2 and
replaces that test. Until then the column is on `dev` unmeasured, under the
owner's 2026-11-01 "owed, not failed" rule: if the run is STRUCK, it is
reverted or waived before the release.

### §E0 what the screen measured, on the PROTOTYPE

⚠ **A prototype is not a port.** These are issue #121's numbers, from run
`screen_r2_20261024` (`gate_e_overlap.py run --module ind_screen_r2 --fn
screen`, Backtesting `main` b2d94243, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 = 687 comparators, canary bit-equal):

| | |
|---|---|
| max \|ρ\| | **0.7059** vs `Dist_to_hma_pct` (manifest), n = 396,606 |
| top-5 per-frame max median | **0.7249** |
| verdict | **SHIP** (under the 0.76 line, `r3-perframe-0.90`) |
| next comparators | `Dist_to_hma_pct_Pctl` 0.6979, `cfo` 0.6857 |

What §A2 adds is that the shipped module is BIT-EQUAL to that prototype on
all eight frames here, so the port and the screened candidate are the same
arithmetic where both fire. That is a reason to expect a similar band, not
a measurement of this module on real data.

The screen's stage-2 fork overlap (scale-free `Category` outputs at
defaults, 12 real frames — not Gate E) put
`linreg_channel:LINREG_LOWER_2_DIST_PCT` nearest at max \|ρ\| 0.7578,
per-frame max median 0.7555: not a restatement at the 0.90 line. §L
measures the same pair on this fork's synthetic frames.

## §F Gate F — suites

Run in this worktree, `python -m pytest -q`: **2 failed, 11,845 passed,
86 skipped**. Both failures are expected and neither is this port's
arithmetic — the `AlternativeRepos`-dependent talib CSV test that CI
deselects, and the owed Gate E row, which reports `['j_safezone_dist']`
and nothing else. §F1 has the output.

The module's own suite: **203 tests**, and the same 203 under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` via
`python docs/measure_j_safezone_dist_cpu.py`, which prints the dispatchable
features still enabled and refuses to run if any of the four survived.

The parent repo's suite is the launcher's: it is not on this machine.

## §G the guards, and what each one buys

### §G1 a bad price EMPTIES BARS — unlike `j_damiani`

```
  leg     value  plant  fired  emptied  first   last  contiguous
  low       nan    100   1450       25    101    125        True
  low       nan    400   1450       25    401    425        True
  low       nan    700   1450       25    701    725        True
  low       nan   1100   1450       25   1101   1125        True
  low       nan   1499   1475        0     -1     -1       False
  low       inf    100   1450       25    101    125        True
  low       inf    400   1450       25    401    425        True
  low       inf    700   1450       25    701    725        True
  low       inf   1100   1450       25   1101   1125        True
  low       inf   1499   1475        0     -1     -1       False
  low      -inf    100   1450       25    101    125        True
  low      -inf    400   1450       25    401    425        True
  low      -inf    700   1450       25    701    725        True
  low      -inf   1100   1450       25   1101   1125        True
  low      -inf   1499   1475        0     -1     -1       False
  close     nan    100   1474        1    100    100        True
  close     nan    400   1474        1    400    400        True
  close     nan    700   1474        1    700    700        True
  close     nan   1100   1474        1   1100   1100        True
  close     nan   1499   1474        1   1499   1499        True
  [ten `close` rows cut here -- see the note below the fence]

  A plant at the LAST bar is the one that cannot empty 25 bars,
  because the frame ends first. Everything before the first
  emptied bar is bit-identical:
    low=NaN at   100: bars < 100 bit-identical: True
    low=NaN at   700: bars < 700 bit-identical: True
```

Abridged where the fence says so: the ten cut rows are the `close` leg's
five `+inf` and five `-inf` plants, and all ten are identical to the five
`close`/`nan` rows above them (`emptied 1`, `first = last = plant`,
contiguous `True`). Every other line in the fence is the script's.

One bad LOW blanks exactly 25 bars, T+1 .. T+25, contiguous, and the count
is the chain's: the two NaN penetrations at T and T+1 spoil the
`PERIOD + 1` = 23 rolling-sum windows ending T .. T+22; `avg.shift(1)`
TRANSLATES that run to T+1 .. T+23 without widening it; and
`rolling(LOOKBACK).max()` adds `LOOKBACK − 1` = 2 more. 23 + 0 + 2 = 25 =
`PERIOD + LOOKBACK`. A bad CLOSE blanks exactly its own bar, because the
close enters only the last division. A plant at the LAST bar blanks nothing
— the frame ends before the 25 bars do.

⚠ So **the NaNs are a leading prefix on a clean frame and are NOT in
general**, unlike `j_damiani`'s. A mid-series hole is reachable, and every
bar before it is bit-identical: the contamination does not run backwards,
and it does not run forwards past the 25 either.

Identical under reduced CPU dispatch.

### §G2 the `hits` divisor guard

```
  frame           guarded   bare  bit-equal
  walk               1475   1475       True
  trend              1475   1475       True
  range-bound        1475   1475       True
  grid               1475   1475       True
  heavy-tailed       1475   1475       True
  jump               1475   1475       True
  flat                  0      0       True
  rising                0      0       True
```

`total > 0` implies `hits > 0` — a counted penetration is positive — so the
bare form's only division by zero is `0 / 0`, which is NaN either way. What
the guard buys is that the decision is this module's rather than numpy's,
stated where a reader looks for it. It is **not** claimed to change a
number, and the table is how that is known.

### §G3 the final finite guard is NOT a no-op

```
  frame           bit-equal
  walk                 True
  trend                True
  range-bound          True
  grid                 True
  heavy-tailed         True
  jump                 True
  flat                 True
  rising               True

  route                                pen max    sum(22)       stop              guarded            unguarded
  1. subtraction (+max to -max)            inf    all NaN    all NaN        inf 0 nan 120        inf 0 nan 120
  2. rolling sum (alternating max)   1.80e+308    all NaN    all NaN        inf 0 nan 120        inf 0 nan 120
  3. division (1e300 / 1e-300)       8.54e+297  5.29e+298  1.00e+300        inf 0 nan 120        inf 95 nan 25

  probe                            inf  warm-up  extra     blanked bars
  one +inf at bar 40                 0       21     22         40 .. 61
  two DBL_MAX at bars 40, 41         1       21     21         42 .. 62
```

⚠ **Finite inputs leave THREE arithmetic routes to an infinity, not one,
and an earlier draft of this section and of the module docstring said the
final division was the only one.** They are numbered in the order they
occur in the chain, and the table's own row labels carry those numbers —
review round 3 found three artefacts using three different numberings for
one measurement:

1. overflow in `low.shift(1) - low` — which needs a NEGATIVE low, and the
   input guard allows one, because `low` is checked for finiteness only;
2. overflow in `pen.rolling(22).sum()` — eleven penetrations near DBL_MAX
   inside one 22-bar window;
3. overflow in `(close - stop) / close` — a stop near 1e+300 over a close
   near 1e-300.

**Only route 3 reaches the output**, and that is measured rather than
argued: the `sum(22)` column above is `all NaN` for routes 1 and 2.
pandas' `rolling.sum` is COMPENSATED (Kahan), and once the compensation
term goes NaN every later window does too.

⚠ **But that is not a rule, and the two probe rows are what say so.** They
are 81 bars with the bad value in the MIDDLE on purpose: `min_periods`
blanks `PERIOD − 1` = 21 windows of ANY frame, so a 31-bar probe with the
bad value at bar 0 cannot tell those 21 from the contamination — an
earlier draft of this paragraph used such a probe and read its 22 NaNs as
22 contaminated windows.

* One `+inf` at bar 40: **0** infinite readings, and all 22 windows that
  hold it (bars 40 .. 61) read NaN.
* Two DBL_MAX at bars 40 and 41: **1** infinite reading — the window in
  which the overflow first happens — with only the 21 after it (bars
  42 .. 62) NaN.

So "the compensated sum absorbs an overflow" is true of routes 1 and 2's
frames and is NOT a guarantee. That is why the final mask stays, and why
the assertion that matters is on this MODULE's output
(`test_routes_1_and_2_never_reach_the_output`, 0 infinite readings with
AND without the mask) rather than on a pandas internal.
`test_the_rolling_sums_overflow_behaviour_is_not_uniform` pins both probe
rows, including the `inf 1`, so a pandas upgrade that changes either is a
loud failure here.

On route 3 this line is the only thing between the column and 95 infinite
readings out of 120, and on all eight ordinary frames it is bit-equal to
the unguarded form. An infinite feature is worse than a missing one, so it
is masked rather than shipped.

### §G4 degenerate frames raise nothing

```
  zeros      fired   0 of 60, infinite   0
  negative   fired   0 of 60, infinite   0
  subnormal  fired   0 of 60, infinite   0
  huge       fired   0 of 60, infinite   0
```

A constant frame of any of those four reads NaN everywhere — a constant
series has no down-penetration — and raises nothing on the way. Separately,
a non-positive or subnormal CLOSE is dropped by the input guard rather than
dividing: a zero close would make the ratio infinite and a negative one
would silently flip the column's sign.

### §G5 frames below `MIN_BARS`, and a constant-NaN frame

```
  0 bars (< MIN_BARS 26): None
  1 bars (< MIN_BARS 26): None
  5 bars (< MIN_BARS 26): None
  100 all-NaN bars: fired 0
```

`verify_series(..., MIN_BARS)` returns `None` below 26 bars, which is this
fork's convention and what `df.ta.strategy()` expects.

## §L what the column reads — in-fork overlap, SYNTHETIC

**Seven neighbours, chosen as the nearest questions this fork already
answers** — not a sweep of the 356 registered indicators or the 701 tagged
columns. Scale-free, at their defaults, Spearman against the shipped
column, over the six varying frames.

```
  comparator                      walk     trend range-bou      grid heavy-tai      jump  max |rho|
  LINREG_LOWER_2_DIST_PCT       0.7040    0.6565    0.6936    0.6970    0.6371    0.6995     0.7040
  RVI_14                        0.5079    0.4518    0.5174    0.4620    0.3905    0.4953     0.5174
  NATR_14                      -0.0322    0.2053   -0.0634   -0.0112    0.0087   -0.1027     0.2053
  ADX_14                       -0.0074   -0.1557   -0.0129   -0.0540    0.0693    0.0210     0.1557
  VHF_28                       -0.0196   -0.0839   -0.0101   -0.0652    0.0948    0.0442     0.0948
  MASSI_9_9                    -0.0911   -0.0076   -0.0229   -0.0025   -0.0873   -0.0545     0.0911
  CHOP_14_1_100                 0.0671   -0.0687    0.0161    0.0229   -0.0113    0.0084     0.0687
```

⚠ **A disclosure, not a gate.** The 687 Gate E comparators hold no
pandas_ta port, so a Gate E run cannot see any of these.

The nearest is the same column the screen found — `linreg_channel`'s
`LINREG_LOWER_2_DIST_PCT`, 0.7040 here on six synthetic frames against
0.7578 there on 12 real ones — and the agreement is not a coincidence: both
are distances from the close down to a lower band, one built from a
regression channel and one from Elder's penetration average. Below the 0.76
disclosure line on both universes, so neither is a restatement; it is the
pair to watch if either column's definition moves.

⚠ `RVI_14` at 0.5174 is second, and it is worth naming by module path
rather than lumping it in: `pandas_ta/volatility/rvi.py`, the Relative
Volatility Index, a rolling-stdev reading. So "the volatility family is
near zero" is NOT what this table says. Of the FIVE dispersion readings
among the seven, four sit at or under 0.21 — `natr` 0.2053 and `massi`
0.0911 (`pandas_ta/volatility/`), `chop` 0.0687 and `vhf` 0.0948
(`pandas_ta/trend/` choppiness filters, not `volatility/`) — and `rvi` at
0.5174 is the one that does not. Nothing else among the seven reaches
0.21.
The reading that survives both halves of that is the modest one: this
column is mostly a POSITION relative to a stop rather than a volatility
level, even though a downside-range average is inside it, and `rvi` is the
one neighbour that picks up the average rather than the position.

Identical under reduced CPU dispatch.

## §W the dictionary's 150-character cut

```
  first paragraph (148 chars):
    How far the close stands above Elder's SafeZone long stop, in fractions of the close. The stop trails yesterday's low by 2.5 mean down-penetrations.

  after the cut (148 chars):
    How far the close stands above Elder's SafeZone long stop, in fractions of the close. The stop trails yesterday's low by 2.5 mean down-penetrations.

  survives whole: True
```

`docs/IndicatorDictionary.md` is what `CLAUDE.md` tells a reader to consult
before judging a column, and it prints this paragraph cut at 150
characters. The test pins that the sentence is not cut.

## §Z cost

⚠ One machine, one run. Nothing else in this document depends on either,
and no claim anywhere divides by these numbers.

```
     1,500 bars:     1.75 ms     1.166 us/bar   peak    0.1 MB
    50,000 bars:     6.06 ms     0.121 us/bar   peak    3.3 MB
   400,000 bars:    40.41 ms     0.101 us/bar   peak   26.0 MB
```

(Three review rounds re-ran this section and the milliseconds moved every
time — 1.80/6.17/40.57 on the first run, these on the last. That is why
nothing anywhere divides by them.)

Two rolling sums, one rolling max, three shifts (`low.shift(1)` in the
penetration, `lo.shift(1)` and `avg.shift(1)` in the raw stop) and two
divisions (the mean over the hits, and the final `/ close`) — linear in
bars, with no Python loop.

---

## Verdict

**SHIP, with Gate E pending.** Gates A, B and D are met on synthetic
frames; Gate C is met on synthetic frames and its real-data limb is owed
with Gate E; Gate F is measured here for PandasTa and is the launcher's for
the parent repo.

Three things a reader should carry away rather than the gate table:

1. **The missingness is informative** (§C3). This column is blank exactly
   where a long has had an easy ride, so how a consumer fills it is a
   decision about trend, not about missing data.
2. **The sweep alone would not have been enough** (§B2). Five wrong
   versions of this module are invisible to a future-perturbation sweep
   because the stop's two `shift(1)`s absorb a one-bar lead. Gate B here is
   the sweep AND the oracle.
3. **Which mean is load-bearing** (§A4). `sum / count` and `sum / 22` are
   different columns, and the second one answers where this one must not.

## Decisions this session made, and why

| decision | why | where it is measured |
|---|---|---|
| category `trend` | it is a trailing STOP distance, and the fork's other stops (`cksp`, `vstop`, `vstop2`, `tvstop`, `psar`) are all in `trend`. ⚠ §L does not settle it either way: the nearest of the seven neighbours is a channel distance at 0.7040, and the SECOND-nearest is `pandas_ta/volatility/rvi` at 0.5174 | §L, ASSUMPTIONS 1 |
| 22 / 2.5 / 3 as module constants, not arguments | the issue's quote and the screen prototype spell exactly these three, and that triple is the whole of what Gate E measured; `docs/gate_e_ledger.py` refuses a run at non-default parameters anyway | — |
| `sum / count`, not `sum / 22` | Elder's definition, and the issue's prototype line says "mean over bars with a penetration" | §A4 |
| `avg` is LAGGED with `L1` (`avg.shift(1)`), not evaluated at T | the issue's quote "L1 - 2.5\*mean(down-penetrations, 22)" does not settle it. The prototype lags it (`ind_screen_r2.py:138`, `avg.shift()`), and the unlagged form makes bar T's stop depend on bar T's own low — a stop no trader could have had in the market. Priced rather than assumed: Spearman 0.9929 / 0.9873 against the oracle, max \|abs\| 9.970e-03 / 9.389e-02 | §B2, `today-avg` |
| sanitise `low` to finite only, `close` to finite-positive-normal | `low` enters through DIFFERENCES and is meaningful at any finite level; `close` is the DIVISOR, so a zero overflows it and a negative flips the column's sign | §G3, §G4 |
| keep the final finite mask | on the ONE of three overflow routes that reaches the output, it is the only thing between the column and 95 infinite readings out of 120, and it is bit-equal to the bare form on all eight ordinary frames. ⚠ The other two routes die in pandas' compensated `rolling.sum`, not in this mask | §G3 |
| look-ahead mutants lead by TWO bars where the chain allows | a one-bar lead is absorbed by the stop's own two shifts and is not a look-ahead at all | §B2 |
| assert "caught ≥ 1", not "36 of 36" | the counts are 3 .. 36 because the formula's `clip`, mean-over-hits and `rolling.max` discard information | §B |

## ASSUMPTIONS

`AskUserQuestion` is unavailable in this headless session, so each of these
took the smaller-scope reading and is logged rather than asked.

1. **Category `trend`.** The alternative was `volatility` (a penetration
   average is a downside-range statistic). `trend` was taken on the
   PRECEDENT: the shipped column is a position relative to a trailing
   stop, and the fork's other stops — `cksp`, `vstop`, `vstop2`, `tvstop`,
   `psar` — are all in `trend`. §L is consistent with that but does not
   settle it, and the honest reading of §L is split: the nearest column of
   the seven is a channel distance (`LINREG_LOWER_2_DIST_PCT`, 0.7040),
   but the second-nearest IS from `pandas_ta/volatility/` — `rvi`, the
   Relative Volatility Index, at 0.5174 — while the other two
   volatility-category comparators, `natr` and `massi`, read 0.2053 and
   0.0911. An earlier draft of this line said "the four volatility
   comparators sit at |ρ| ≤ 0.21", which was selected evidence: two of
   those four (`vhf`, `chop`) are `pandas_ta/trend/` choppiness filters,
   and `rvi` was left out.
2. **One column, long side only.** The issue's title and quote name the
   long stop. A short-side column would be a second, unscreened feature.
3. **No parameters.** See the decisions table.
4. **Column name `J_SAFEZONE_DIST_22_2.5_3`.** The fork's convention is
   that parameters are in the name (`BBU_20_2.0` carries a decimal point
   too), even where they are constants — `J_DAMIANI_13_40` is the nearest
   precedent.

## §F1 suite output

`python -m pytest -q`, this worktree, 2026-11-16:

```
FAILED tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows
FAILED tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one
2 failed, 11845 passed, 86 skipped, 97137 warnings in 296.60s (0:04:56)
```

(The run after review round 2, which added ten tests to this module. The
round-1 run read `2 failed, 11835 passed, 86 skipped`; the two failures and
the 86 skips are the same.)

Both failures are expected and neither is this port's arithmetic.

* `test_regenerating_reproduces_the_committed_rows` needs the sibling
  `../AlternativeRepos` checkout, which is not on this machine. CI
  deselects it by name (`CLAUDE.md`, *CI*).
* The Gate E row is OWED, and the message names this port and nothing
  else:

  ```
  no Gate E ledger row for ['j_safezone_dist'] (new to Category, or a
  grandfathered indicator whose default columns grew). Run Gate E
  (CLAUDE.md, 'Gate E harness'), then `python docs/gate_e_ledger.py
  record <run dir> --measured YYYY-MM-DD`
  ```

  Under `GATE_E_PENDING_OK=1`, which `ci.yml` and `gate-e-guard.yml` set
  for PRs into `dev`, that is a skip rather than a failure.

⚠ **The 86 skips are NOT one cause**, and the first draft of this section
said they were. Measured with `python -m pytest -q -rs`, grouped by reason:

| n | cause |
|---|---|
| 45 | the sibling `../AlternativeRepos` CSVs are not checked out — `altrepo_tti.csv` (9 + 1), `altrepo_talib.csv` (6), `altrepo_pandas_ta_classic.csv` (6 + 1), `altrepo_ptclassic_divergence.csv` (2 + 3), plus `test_gap_rows_are_derived.py` (9), `test_indicator_list_tables.py` (4), `test_prose_counts_match_the_csvs.py` (3) and `test_altport2_ports.py:399` |
| 21 | `tests/config.py:23` — `data/SPY_D.csv` is gitignored, so the whole upstream correlation suite skips at import. This is the number `CLAUDE.md` quotes |
| 14 | the parent repo's frame cache is absent — `Backtesting/datastore/cache` (6 + 4 + 2) and `test_altport2_ports.py` (1 + 1) |
| 3 | per-port degenerate comparators — `test_ts_aggac_60.py` (2), `test_tf_iqr_ret_60.py:610` (1) |
| 1 | `test_candle_patterns_reachable.py:131` — TA-Lib **is** installed here |
| 1 | `test_pine_coverage_csv.py:116` — the `docs/pine/` corpus is untracked by design |
| 1 | `test_multil_length_grid.py:298` — `Backtesting/TODO.md` absent |

That sums to 86. None of them is this port's.

`python docs/measure_j_safezone_dist_cpu.py`:

```
NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512_SKX AVX2 FMA3'
dispatchable features still enabled: ['SSSE3', 'SSE41', 'POPCNT', 'SSE42',
  'AVX', 'F16C', 'AVX512CD', 'AVX512_CLX', 'AVX512_CNL', 'AVX512_ICL']
203 passed in 6.90s
```
