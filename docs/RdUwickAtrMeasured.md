# Upper wick in ATR5 units — measured (`rd_uwick_atr`)

Issue #172 (RD-UWICK-ATR), from the 2026-10-25 ResearchIntel Reddit-KB scan, round 6
(`docs/issues/screen/candidates_r6.csv`). Crowd talk (Reddit, tier 4): the definition comes
from a post or comment, and nothing in this port tests what the poster says it does —
existence, not evidence.

**Source:** Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1rjq7kd (2026-03-03)
https://www.reddit.com/r/Daytrading/comments/1rjq7kd/ — the poster's words: "I divide
parameters like the MAEs for both sides, candle range, body and wick sizes by my chosen
ATR period." Claimed use: size stops/buffers in ATR terms — **not independently tested
here either way.** The MAE part of the poster's words needs forward bars (a label, not a
feature) and is out of scope for this port. A Reddit post is not a script, so there is no
source line number to cite; Gate A below reads the formula directly from the issue's own
restatement ("`(high - max(open, close)) / ATR(5)`"), per its own instruction ("Gate A
starts from the source formula, not the prototype"), not from the screen prototype
(`docs/issues/screen/ind_screen_r6.py`'s `rd_uwick_atr`, which is mathematically the same
reading but is not what Gate A cites). The poster's words name "ATR" without saying which
smoothing — the screen prototype's own disclosed choice (`atr_wilder`, `ewm(alpha=1/5,
adjust=False)`) is the only concrete answer on the record, carried through here via this
fork's own shipped Wilder smoothing (`atr(mamode="wrma")`) rather than re-implemented
inline.

**Status:** shipped through Gates A–F.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/candles/rd_uwick_atr.py` | candles | `RD_UWICK_ATR` | unbounded above (≥ 0 whenever `high >= max(open, close)`, which holds for any OHLC bar that is not itself malformed); NaN during the ATR warm-up |

Tests: `tests/test_rd_uwick_atr.py` (19 tests). Numbers: `python docs/measure_rd_uwick_atr.py`,
run from the repo root. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4.
Measured 2026-11-25.

## Decisions

1. **ATR smoothing is the prototype's disclosed choice, not the poster's.** The poster's
   words say only "ATR period" — no smoothing method. The screen prototype's own
   `atr_wilder` helper (`ewm(alpha=1/5, adjust=False)`, Wilder's recursive mean) is the
   only concrete reading on record for what "my chosen ATR" computes, so this port carries
   that choice through via this fork's own shipped Wilder smoothing
   (`atr(high, low, close, length=5, mamode="wrma")`, backed by
   `pandas_ta.overlap.wilder_rma`) rather than re-implementing the recursion inline, per
   CLAUDE.md's "import a helper from its own module" rule. This fork's `wilder_rma` is
   SMA-seeded (slides to the first full non-NaN window and averages it), while the
   prototype's `ewm(adjust=False)` seeds from its own first value — the two converge but
   are not bit-identical in the first few bars after warm-up; not measured here (no
   prototype import available in this worktree), noted as a known divergence from the
   prototype's own numbers, not from the poster's formula (which names no seeding rule at
   all).
2. **Candle colour is not read.** Unlike `rd_wick_pressure_10`/`rd_horseshoe`, this
   formula's numerator (`high - max(open, close)`) does not branch on bull/bear — it is
   the upper wick on every bar regardless of body colour, per the issue's own formula.
3. **Period = 5, fixed by the formula's own `ATR(5)`,** not a title suffix (the issue's own
   title, "RD-UWICK-ATR", carries no numeric suffix, unlike `rd_wick_pressure_10`'s "(10)"
   title). A `length` argument is still offered with that default, this fork's convention
   for a fixed-period port (`rd_wick_pressure_10`, `osap_retskew_21`). The column name
   carries no suffix (`RD_UWICK_ATR`), matching the candidate screen's own naming for the
   sibling `rd_body_atr`/`rd_lwick_atr` candidates, which also use a fixed internal ATR(5)
   without a numeric column suffix.
4. **A flat run (every bar a doji, `open == high == low == close`, unchanged) reads 0.0,
   not NaN, past warm-up — measured, not merely argued.** `true_range`'s own
   `non_zero_range` util floors an exactly-equal `high`/`low` pair at machine epsilon
   rather than leaving it 0 (this fork's existing defence for crypto data where
   `high == low`), so ATR on a fully flat run is a tiny epsilon, never exactly 0; the
   numerator is also exactly 0, so the ratio is `0 / epsilon = 0.0`. The module's
   `.replace([inf, -inf], nan)` guard exists for the in-principle exact-zero-ATR case this
   epsilon floor otherwise forecloses (same defensive-but-currently-unreachable pattern as
   `rd_wick_pressure_10`'s zero-range guard).

## Gate A — correctness

The issue's own formula, read bar-by-bar:

```
upper_wick    = high - MAX(open, close)
RD_UWICK_ATR  = upper_wick / ATR(5)
```

A 3-bar hand-derived fixture, chosen on paper before the module ran
(`tests/test_rd_uwick_atr.py::test_hand_derived_value`, length=2 to keep the derivation
small): `true_range` forces its own bar-0 to NaN (its own `drift`-bar warm-up, independent
of this port), so the SMA seed needs the first 2 non-NaN true ranges — bar1 (TR=6, from
high=103/low=97/prev_close=101) and bar2 (TR=10, from high=106/low=96/prev_close=99) —
landing the first valid ATR at bar2: `ATR[2] = mean(6, 10) = 8`. Bar2's upper wick is
`106 - max(99, 102) = 4`, giving `4 / 8 = 0.5`; `python docs/measure_rd_uwick_atr.py`
reproduces this exactly.

Cross-checked against an independent per-bar Python loop built straight from the formula
above (true range + Wilder's SMA-seeded recursion, not read from `wilder_rma` or
`true_range`) on a 1,600-bar synthetic OHLC frame with independently-drawn upper/lower
wicks, `length=5`: **1,595 compared bars, NaN masks identical, max|diff| = 2.776e-16**
(`test_matches_an_independent_loop`, `python docs/measure_rd_uwick_atr.py`) — at the scale
of a single machine-epsilon rounding step, consistent with the two computing the same
recursion through different code paths, not a correctness gap.

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Two 1,600-bar
  synthetic frames (seeds 1 and 2) spliced at `J`: bars `< J` come only from seed 1 in both
  the base and the spliced frame, so if the module reads no later bar than `T` its output
  on `[0, J)` cannot move. Measured over **28 swept J values** (`J` = 100, 150, ..., 1450,
  `python docs/measure_rd_uwick_atr.py`): **real module leaked at 0 of 28**.
- **The mutant (the final ratio write with a `.shift(-1)` appended, reading one bar into
  the future) is live** (differs from the real module on the unperturbed frame) **and
  leaked at all 28 of the same 28 swept J values** — a continuous ratio built from a
  per-bar numerator and a recursively-smoothed denominator moves on nearly every bar, so a
  one-bar back-date is caught everywhere it was swept
  (`tests/test_rd_uwick_atr.py::test_lookahead_mutant_is_caught`).

## Gate C — reachability

Synthetic, from this session (no real-data cache in this worktree):

- **1,600-bar frame (seed 4), default length 5:** 1,595 of 1,600 bars fire (5-bar
  warm-up); values range 0.0002 to 0.7506 across **1,595 distinct values** — not constant.
- **10 independent 600-bar frames (seeds 100–109):** every frame fires on 595 of 600 bars
  (fixed 5-bar warm-up), with the range spanning 0.0000 (seeds 103/105/109) to 0.7980
  (seed 104) across seeds.
- **A flat run (every bar a doji, unchanged close) reads 0.0, not NaN, past the 3-bar
  warm-up** (`length=3`; `test_flat_run_reads_zero_not_nan`, Decision 4 above) — the
  epsilon-floored ATR forecloses the in-principle zero-ATR NaN case on this fork's own
  `true_range`.
- **Real data:** Gate E's run, 398,404 non-NaN / 332,166 non-zero of 398,849 pooled bars
  across the 89 ALTPORT-1 frames, 0 degenerate frames — fires on real data.

## Gate D — scale-free

- **Power-of-two (x8, x64): bit-identical, 0 mismatches on 1,595 co-finite cells**
  (`tests/test_rd_uwick_atr.py::test_power_of_two_scale_is_bit_identical`,
  `python docs/measure_rd_uwick_atr.py`). The numerator and every term feeding Wilder's
  ATR are each a difference of like-for-like price terms on the same bars, so an exact
  power-of-two rescale is an exponent shift on every operand — numerator and denominator
  scale by the same `k`, leaving the ratio bit-identical. This holds CONDITIONAL on no
  bar in the series having an exact `high == low` tie: `true_range`'s own
  `non_zero_range` floors such a tie at a FIXED (unscaled) machine epsilon rather than
  `k * epsilon`, which would break bit-identity on that bar (same epsilon floor as
  Decision 4); not observed on the measured synthetic frame, whose continuous-valued
  wicks essentially never tie exactly.
- **Non-power-of-two (x10, x3.7): measured max|diff| 1.865e-14 / 1.371e-14 on 1,595
  co-finite cells** (1,575 / 1,588 of them differ at the last bits, both far under the
  test's 1e-6 tolerance) — reported as a measured tolerance bound, not a mathematical
  guarantee the way the power-of-two case is: each scaled operand carries its own
  last-bit rounding under a non-power-of-two factor, compounded through the recursive ATR
  smoothing (a looser tolerance than `rd_wick_pressure_10`'s non-recursive 1e-9, because a
  recursive mean accumulates rounding bar over bar rather than resetting each window).
- NaN masks match exactly at every factor. `0 < 1,595 fires < 1,600` bars, 1,595 distinct
  values (not a constant column) — the same frame as Gate C.

## Gate E — attribution

Run by issue-solver (`gate_e_overlap.py run --module pandas_ta.candles.rd_uwick_atr`), 89
ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358 manifest),
canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS. Recorded in `docs/gate_e_ledger.csv`
(2026-11-25).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `RD_UWICK_ATR` | 0.5249 | `BODY_PCT` | 397,009 | 0.5304 | SHIP |

Pooled max |ρ| 0.5249 and per-frame max median 0.5304 both land below the 0.76 SHIP line
(`r3-perframe-0.90` bands) — ships as-is, no column removed.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_rd_uwick_atr.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Re-measured in the receipt session after the ledger row was recorded:
**1,597 passed, 7 skipped, 0 failed.** `tests/test_rd_uwick_atr.py` alone: 19 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set, which also has `AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL`
enabled): `python docs/measure_rd_uwick_atr_cpu.py` — **19 passed** (just
`tests/test_rd_uwick_atr.py`; the ledger/readme/wiring modules above are not CPU-sensitive
and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 398 → 399 (`tests/test_altport2_ports.py`); candles bucket (not
  individually tracked in `CATEGORY_BUCKETS`) 8 → 9.
- README: 398 → 399 registered, 406 → 407 callable, candles (8) → (9).
- `docs/MLCompanionContract.md`: 743 → 744 tagged and 373 → 374 `SF` (newest first in the
  chain). `RD_UWICK_ATR` tags `SF` because the numerator and every term feeding the ATR
  are like-for-like price differences — the dictionary generator's own probe frame
  confirms it (`docs/IndicatorDictionary.md`'s `rd_uwick_atr` row), not merely asserted
  here.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `rd_uwick_atr` row (`RD_UWICK_ATR` SF, 5-bar warm-up), the three header counts, the
  candles section count, the SF shortlist, and nothing else (checked:
  `git diff docs/IndicatorDictionary.md`).
- `Category`: `rd_uwick_atr` is placed alphabetically between `rd_outside_bar` and
  `rd_wick_pressure_10` in `candles`.

## Open

None. Gate E SHIP, ledger row recorded. Real-data reachability (Gate C's "owed" line) is
covered by the same Gate E run: 398,404 non-NaN / 332,166 non-zero of 398,849 pooled bars,
0 degenerate.
