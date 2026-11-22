# B3-INRANGE-COUNT-20 — `inrange_count` measured (PandasTa issue #203)

**Port:** `pandas_ta/volatility/inrange_count.py` → one column, `INRC_20` (`INRC_{length}`).
**Source:** Reddit, r/TradingView post 1k894ya (2025-04-26),
https://www.reddit.com/r/TradingView/comments/1k894ya/ — crowd talk, tier 4. The poster's
Pine: *"if high < recent_high[1] and low > recent_low[1] in_range_count :=
math.min(in_range_count + 1, range_lookback)"*, else `math.max(in_range_count - 2, 0)`,
with `recent_high` / `recent_low` the highest high / lowest low over `range_lookback`.
The claimed use, *"counts how long price has stayed inside the established range"*, is
untested. The post does not show `range_lookback`'s value; 20 and the `/ length` scale-free
form are the screen prototype's (issue #203).
**Measured:** 2026-11-20, on this tree, by `python docs/measure_inrange_count.py`
(pandas 2.3.3, numpy 1.26.4). Every figure below is printed by that script.

    cnt[T]  = min(cnt[T-1] + 1, 20)  if high[T] < max(high[T-20 .. T-1])
                                     and low[T]  > min(low[T-20 .. T-1])
              max(cnt[T-1] - 2, 0)   otherwise
    INRC_20 = cnt / 20               in [0, 1], 21 possible values

---

## ⚠ What this port does NOT establish

- **Gate E: SHIP** (measured 2026-11-22 by the owner, after this branch was merged with `dev`;
  row `pr356-inrange_count` in `docs/gate_e_ledger.csv`). `gate_e_overlap.py run --module
  pandas_ta.volatility.inrange_count` over the 89 BIST frames, 687 comparators, canary bit-equal:
  `INRC_20` max |ρ| **0.4794** vs `CHOP` (compute_all, n = 396,311), per-frame max median
  0.4897; against the manifest the top is 0.4128 vs `BB_BWidth_Pctl`. Far under the 0.76 ship
  line, and equal to the issue's prototype figures (0.4794 vs `CHOP`, per-frame 0.4897), so on
  real data the prototype and this module agree at the reported precision.
- **No tie to the prototype.** `docs/issues/screen/ind_screen_r9.py` is gitignored and is not on
  this machine, so Gate A has one limb (the poster's formula by loops), not two. Whether the
  prototype's warm-up, NaN handling and tie rule match this module is not known.
- **Gate C on real data** rests on the Gate E run above (n = 396,311 bars scored). Every other count below is synthetic.
- **The poster's NaN behaviour is not reproduced.** In Pine `high < na` is false, so a bar with a
  missing envelope would cost 2. This port emits NaN on the first `length` bars and on a bar
  whose own high or low is bad, and holds the count there (§G). The fork's choice, stated.

---

## A1 Gate A — the poster's formula by explicit loops

`_oracle` re-scans bars `T-20 .. T-1` on every bar: no rolling window, no shift, no code
shared with the module.

| frame | fired | masks | differ | bit-equal |
|---|---:|---|---:|---|
| walk | 1480 | True | 0 | True |
| trend | 1480 | True | 0 | True |
| range-bound | 1480 | True | 0 | True |
| grid | 1480 | True | 0 | True |
| heavy-tailed | 1480 | True | 0 | True |
| jump | 1480 | True | 0 | True |
| flat | 1480 | True | 0 | True |
| coarse | 1480 | True | 0 | True |
| **pooled** | **11,840** | | | |

Also bit-equal at lengths 5, 10 and 50 on `walk` and `coarse` (6 of 6). A hand frame
(length 3, `tests/test_inrange_count.py::test_gate_a_hand_frame_steps_plus_one_and_minus_two`)
pins the +1 / cap / −2 / clip-at-0 steps bar by bar.

## A4 The reading not taken: non-strict `<=` / `>=`

The poster's comparisons are strict, so a bar that **ties** the prior range's extreme is
outside and costs 2.

| frame | ties | bars differ | Spearman vs strict |
|---|---:|---:|---:|
| walk | 0 | 0 | 1.0000 |
| trend | 0 | 0 | 1.0000 |
| range-bound | 0 | 0 | 1.0000 |
| grid (0.01 tick) | 4 | 57 | 0.9984 |
| heavy-tailed | 0 | 0 | 1.0000 |
| jump | 0 | 0 | 1.0000 |
| coarse (2.0 tick) | 1075 | 1478 | 0.0944 |

⚠ On continuous floats the rule is invisible; on a coarse tick grid it is the whole column
(`coarse` reads exactly 0.0 on 1,055 of 1,480 bars, §C). That is the FVGDEAD regime of
`CLAUDE.md` (21.17% of real BIST daily bars close exactly at an extreme), so what Gate E's real
frames will show cannot be predicted from these synthetic frames.

## B Gate B — causality

Detector: one shared past and three futures for bars ≥ j — the frame itself, and every bar ≥ j
scaled up by a per-bar factor in [1.5, 4] or down by its reciprocal. A bar < j that moves
between them reads the future. (An up/down pair without the untouched tail caught
`output-early` on 0 of 36 offsets of `walk`, because it sends bar j outside the range under both.)

36 tail offsets (1464..1499):

| frame | module | high-envelope-lead | low-envelope-lead | high-lead | output-early |
|---|---:|---:|---:|---:|---:|
| walk | 0 | 3 | 3 | 33 | 31 |
| trend | 0 | 16 | **0** | 36 | 20 |
| range-bound | 0 | 7 | 1 | 35 | 27 |
| grid | 0 | 6 | 13 | 23 | 17 |
| heavy-tailed | 0 | 2 | 4 | 32 | 31 |
| jump | 0 | 8 | 4 | 32 | 24 |
| flat | 0 | 0 | 0 | 0 | 0 |
| coarse | 0 | 9 | 10 | 28 | 21 |

Module, every bar but bar 0 as a split point: **0 of 1,499 on each of the eight frames.**

Each mutant is live against the module on unperturbed `walk`: it moves 563
(`high-envelope-lead`), 780 (`low-envelope-lead`), 669 (`high-lead`) and 1,132 (`output-early`)
of 1,479 shared bars.

⚠ The two envelope mutants read the window **including** bar T and bar T+1, so they look ahead
only when bar T is itself the extreme of that window. The detector sees that on 1 .. 16 of 36
offsets, and `low-envelope-lead` is never seen on `trend` (0 of 36): in an uptrend a bar's low
is rarely its window's minimum. `flat` never moves at all. The test asserts each mutant caught
on each of the six other frames, plus live on `walk`.

## C Gate C — reachability (synthetic)

| frame | bars | fired | first | distinct | == 0 | == 1 | mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| walk | 1500 | 1480 | 20 | 21 | 34 | 388 | 0.7108 |
| trend | 1500 | 1480 | 20 | 21 | 336 | 25 | 0.2718 |
| range-bound | 1500 | 1480 | 20 | 21 | 2 | 818 | 0.9159 |
| grid | 1500 | 1480 | 20 | 21 | 36 | 319 | 0.6709 |
| heavy-tailed | 1500 | 1480 | 20 | 21 | 7 | 456 | 0.7599 |
| jump | 1500 | 1480 | 20 | 21 | 2 | 454 | 0.7995 |
| flat | 1500 | 1480 | 20 | 1 | 1480 | 0 | 0.0000 |
| coarse | 1500 | 1480 | 20 | 15 | 1055 | 0 | 0.0579 |

The warm-up is exactly `length` bars. `0 < non-zero < fired` on the seven moving frames; `flat`
is constant 0.0 because every bar ties its own prior range. On `walk` the counter took 760 +1
steps, 368 −2 steps, 4 −1 steps (a count of 1 clipped to 0) and held on 347 bars (at 0 or at
the cap).

## D Gate D — scale

| frame | ×8 | ×64 | ×10 | ×3.7 | ×0.1 |
|---|---|---|---|---|---|
| all eight | bit-equal | bit-equal | bit-equal | bit-equal | bit-equal |

Only comparisons touch the prices, so even the inexact factors came out bit-identical on these
frames; the test still asserts only the tolerance (masks equal, ≤ 1e-9) for them, because an
inexact rescale could in principle merge two neighbouring prices into one double. ×8 and ×64
are also bit-identical at price levels 1e-6, 1e+6 and 1e+100 (1,480 fired each).

## F Non-redundancy against fork columns — SYNTHETIC, a disclosure, not Gate E

Spearman over the seven moving frames:

| comparator | median \|ρ\| | max \|ρ\| |
|---|---:|---:|
| `adx:ADX_14` | 0.5563 | 0.7522 (walk) |
| `vhf:VHF_28` | 0.5225 | 0.6453 |
| `chop:CHOP_14_1_100` | 0.4797 | 0.6252 |
| `squeeze:SQZ_ON` | 0.0784 | 0.1239 |
| `range_compress_run:RCR_100` | 0.0133 | 0.0573 |

The issue's own fork stage (12 real frames) put the nearest at `vhf:VHF_28` 0.5254.

## G Guards

One bad high or low at bar 700 of `walk`:

| leg | value | own bar NaN | earlier bars moved | later bars moved | unguarded: later moved |
|---|---|---|---:|---:|---:|
| high | nan | True | 0 | 28 | 28 |
| high | +inf | True | 0 | 28 | 30 |
| high | −inf | True | 0 | 28 | 0 |
| low | nan | True | 0 | 28 | 28 |
| low | +inf | True | 0 | 28 | 0 |
| low | −inf | True | 0 | 28 | 30 |

The bad bar is dropped from later envelopes (`min_periods=1` after the head), so its reach is
the count's memory, not a 20-bar NaN block. The infinity guard makes an infinity behave as a
NaN; unguarded, a `+inf` high or `-inf` low sits in the envelope for 20 bars.

## L Short and degenerate frames

20 bars → `None`; 21 → 1 fired; 25 → 5 fired. All-NaN → 0 fired; all 0.0, all −5.0 and
all 100.0 → 40 of 60 fired, every value 0.0, no float error under `errstate(all="raise")`.

## M Wiring counts, read back

`Category` 362, volatility 38, `df.ta` accessors 370. Dictionary: 707 tagged columns
(`SF` 343). Row: `` `inrange_count` | H/L | `length=None` | `INRC_20` SF | 20 ``.

## W Dictionary cut

The docstring's first paragraph is 136 characters; `desc()` returns it whole.

## Z Cost (this machine, this run)

A Python loop over bars: 128 .. 130 ms at 100,000 bars (peak 4.8 MB), 520 .. 524 ms at
400,000 bars (peak 19.2 MB).
