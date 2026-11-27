# Share of window volume on closes above the range midpoint (20) — measured (`b2_vol_above_mid_20`)

Issue #188 (B2-VOL-ABOVE-MID-20), from the 2026-10-26 Reddit-KB scan, batch 2
(round 8). Crowd talk (Reddit, tier 4): rd:algotrading:1whq9hv (2026-09-16),
https://www.reddit.com/r/algotrading/comments/1whq9hv/ — the poster's own
words: "Get the highest high - lowest low divide by half = equals
equilibrium or zeroline, program any candle closing above or below
zeroline, find volume for those." Existence, not evidence: nothing here
tests the poster's claimed use (supply/demand imbalance, support/resistance
at the resulting split).

**Status:** Gates A-E measured, SHIP. Whole-suite run is owed to the
launcher, per the issue-solver's own rules (it must not run the whole
suite).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volume/b2_vol_above_mid_20.py` | volume | `B2_VOL_ABOVE_MID_20` | `[0, 1]`, a ratio of two volume sums; measured 0.055333 .. 0.908908 on a 1,500-bar synthetic frame below, or NaN |

Tests: `tests/test_b2_vol_above_mid_20.py` (34 tests). Numbers: `python
docs/measure_b2_vol_above_mid_20.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

## Decisions

1. **The formula is read directly from the prototype**
   (`docs/issues/screen/ind_screen_r8.py`'s `b2_vol_above_mid_20`), which is
   itself a direct, scale-free translation of the poster's own words: split
   the CURRENT 20-bar window at `(HHV(high,20) + LLV(low,20)) / 2`, then
   report what fraction of that SAME window's own volume traded on bars
   closing strictly above it.
2. **"Closing above" is read as strict `>`,** matching the prototype's own
   `cw > mid[t]` (not `>=`). A bar closing exactly at the midpoint counts
   toward neither side, consistent with the poster's own binary "above or
   below" framing (nothing stated about ties).
3. **`length` is a parameter, not hard-coded**, defaulting to `20` — the
   issue's own stated window, matching this fork's standing convention for
   every other rolling-window port.
4. **Only ONE masking condition: a zero-volume window.** There is a single
   division here (`vol_above / vol_total`), unlike `nm_effort_result_20`'s
   two independent divisions. A zero-RANGE window (every `high == low ==
   close`, i.e. a flat price level) does NOT blank: `mid` then equals that
   same level exactly, so no bar can close strictly above it, and the ratio
   is a well-defined `0.0` as long as volume is nonzero
   (`tests/test_b2_vol_above_mid_20.py::test_a_flat_price_window_computes_a_defined_zero_not_a_blank`).
5. **No `MIN_LENGTH` floor.** At `length=1`, `mid[t]` is just the bar's own
   `(high[t]+low[t])/2`, so the ratio collapses to a plain `{0.0, 1.0}` flag
   (did this bar close in the top half of its own range) — informative
   (measured 218 zeros / 182 ones on a 400-bar slice), not a forced single
   constant the way `nm_effort_result_20`'s `length=1` collapses to `1.0`.
   The length fallback (`length = int(length) if length and int(length) > 0
   else 20`) guards only against a non-positive or sub-1 truncated value,
   e.g. `length=0.5` truncates to `0` and falls back to the default — not a
   degenerate-but-valid window.
6. **Column name carries the one parameter**, `B2_VOL_ABOVE_MID_{length}` —
   e.g. `B2_VOL_ABOVE_MID_20` at the default, `B2_VOL_ABOVE_MID_50` at
   `length=50`.
7. **Vectorised with `numpy.lib.stride_tricks.sliding_window_view`** rather
   than the prototype's own per-bar Python loop: for each window ending bar
   `t`, `mid[t]` (from pandas' trailing `rolling(length, min_periods=length)`
   max/min) is broadcast against that window's own `close`/`volume` slice,
   taken as overlapping array views rather than copies. Cross-checked
   against an independent plain-Python per-bar loop with no shared helper
   (`test_matches_an_independent_scalar_loop`).

## Gate A — correctness

The poster's own words, read with this fork's standing rolling-max/min
convention (trailing, ending at and including the current bar) and the
prototype's own strict `>` and zero-volume mask:

```
mid[t]       = (HHV(high, length)[t] + LLV(low, length)[t]) / 2
window       = bars [t-length+1, t]
vol_above[t] = sum(volume[i] for i in window if close[i] > mid[t])
vol_total[t] = sum(volume[i] for i in window)
B2_VOL_ABOVE_MID[t] = vol_above[t] / vol_total[t]        (vol_total == 0 -> NaN)
```

A hand-derived fixture, chosen on paper before the module ever ran
(`tests/test_b2_vol_above_mid_20.py::test_hand_derived_four_bars`):
`high=[10,12,9,11]`, `low=[8,7,8,9]`, `close=[9,11,8.5,10]`,
`volume=[100,200,150,300]`, `length=4`. `HHV=12`, `LLV=7`, `mid=9.5`;
closes above: bar 1 (`11`) and bar 3 (`10`); volume `200+300=500` of a
`750` total; ratio exactly `2/3`. Module's measured output (`python
docs/measure_b2_vol_above_mid_20.py`): `0.6666666666666666` — float64's own
repeating representation of `2/3`, within the test's `pytest.approx(...,
abs=1e-12)`.

Cross-checked against an independent per-bar Python loop (plain Python
`max()`/`min()`/`sum()`, no `.rolling()` or `sliding_window_view` calls, no
shared helper with the module except the input series themselves) on a
400-bar synthetic frame (`length=50`, 351 defined bars): NaN masks
identical, **max |diff| 0.0** on this machine
(`test_matches_an_independent_scalar_loop`), within the test's pinned
`< 1e-9` band — not tightened to exact bit equality per the issue-solver's
own CPU-variant rule (the oracle sums with plain Python while the module
uses numpy's `sliding_window_view` + `.sum(axis=1)`, and the two reduction
paths could in principle round differently on a CPU with different
dispatched kernels).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** A
  1,500-bar synthetic OHLCV frame, spliced at `J` with 3 independent random
  futures (high, low, close AND volume all replaced from `J` onward): bars
  `< J` come only from the original path in both the base and the spliced
  series, so if the module reads no later bar than `T` its output on
  `[0, J)` cannot move. Measured over **36 swept J values** (`J` = 60, 100,
  ..., 1460, past the 20-bar default warm-up; `python
  docs/measure_b2_vol_above_mid_20.py`): **real module leaked at 0 of 36.**
- **Two independent mutants, each `importlib`-read and `exec`'d in memory,
  each live (differs from the real module) and each caught at every one of
  the same 36 swept offsets:**
  - `write-shift`: the final write (`result = Series(out, index=close.index)`)
    shifted `length` bars into the future (`.shift(-length)` appended), so
    bar `T`'s output actually describes the window ending at `T + length`.
  - `forward-mid`: `mid` built from a FORWARD-looking window
    (`.shift(-length)` appended after the trailing rolling max/min), so bar
    `T`'s "midpoint" reads `high[T+1 .. T+length]` / `low[T+1 .. T+length]`,
    none of which overlaps the trailing window the real module reads.

  Measured leak counts (`python docs/measure_b2_vol_above_mid_20.py`, out of
  the same 36 swept offsets as the real module above): **both mutants, 36 of
  36.**

## Gate C — reachability

Synthetic, from the port session, one 1,500-bar frame at the default
`length=20` (`python docs/measure_b2_vol_above_mid_20.py`):

| frame | fires | warm-up | min | max | distinct values |
|---|---|---|---|---|---|
| synthetic walk (seed 11) | 1,481 of 1,500 | 19 | 0.055333 | 0.908908 | 1,481 |

Every fired bar reads a genuine spread of distinct values (1,481 of 1,481
fired bars distinct), not a narrow or degenerate subset. Bounded in
`[0, 1]` by construction (a ratio of a sub-sum over its own total, min
0.055333 / max 0.908908 on this frame comfortably inside that band). The
warm-up is `length - 1 = 19` bars (not `length`), matching pandas' own
`rolling(length, min_periods=length)` convention: the first full window
ends at index `length - 1`.

Only a zero-volume window blanks its own bar
(`test_a_zero_volume_window_blanks_its_own_bar`: every bar in the window set
to `0.0` volume -> `NaN` at the window's end). A zero-RANGE (flat-price)
window does NOT blank — `mid` then equals the constant level exactly, no
bar can close strictly above it, and the ratio is a defined `0.0`
(`test_a_flat_price_window_computes_a_defined_zero_not_a_blank`), the one
place this port's masking differs from `nm_effort_result_20`'s own
zero-range-blanks-everything pattern.

## Gate D — scale-free, two independent axes

- **Bit-identical under a power-of-two PRICE rescale (x8/x64); bit-identical
  under a power-of-two VOLUME rescale (x8/x64); bit-identical under BOTH
  together (x8/x64).** `mid` scales exactly by a power-of-two price factor
  `k` (max/min pick an existing, exactly `k`-scaled element; the average of
  two exactly-`k`-scaled values rounds identically to `k` times the average
  of the unscaled values), so the strict comparison `close[i]*k > mid[t]*k`
  decides the same side as the unscaled comparison, bit-for-bit, for a
  power-of-two `k`; `vol_above`/`vol_total` never read price at all.
  Symmetrically, a power-of-two volume rescale `j` scales `vol_above` and
  `vol_total` by the identical exact factor, and IEEE754 division of two
  `j`-scaled floats by each other reproduces the unscaled quotient
  bit-for-bit. Measured on the 1,500-bar frame (`python
  docs/measure_b2_vol_above_mid_20.py`): **price x8/x64: 0 exact mismatches
  on 1,481 co-finite cells, max\|diff\| 0.0. Volume x8/x64: 0 mismatches,
  max\|diff\| 0.0. Combined x8/x64: 0 mismatches, max\|diff\| 0.0.**
- A non-power-of-two rescale (`x10`, `x3.7`) is not exact at the scalar
  multiply, so independent last-bit rounding noise can in principle move a
  bar across the strict `>` boundary it sat exactly on before scaling (a
  PRICE-rescale effect) or perturb the volume ratio's last bits (a
  VOLUME-rescale effect). Measured on the same frame: **price x10 and
  x3.7: 0 of 1,481 co-finite cells differ at all** (no comparison happened
  to sit on an exact tie that non-power-of-two rounding could flip on this
  synthetic frame); **volume x10: 1,018 of 1,481 cells differ, max\|diff\|
  3.331e-16; volume x3.7: 1,026 differ, max\|diff\| 4.441e-16; combined x10:
  1,018 differ, max\|diff\| 3.331e-16; combined x3.7: 1,026 differ,
  max\|diff\| 4.441e-16** — every one of these is float64 rounding noise at
  the last bit or two, many orders of magnitude under
  `tests/test_b2_vol_above_mid_20.py`'s pinned `1e-6` tolerance, not a
  disagreement; NaN masks matched exactly in every case. The price-rescale
  "0 cells differ even at non-power-of-two factors" result is NOT claimed as
  a general guarantee (a different random frame could land a close exactly
  on a midpoint and have rounding flip it) — it is what this specific
  measurement found, stated as such.
- `0 < 1,481 fires < 1,500`, 1,481 distinct values: not constant.

## Gate E — attribution

Run by issue-solver (`gate_e_overlap.py run --module pandas_ta.volume.b2_vol_above_mid_20`),
89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all`
+ 358 manifest), canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS.
Recorded in `docs/gate_e_ledger.csv`, measured 2026-11-28.

| column | max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `B2_VOL_ABOVE_MID_20` | 0.3431828168190431 | `skew` | 396,258 | 0.3441936038332621 | SHIP |

0.3432 < 0.76 (SHIP line, `r3-perframe-0.90` band). Not a restatement of any
existing column. Ships as-is.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole
suite):

```
python -m pytest -q tests/test_b2_vol_above_mid_20.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,796 passed, 7 skipped, 0 failed** (re-run by the receipt session after
recording the Gate E ledger row: the prior session's single failure,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
is now closed). `tests/test_b2_vol_above_mid_20.py` alone: **34 passed.**

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in
for a GitHub runner without AVX-512 — the four features issue-solver's
rules name, not this machine's full dispatchable set, which also has
`AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_b2_vol_above_mid_20_cpu.py` — **34 passed** (just
`tests/test_b2_vol_above_mid_20.py`; the ledger/readme/wiring modules above
are not CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 421 → 422 (`tests/test_altport2_ports.py`);
  `CATEGORY_BUCKETS["volume"]` 49 → 50.
- README: 421 → 422 registered, 429 → 430 callable, volume (49) → (50).
- `docs/MLCompanionContract.md`: 766 → 767 tagged and 391 → 392 `SF` (newest
  first in the chain). `B2_VOL_ABOVE_MID_20` tags `SF` because the output is
  already a bounded `[0, 1]` ratio, invariant to a positive price rescale
  (the deciding comparison) and a positive volume rescale (the ratio's own
  cancellation) — measured bit-identical under x8/x64 on both axes.
- `docs/IndicatorDictionary.md`, regenerated with this environment's
  package (`python docs/gen_indicator_dictionary.py docs/IndicatorDictionary.md`):
  adds `b2_vol_above_mid_20` under `## volume (51)`, tagged `SF`, warm-up 19
  (`length - 1`), probed indicator count 423 → 424. Its diff is the
  `b2_vol_above_mid_20` row, the three header counts, the volume section
  count, and the no-transform-needed shortlist, and nothing else (checked:
  `git diff docs/IndicatorDictionary.md`).
- `Category`: `b2_vol_above_mid_20` is placed alphabetically between
  `avwap_z` and `bw_mfi` in `volume`.
- Module sha1 (LF-normalised, for the later `docs/gate_e_ledger.csv` row):
  `a743499340361f511eafcc2e42426ad982ae730f` (measured, `python
  docs/measure_b2_vol_above_mid_20.py`).

## Next step

Shipped through Gates A-E; whole-suite run is the launcher's (Gate F).
