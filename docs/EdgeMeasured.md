# EDGE bid-ask spread — measured (`edge`)

Issue #183 (NM-EDGE-21), from the owner's Reddit named-only follow-up, round 7, of
2026-10-25. The EDGE estimator of Ardia, Guidotti & Kroencke (2024), "Efficient estimation
of bid-ask spreads from open, high, low, and close prices", *Journal of Financial
Economics* 161, 103916 (the issue cites eq. 15). It is transcribed from the authors'
reference implementation, `eguidotti/bidask` (MIT), `python/bidask/edge.py` at commit
`1caba55`.

**Status:**
- Gates A, B and D are cleared, and this repo's suite is green, which is the half of
  Gate F that runs here.
- Gate C has synthetic counts only, and Gate E is owed. Both need the BIST frames and the
  private Backtesting repo, which the contributor's machine does not have.
- One decision is the owner's: unsigned or signed (see "Open question").

Review round 1 (a review of this branch, 2026-11-09) found these, all fixed here:
- a false "nan-means" docstring;
- a circular Gate A row;
- no source line mapping;
- an unbounded memory cost;
- a comparison with `natr` it could not support;
- numbers from an uncommitted script.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volatility/edge.py` | volatility | `EDGE_21` | `[0, +inf)` or NaN; a spread as a fraction of price (0.01 = 1%) |

Tests: `tests/test_edge.py` (27 tests).

Numbers: `python docs/measure_edge.py [REF_DIR]`, run from the repo root. `REF_DIR` holds
the reference's `ohlc.csv` and `ohlc-miss.csv`. They are not committed (0.6 MB each), and
without them the Gate A section of the script is skipped. The script reads them as data;
it compares against the test's own transcription `_oracle` and never runs the
reference's code.

Environment: Python 3.13.14, pandas 2.3.3, numpy 2.5.4 (`.venv-pd2`). The 27 tests also
pass on pandas 3.0.0 (`.venv`). Measured 2026-11-09.

## Decisions

1. **Unsigned, `sqrt(|s2|)`.** This is the reference's default (`sign=False`). Its cost
   is measured below: at a zero spread it reads a floor proportional to volatility.
2. **Window = `length` bars**, as `edge_rolling(window=length)` reads them.
   - Each bar reads its own `length` bars, which is `length - 1` consecutive pairs. The
     first value is at bar `length - 1`.
   - Two inputs in the window are not read: the open of its first bar and the close of
     the current bar. The reference uses close only as the prior close
     (`test_current_close_is_not_read`).
3. **Ties are tested on raw prices with a relative tolerance of 1e-9**, where the
   reference tests exact equality on logs. The issue's prototype made this change
   because adjusted prices carry ulp noise.
   - On the reference's `ohlc.csv` both tests find the same ties: 3815 open=high, 3905
     open=low and 949 high=low.
   - Moved by one ulp, the ties leave EDGE within 1e-12 of the published value. The
     exact test reads 0.7069× of it (`test_ulp_noise_on_ties_is_ignored`).
   - A tie moved by 1e-7 relative is a real difference: EDGE moves by 6.0%. A tolerance
     loosened to 1e-6 fails `test_a_real_price_difference_is_not_a_tie` (checked).
4. **A window with a missing, zero or negative price is NaN.** This follows
   `edge_rolling`'s default `min_periods`. **It deviates from the single-sample `edge()`,
   which skips missing values.**
   - On the reference's `ohlc-miss.csv`, `edge()` over the whole file gives the
     published `0.01013284969780197`.
   - The port reads NaN on 6451 / 10000 / 10000 bars at length 3 / 21 / 252: the missing
     values are spread through the whole file, so almost no window is complete.
   - The port has no form that reproduces the published missing-data value.
5. **Computed one window at a time, not from rolling sums.**
   - Each value depends on its own window only. A bad tick moves exactly the 21 bars
     whose window holds it and no bar after (`test_a_bad_tick_moves_exactly_its_windows`).
   - Windows are evaluated in chunks of `CHUNK_CELLS = 2^18` window cells, so peak memory
     does not grow with n · length. Measured with tracemalloc on: 16 MiB at n = 20,000
     and 31 MiB at n = 200,000, at both length 21 and length 252.
   - Before chunking, the peaks were 238 MiB (n = 200,000, length 21) and 2702 MiB
     (length 252).
   - Chunked output is bit-identical to unchunked at length 3 / 21 / 252 / 4000 (scratch
     check). `test_chunk_boundaries_do_not_change_values` pins it at a 7-window chunk.
   - Time stays O(n · length): 0.055 s / 0.247 s at n = 20,000, length 21 / 252, and
     0.367 s / 1.906 s at n = 200,000.
6. **Returns are taken as logs of price ratios** (`log(h/o)`, not `log h − log o`), so a
   ×2^k rescale is bit-identical.
7. **Category `volatility`**, next to `corwin_schultz` and `roll_spread`, the other two
   spread estimators (#10).

## Gate A — correctness

**Line mapping against the reference `edge.py` @ `1caba55`.** This is against the code,
not the paper: the typeset eq. 15 was not available here. The reference's docstring
names the paper as the source of its implementation.

| reference `edge.py` | this port, `pandas_ta/volatility/edge.py` | change |
|---|---|---|
| L41–45 log prices, `m = (h + l) / 2` | `_pairs` L37–41 | the returns are written as logs of ratios; same values up to rounding |
| L48–49 lag by one period | `_pairs` L34–35 | none |
| L52–56 `r1..r5` | `_pairs` L37–41 (each line commented with the reference expression) | log of a ratio |
| L59–63 `tau`, `po1`, `po2`, `pc1`, `pc2` | `_pairs` L43–48 via `_differs` | `!=` becomes a relative tolerance of 1e-9 (Decision 3) |
| L70–72 `pt`, `po`, `pc` | `_edge_rows` L57–59 | `nanmean` becomes `mean`; a window with a NaN is blanked first (Decision 4) |
| L76–77 missing if `sum(tau) < 2`, `po == 0` or `pc == 0` | `_edge_rows` L62, applied at L84 | none |
| L80–82 `d1`, `d3`, `d5` | `_edge_rows` L65–67 | none |
| L85–86 `x1`, `x2` | `_edge_rows` L70–73 | none |
| L89–94 `e1`, `e2`, `v1`, `v2` | `_edge_rows` L75–78 | none |
| L98–99 `s2`, inverse-variance or equal weights | `_edge_rows` L82–83 | none |
| L102–104 `sqrt(abs(s2))`, sign if asked | `_edge_rows` L84 | unsigned only (Decision 1) |

**Numerical checks:**

| check | result |
|---|---|
| reference `ohlc.csv`, all 10,000 rows, `length = 10000`, last bar vs the published `0.0101849034905478` | relative error 3.55e-15 (`measure_edge.py`) |
| first 10 rows, `length = 10`, vs the published signed `-0.016889917516422` (embedded in the test) | relative error 6.9e-15; pinned at 1e-12 |
| `_oracle` (transcribed reference with log differences and exact ties) at every window of `ohlc.csv`, length 3 / 21 / 252 | max relative error 8.76e-10 / 1.68e-11 / 3.84e-11 over 9546 / 9980 / 9749 bars (`measure_edge.py`) |
| `_oracle` at 12 bars of a simulated frame, length 3 / 21 / 63 | within 1e-9 relative (test) |

`_oracle` is checked against the published 10-row value, so its agreement with the port
is agreement with a verified transcription. Its NaN rule is the port's (Decision 4), so
the NaN masks agree by construction. They are not counted as evidence here.

## Gate B — causality

- **Future perturbation:** 16 offsets, every bar from `j` on replaced by another path.
  Bars before `j` are bit-identical.
- **Mutant:** the chunk write offset `lo = length - 1 + start` is moved to
  `length - 2 + start`, which writes each value one bar earlier. The mutant is live, and
  it is caught at 16 of 16 offsets.

## Gate C — reachability

- **Synthetic:** 580 of 600 bars fire (20 warm-up), and all 580 values are distinct.
- **Real data: owed.** The counts come with the Gate E run on BIST.
- From the reference, these kill a window:
  - fewer than two bars that trade at more than one price;
  - no open away from the high or low (`po == 0`);
  - no prior close away from the high or low (`pc == 0`);
  - a bad price.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks.
- ×10 and ×3.7: within 1e-12; measured max 9.4e-15 / 1.2e-15 on the test's frame
  (scratch check).
- `0 < fires < n`.

## Semantics — what EDGE_21 reads

The simulation is the paper's design as `tests/test_edge.py::_sim` writes it:
- 390 one-minute steps a day;
- a trade is seen with probability 0.1, at the bid or the ask;
- daily OHLC are taken from the seen trades;
- 1000 days, seed 7.

Source: `measure_edge.py`.

| true spread | daily σ | length | EDGE median | share of windows with s2 < 0 | signed median |
|---|---|---|---|---|---|
| 0 | 0.01 | 21 | 0.00229 | 0.532 | −0.00064 |
| 0 | 0.02 | 21 | 0.00457 | 0.532 | −0.00129 |
| 0 | 0.04 | 21 | 0.00914 | 0.532 | −0.00257 |
| 0 | 0.02 | 63 | 0.00360 | 0.496 | +0.00037 |
| 0 | 0.02 | 252 | 0.00253 | 0.479 | +0.00066 |
| 0.002 | 0.02 | 21 | 0.00442 | 0.454 | +0.00191 |
| 0.005 | 0.02 | 21 | 0.00524 | 0.277 | +0.00456 |
| 0.01 | 0.02 | 21 | 0.00906 | 0.066 | +0.00905 |
| 0.01 | 0.02 | 252 | 0.01010 | 0.000 | +0.01010 |
| 0.02 | 0.02 | 21 | 0.01932 | 0.001 | +0.01932 |
| 0.05 | 0.02 | 21 | 0.04969 | 0.000 | +0.04969 |

- **Spreads of 1% and more are recovered within about 10%, reading low at 21 bars.**
  - At 1% the median over 10 paths is 0.009575 (pinned), and single paths read 0.00866
    to 0.01026 (measured, not asserted).
  - At 5% the median is 0.04973 (pinned within 2%).
- **Below about 0.5% at σ = 2%, EDGE_21 reads mostly noise.** At a zero spread about
  half the windows estimate s2 < 0. The unsigned form folds those up into a floor
  proportional to σ: the same seed at twice the σ reads twice the median, to 1e-6
  (pinned).
- **The floor correlates with volatility.** Spearman ρ between EDGE_21 and 21-bar
  realised volatility, over 8 regimes × 250 days with σ drawn from U(0.01, 0.04):
  - 0.4481 at a zero spread;
  - 0.2282 at a 1% spread.

  This is synthetic and cannot be set against the prototype's real-data ρ of 0.3889 vs
  `natr`. Whether the floor lifts the port's real-data ρ is what the owed Gate E run will
  show.
- **A longer window lowers the floor only slowly:** 0.00457 → 0.00253 from 21 to 252 bars
  at σ = 2%.

## Open question for the owner

**Unsigned (shipped, the reference's default) or signed?**
- Signed drops the floor: its median at a zero spread is −0.00129, against 0.00457
  unsigned.
- A negative signed value marks a window whose estimate is dominated by noise. A positive
  one does not prove the opposite: at a true 0.2% spread, 45% of windows still estimate
  s2 < 0.
- The issue measured the prototype at Gate E without stating which form it used.
- Switching the default changes the values but not the name. If both are wanted, the
  signed form could be offered as a parameter (e.g. `signed=True` →
  `EDGE_21_S`).

## Gate E — owed

From `../Backtesting/Backtesting` on the owner's machine:

```sh
python scripts/analysis/gate_e_overlap.py run --module pandas_ta.volatility.edge --name edge
python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD   # from this repo
```

The prototype's numbers in the issue (max |ρ| 0.3889 vs `natr`, SHIP) are not a
measurement of this port.

## Gate F — suites

Full suite on this branch (`.venv-pd2`, CI's two deselects, `GATE_E_PENDING_OK=1`):
4877 passed, 84 skipped, 0 failed.

Without the variable, `test_every_indicator_that_needs_a_row_has_one` fails on the owed
rows `edge` and `mtd_ret`; `mtd_ret` is already owed on `dev`. The Backtesting suite cannot
be run here.

## Counters touched

- `CATEGORY_TOTAL` 300 → 301, `CATEGORY_BUCKETS["volatility"]` 28 → 29.
- README: 301 registered, 309 callable, volatility (29).
- `docs/MLCompanionContract.md`: 645 → 646 tagged and 288 → 289 `SF`, with a revert note.
- `docs/IndicatorDictionary.md`, regenerated with `.venv-pd2`. Its diff is the edge row
  (`EDGE_21` SF, 20 warm-up), the four counts and the shortlist entry, and nothing else.

All counts are as of `dev` at `dfe654f`.
