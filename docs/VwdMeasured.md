# VWD — measured

PandasTa issue **#202**: *B3-VWD-14 — volume-weighted MA-difference
oscillator (VWD; 7, 14)*. Shipped as `pandas_ta/momentum/vwd.py`, one column
**`VWD_7_14`**.

```
madif[T] = (SMA(close, 14)[T] - EMA(close, 7)[T]) / EMA(close, 7)[T] * 100
vp[T]    = (buy - sell) / (buy + sell), buy = V*(C-L)/(H-L), sell = V*(H-C)/(H-L)
         == ((C-L) - (H-C)) / (H-L)                   blank where H <= L
vs[T]    = SMA(|vp|, 14)[T]
VWD[T]   = madif[T] * vp[T] * vs[T] * 10
```

Source: Reddit, tier 4 — r/TradingView post 1gofmli (2024-11-11),
https://www.reddit.com/r/TradingView/comments/1gofmli/, as issue #202 quotes
it. The poster reads 3-minute bars and fires when `vwd` leaves its 2-sigma
band with an RSI filter; neither the band nor the filter ships. Nothing here
tests what the poster says the oscillator does: *existence, not evidence*.

**Every number below is printed by `python docs/measure_vwd.py`** (section
names match the headings: `python docs/measure_vwd.py A1 B1 …`).

⚠ **Three exceptions, named here rather than left for a reader to find.**

1. §F's counts are **pytest's**, from the runs named there;
2. the before/after counts in *Wiring* are read off `README.md`'s and
   `docs/MLCompanionContract.md`'s diffs (checked by
   `tests/test_readme_counts.py` and
   `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`);
3. §E0's screen figures are **issue #202's**, quoted.

The asserted bounds in `tests/test_vwd.py` (1e-9, 1e-4) are that file's own
constants, not run output.

## Verdict

Gates A–D are cleared on synthetic frames, and the column is wired through
all five touch points. **Gate E is OWED:** it cannot run in this worktree,
and no row is recorded in `docs/gate_e_ledger.csv`. The launcher runs
`gate_e_overlap.py run --module pandas_ta.momentum.vwd --name vwd` and
records the row. Real-data reachability (Gate C's second limb) is reported by
that run's sample size.

Choices made in the port:

* **Volume is not read.** V multiplies both `buy` and `sell`, so it cancels
  from `vp`. That is the reduction the screen prototype also uses ("vp
  reduces to the close location (V cancels)"). The literal form differs
  only where V == 0 (0/0) or V is NaN (§A4).
* **The EMA is SMA-seeded**: this fork's `ema`, which is also `talib.EMA`
  (§A2). A bare `ewm(span=7)` from bar 0 differs only in the warm-up (§A3).
* **An H == L bar is blank, as the source computes it** (0/0), and it blanks
  the 14 bars of `vs` that contain it (§C2). ⚠ An H < L bar is blanked too,
  although the source is finite there: that is corrupt data, and the port
  refuses to read a close location off an inverted range
  (`tests/test_vwd.py::test_an_inverted_range_is_blank_like_a_zero_range`).

## §A1 Gate A — against a bar-by-bar oracle

The oracle uses its own `math.fsum` SMAs and its own SMA-seeded EMA
recursion over Python floats, and it computes `vp` in the LITERAL form, with
`buy` and `sell` each carrying V. It shares no code with the module.

| frame | fired | masks equal | max abs | max rel | Spearman |
|---|---|---|---|---|---|
| walk | 1,487 / 1,500 | True | 1.785e-13 | 1.912e-11 | 1.0000 |
| trend | 1,487 / 1,500 | True | 1.374e-13 | 2.573e-12 | 1.0000 |
| range-bound | 1,487 / 1,500 | True | 1.368e-13 | 3.704e-11 | 1.0000 |
| grid | 1,487 / 1,500 | True | 2.025e-13 | 5.625e-03 | 1.0000 |
| heavy-tailed | 1,487 / 1,500 | True | 1.441e-13 | 2.230e-11 | 1.0000 |
| jump | 1,487 / 1,500 | True | 1.990e-13 | 7.099e-12 | 1.0000 |

`grid`'s relative figure is large because 19 of its bars read exactly 0.0
(§C1), so relative error is taken against values near zero. Its absolute
gap is the same size as on the other frames. The test asserts the absolute
gap at 1e-9.

## §A2 the EMA leg is TA-Lib's

`ema(close, 7)` against `talib.EMA(close, 7)`: the NaN masks are equal on
all six frames and the gap is at most 1.819e-12 (`trend`); 2.842e-14 ..
5.684e-14 elsewhere. Both first fire at bar 6.

## §A3 a reading NOT taken: bare `ewm(span=7)` from bar 0

| frame | bars differing > 1e-9 | max abs | last differing bar | Spearman |
|---|---|---|---|---|
| walk | 63 / 1,487 | 6.061e-02 | 78 | 0.999998 |
| trend | 58 / 1,487 | 1.808e-02 | 72 | 1.000000 |
| range-bound | 61 / 1,487 | 1.463e-01 | 76 | 0.999999 |
| grid | 64 / 1,487 | 1.334e-01 | 80 | 0.999999 |
| heavy-tailed | 53 / 1,487 | 8.362e-03 | 67 | 1.000000 |
| jump | 61 / 1,487 | 8.623e-02 | 77 | 0.999998 |

The seeding affects only the warm-up and has washed out by bar 80. The
screen's Gate E figures are therefore unlikely to depend on which EMA the
prototype used, but this is not measured here: the prototype is not in this
tree.

## §A4 V == 0 or NaN: the literal form is blank, the module is not

With one zero-volume bar at 700 on `walk` (and, separately, one NaN-volume
bar there), the module fires on 1,487 bars and the literal form on 1,473:
bars 700 .. 713 are blank in the literal form only. The figures are the
same for both cases.

## §B1 Gate B — the blind future sweep

Each high, low and close from bar J onward is perturbed, by ×1.02, ×1.01
and ×1.03 respectively, and the test checks whether anything before J
moves. J takes 36 values (bars 1,464 .. 1,499).

* The module is caught **0 / 36** times on each of the six varying frames.
* Six look-ahead mutants are read off the shipped source, edited, and
  `exec`'d in memory:

| mutant | caught (walk, trend, heavy-tailed) | smallest first-catch move |
|---|---|---|
| close-lead | 36, 36, 36 | 1.521e+02 |
| ema-lead | 36, 36, 36 | 2.698e-02 |
| sma-lead | 36, 36, 36 | 7.490e-03 |
| vp-lead | 36, 36, 36 | 3.638e+00 |
| vs-lead | 36, 36, 36 | 2.640e-02 |
| output-early | 36, 36, 36 | 1.159e+00 |

⚠ **The factors are unequal on purpose.** `vp` is invariant under a common
rescale of one bar's H, L and C. The first draft scaled all three by ×1.03,
and the `vp-lead` and `vs-lead` mutants were then caught only by rounding.

## §B1U the uniform rescale, re-run

A uniform ×1.03 suffix at bar 1,464 moves the prefix of:

| mutant | walk | trend | heavy-tailed |
|---|---|---|---|
| vp-lead | 1.930e-14 | 1.097e-13 | 1.703e-13 |
| vs-lead | 5.551e-16 | 1.599e-14 | 2.359e-16 |

These are rounding, not catches. `tests/test_vwd.py::test_a_uniform_suffix_rescale_cannot_see_a_vp_lead`
pins both mutants on all three frames below 1e-9.

## §B2 the sweep's blind spot, and the oracle covering it

Three edits are wrong without reading any later bar, so the suffix sweep
cannot see them. Gate A's oracle rejects all three:

| edit | sweep | miss vs oracle (walk) |
|---|---|---|
| `vs` lagged a bar | 0 / 36 | 1.155e+00 |
| EMA at 14 instead of 7 | 0 / 36 | 9.068e+00 |
| madif over the SMA instead of the EMA | 0 / 36 | 3.737e-01 |

## §C Gate C — reachability

### C1 the six varying frames (SYNTHETIC)

| frame | fired | first | distinct | exactly 0.0 | min | max |
|---|---|---|---|---|---|---|
| walk | 1,487 / 1,500 | 13 | 1,487 | 0 | -1.0486e+01 | 1.3453e+01 |
| trend | 1,487 / 1,500 | 13 | 1,487 | 0 | -1.6094e+01 | 1.3034e+01 |
| range-bound | 1,487 / 1,500 | 13 | 1,487 | 0 | -1.7651e+01 | 1.5113e+01 |
| grid | 1,487 / 1,500 | 13 | 1,469 | 19 | -1.1111e+01 | 9.8030e+00 |
| heavy-tailed | 1,487 / 1,500 | 13 | 1,487 | 0 | -2.6651e+01 | 3.9251e+01 |
| jump | 1,487 / 1,500 | 13 | 1,487 | 0 | -5.7406e+01 | 4.9034e+01 |

Pooled over 8,922 bars: -5.7406e+01 .. 4.9034e+01. 4,416 bars are negative,
19 are exactly 0.0 (all on `grid`, where a tick-rounded close sits at the
exact mid-range), and 4,837 have |v| <= 1.

### C2 degenerate frames

* `doji`: a `walk` with H == L == C on 15 bars (every 100th bar from bar
  50). It fires on 1,277 / 1,500 bars, with 210 = 15 × 14 bars blank after
  the warm-up. Each such bar blanks itself and the next 13.
* `flat`: a constant close with H > L. It fires on all 1,487 bars, and every
  one reads exactly 0.0 (max |v| 0.000e+00) because `madif` is zero. This is
  why "not a constant column" is asserted on the varying frames only.

### C3 real data — OWED to Gate E

Not measured here; the port's Gate E run reports it. §E0's n = 383,681 is
the PAIRWISE sample against `Dist_to_Nearest_Fib_pct` on the prototype, so
it cannot be read as this column's fire count.

## §D Gate D — scale-freeness

* **D1** ×8 and ×64 are bit-identical on all six varying frames and on
  `doji`, so the H == L blanks scale with the rest.
* **D2** ×10 / ×3.7 / ×0.1 / ×1.0000001 over 24 cells: every NaN mask
  matches; the worst absolute gap is 1.717e-11, and the worst relative gap
  is 1.011e-10 over bars with |v| >= 1e-3. Asserted at 1e-9 absolute.
* **D3** Non-vacuity: a +10 level shift on H, L and C moves
  1,468 .. 1,487 of the 1,487 fired bars (by up to 4.203e+00). `madif` is a
  ratio of levels, so the column is scale-free but NOT shift-invariant, and
  that is what makes the ×8 identity meaningful.
* **D4** 1,487 of 1,500 fire on every varying frame, so `0 < fires < n`
  holds.

## §E Gate E — OWED

### §E0 what the screen measured, on the PROTOTYPE (issue #202, quoted)

Run `screen_r9_20261029`, `gate_e_overlap.py run --module ind_screen_r9 --fn
screen`, Backtesting `main` b2d94243, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 comparators, canary bit-equal. Max |ρ| **0.3064** vs
`Dist_to_Nearest_Fib_pct` (manifest, n = 383,681); top-5 per-frame max
median 0.3156 → **SHIP**. Next comparators: `er_Pctl` 0.2101,
`EFFICIENCY_RATIO` 0.2066. A prototype is not a port: the port's own run
decides its band.

### §E1 the port's run

**OWED.** It is not run here and no ledger row is recorded;
`tests/test_gate_e_ledger.py` reports it as a "Gate E owed" skip under
`GATE_E_PENDING_OK=1`.

## §L in-fork overlap — a DISCLOSURE, not Gate E

Every `Category` column at its defaults was scored against `VWD_7_14` on the
six varying frames (open = previous close). 544 columns scored on all six.
The highest per-frame median |Spearman ρ| values:

| column | median \|ρ\| |
|---|---|
| `g191_146:G191_146_61_2_20_60_2` | 0.5631 |
| `pocket_pivot:PPIVOT_MAOFFSET_10_10` | 0.4536 |
| `er:ER_10` | 0.3146 |
| `dx:DX_14` | 0.2211 |
| `a101_023:A101_023_20_2` | 0.1923 |

All are well under the issue's 0.90 restatement line and CLAUDE.md's 0.76 Gate E ship line. These
are six SYNTHETIC frames, not 89 real ones. The issue's own fork-overlap
stage (12 real frames) put the maximum at 0.2640, against `PPIVOT_MAOFFSET_10_10`.

## §Z cost — this machine, this run

`vwd` takes 1.856 ms per call on 1,500 bars; the pure-Python oracle takes
4.564 ms.

## §F suites

`python -m pytest -q -p no:cacheprovider -W ignore tests/test_vwd.py
tests/test_altport2_ports.py tests/test_gate_e_ledger.py
tests/test_indicator_list_tables.py tests/test_readme_counts.py
tests/test_ml_companions.py tests/test_wiring_accessors.py` → **1633 passed,
8 skipped** in 37.25s. One of the skips is `tests/test_gate_e_ledger.py`'s
"Gate E owed … no Gate E ledger row for ['vwd']". The full suite is run once
by the orchestrator.

## Wiring

| # | file | change |
|---|---|---|
| 1 | `pandas_ta/momentum/vwd.py` | new |
| 2 | `pandas_ta/momentum/__init__.py` | `from .vwd import vwd` |
| 3 | `pandas_ta/__init__.py` | `"vwd"` in `Category["momentum"]` |
| 4 | `pandas_ta/core.py` | `df.ta.vwd()` (high, low, close) |
| 5 | `tests/test_vwd.py` | new |

`README.md`: 395 → 396 in `Category`, 403 → 404 callable, momentum 89 →
90. `tests/test_altport2_ports.py`: `CATEGORY_TOTAL` 395 → 396.
`docs/MLCompanionContract.md`: 740 → 741 tagged, 371 → 372 `SF`.
`docs/IndicatorDictionary.md` was regenerated.
