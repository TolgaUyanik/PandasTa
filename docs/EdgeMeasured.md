# EDGE bid-ask spread — measured (`edge`)

Issue #183 (NM-EDGE-21), from the owner's Reddit named-only follow-up, round 7, of
2026-10-25. The EDGE estimator of Ardia, Guidotti & Kroencke (2024), "Efficient estimation
of bid-ask spreads from open, high, low, and close prices", *Journal of Financial
Economics* 161, 103916, eq. 15, transcribed from the authors' reference implementation
`eguidotti/bidask` (MIT), `python/bidask/edge.py` at commit `1caba55`.

**Status: Gates A, B and D cleared, and this repo's suite is green (the half of Gate F
that runs here). Gate C has synthetic counts only and
Gate E is owed.** Both need the BIST frames and the private Backtesting repo, which the
contributor's machine does not have. One decision is the owner's: unsigned or signed
(see "Open question").

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volatility/edge.py` | volatility | `EDGE_21` | `[0, +inf)` or NaN; a spread as a fraction of price (0.01 = 1%) |

Tests: `tests/test_edge.py` (25). Environment: Python 3.13.14, pandas 2.3.3, numpy 2.5.4
(`.venv-pd2`); the 25 also pass on pandas 3.0.0 (`.venv`). Measured 2026-11-09.

## Decisions

1. **Unsigned, `sqrt(|s2|)`.** This is the reference's default (`sign=False`). It has a
   cost, measured below: at a zero spread it reads a floor proportional to volatility.
2. **Window = `length` bars.** Each bar reads its own `length` bars, which is
   `length - 1` consecutive pairs, as `edge_rolling(window=length)` does. The first value
   is at bar `length - 1`. Two inputs in the window are not read: the open of its first
   bar and the close of the current bar. The reference uses close only as the prior
   close; this is pinned by `test_current_close_is_not_read`.
3. **Ties are tested on raw prices with a relative tolerance of 1e-9.** The reference
   tests exact equality on logs. The issue's prototype made this change because adjusted
   prices carry ulp noise.
   - On the reference's own data both tests find the same ties: 3815 open=high, 3905
     open=low and 949 high=low in 10,000 rows, identical under both.
   - With every tie moved by one ulp, EDGE stays within 1e-12 of the published value.
     The exact test reads 0.7069× of it (`test_ulp_noise_on_ties_is_ignored`).
4. **A window with a missing, zero or negative price is NaN.** This matches
   `edge_rolling`'s default `min_periods`. The single-sample `edge()` skips missing values
   instead. On the reference's `ohlc-miss.csv`, where values are missing all over the
   file, every 21- and 252-bar window is therefore NaN.
5. **Computed one window at a time, not from rolling sums.** Each value depends on its own
   window only, so a bad tick moves exactly the 21 bars whose window holds it and no bar
   after (`test_a_bad_tick_moves_exactly_its_windows`). The cost is O(n · length): 0.026 s
   at n = 20,000, length 21, and 0.261 s at length 252.
6. **Returns are taken as logs of price ratios** (`log(h/o)`, not `log h − log o`), so a
   ×2^k rescale is bit-identical.
7. **Category `volatility`**, next to `corwin_schultz` and `roll_spread`, the other two
   spread estimators (#10).

## Gate A — correctness

| check | result |
|---|---|
| reference `ohlc.csv`, all 10,000 rows, `length = 10000`, last bar vs published `0.0101849034905478` | relative error 3.6e-15 |
| first 10 rows, `length = 10` vs published signed `-0.016889917516422` (embedded in the test) | relative error 6.9e-15; pinned at 1e-12 |
| independent transcription of `edge()` (log differences, exact ties), every window of `ohlc.csv`, length 3 / 21 / 252 | NaN masks identical; max relative error 8.8e-10 / 1.7e-11 / 3.8e-11 |
| same, `ohlc-miss.csv` | NaN masks identical (6451 / 10000 / 10000 NaN) |
| the test's oracle at 12 bars of a simulated frame, length 3 / 21 / 63 | within 1e-9 relative |

The full-file and every-window rows were measured with a scratch script on the
reference's CSVs, which are not committed because they are 0.6 MB each. The test pins the
10-row published value and the oracle.

## Gate B — causality

- **Future perturbation:** 16 offsets, every bar from `j` on replaced by another path;
  bars before `j` are bit-identical.
- **Mutant:** the write `values[length - 1:]` is moved to `values[length - 2:-1]`, one
  bar earlier. The mutant is live, and it is caught at 16 of 16 offsets.

## Gate C — reachability

- **Synthetic:** 580 of 600 bars fire (20 warm-up), and all 580 values are distinct.
- **Real data: owed.** The counts come with the Gate E run on BIST.
- What kills a window is known from the reference:
  - fewer than two bars that trade at more than one price;
  - no open away from the high or low (`po == 0`);
  - no prior close away from the high or low (`pc == 0`);
  - a bad price.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks.
- ×10 and ×3.7: within 1e-12, measured max 9.4e-15 / 1.2e-15 on the test's frame.
- `0 < fires < n`.

## Semantics — what EDGE_21 reads

The simulation is the paper's design (`tests/test_edge.py::_sim`):
- 390 one-minute steps a day;
- a trade is seen with probability 0.1, at the bid or the ask;
- daily OHLC are taken from the seen trades;
- 1000 days, seed 7.

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

- **A spread of 1% or more is recovered.** Over 10 paths at 1%, the median is 0.009575
  and single paths range from 0.00866 to 0.01026 (pinned).
- **Below about 0.5% at σ = 2%, EDGE_21 reads mostly noise.** At a zero spread about
  half the windows estimate s2 < 0. The unsigned form folds those up into a floor
  proportional to σ: the same seed at twice the σ reads exactly twice the median (pinned).
- **The floor makes it correlate with volatility.** Spearman ρ between EDGE_21 and 21-bar
  realised volatility, over 8 regimes × 250 days with σ drawn from U(0.01, 0.04):
  - 0.4481 at a zero spread;
  - 0.2282 at a 1% spread.

  This fits the prototype's Gate E nearest comparator, `natr` at 0.3889. That figure
  comes from the issue and was not re-measured here.
- **A longer window lowers the floor only slowly:** 0.00457 → 0.00253 from 21 to 252 bars
  at σ = 2%.

## Open question for the owner

**Unsigned (shipped, the reference's default) or signed?**
- Signed drops the floor: its median at a zero spread is −0.00129, against 0.00457
  unsigned.
- Signed also tells a tree when the window carries no spread information.
- The issue measured the prototype at Gate E without stating which form it used.
- Changing the form changes the values but not the name. A signed form could be offered
  as a parameter, `signed=True` as `EDGE_21_S`, if both are wanted.

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
4875 passed, 84 skipped, 0 failed. Without the variable,
`test_every_indicator_that_needs_a_row_has_one` fails on the owed rows `edge` and `mtd_ret`
(the latter already owed on `dev`). The Backtesting suite cannot be run here.

## Counters touched

- `CATEGORY_TOTAL` 300 → 301, `CATEGORY_BUCKETS["volatility"]` 28 → 29.
- README: 301 registered, 309 callable, volatility (29).
- `docs/MLCompanionContract.md`: 645 → 646 tagged and 288 → 289 `SF`, with a revert note.
- `docs/IndicatorDictionary.md` regenerated with `.venv-pd2`. Its diff is the edge row
  (`EDGE_21` SF, 20 warm-up), the four counts and the shortlist entry, and nothing else.

All counts are as of `dev` at `dfe654f`.
