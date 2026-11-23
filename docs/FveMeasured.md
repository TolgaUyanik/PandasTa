# fve — measured (issue #260)

> **Status: Gates A–D cleared, wired, tests green. Gate E pending, run by issue-solver after
> this session** (owed on the way to `dev`; no ledger row yet). Gate F: the targeted guard run
> below is green; the full suite and the parent repo are the launcher's run, not this session's.

Finite Volume Elements: Markos Katsanos, *Technical Analysis of Stocks & Commodities*, April
2003, per issue #260 (split out of #32 LIBSINGLES), with the owner's fixed 0.3% cutoff. Module
`pandas_ta/volume/fve.py`, column `FVE_22`. Tests: `tests/test_fve.py` (24, all passing).
Numbers below come from `python docs/measure_fve.py` unless another source is named.
Environment: pandas 2.3.3 / numpy 1.26.4. Measured 2026-11-23.

## Gate A: derivation from the issue's definition

Issue #260 states, citing Linnsoft's reference (https://www.linnsoft.com/techind/finite-volume-elements)
and finta's `FVE` (LGPL-3.0, its code not used):

    TP_t  = (high_t + low_t + close_t) / 3
    MF_t  = (close_t - (high_t + low_t) / 2) + (TP_t - TP_{t-1})
    VE_t  = volume_t if MF_t > 0.003 * close_t; -volume_t if MF_t < -0.003 * close_t; else 0
    FVE_t = 100 * sum_22(VE) / sum_22(volume); NaN when that volume sum is 0

**What this session could NOT do:** it read none of these: Katsanos's April or September 2003
articles, Linnsoft's page, finta's source. The derivation starts from the issue body, as the issue
says it should. Whether Katsanos's original also caps volume or uses a cumulative sum is unverified
and, per the issue, not part of this port.

Interpretation choices, each read from the issue's text:

* Both band comparisons are **strict**: `|MF|` exactly equal to `0.003 * close` is a 0 ("else 0").
  Pinned by `::test_band_is_strict_on_both_sides`.
* `SMA(volume, 22) * 22` is computed as the rolling **sum** it equals.
* `VE_0` is NaN (no `TP_{-1}`), so the first defined bar is 22, not 21.
* Column name: `FVE_22` as the issue specifies. A non-default `cutoff` is appended
  (`FVE_22_0.005`) so two cutoffs never share a column name.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | 5-bar hand-derived example at `length=3` (`::test_hand_derived_five_bars`): bars 3, 4 = `-11.11111111111111, 16.666666666666668` against the hand-computed `-100/9, 50/3`. Bar 3 has `MF = 0` exactly, inside the band. Independent per-bar loop of the issue's definition over every defined bar 22..1499: `max\|diff\| = 0`, **1,478 of 1,478 bit-identical**. The test file asserts the same loop on every defined bar of its 900-bar frame |
| B Causality | pass | Future-perturbation: high, low, close and volume rewritten from bar `j` onward with another frame's values, 35 offsets `range(100, 1500, 40)`. The real module leaks at **0 of 35**. Mutant (`importlib` source read, `exec`'d in memory, final write `.shift(-1)`, a 1-bar look-ahead) leaks at **35 of 35**. The test file repeats this on 900 bars over `range(40, 900, 25)` |
| C Reachability | pass on synthetic data. Real data waits for Gate E | 1,500-bar frame (seed 11, OHLC rounded to 0.01, about 20% of closes pinned to the high or low — 315 bars where `close == high` or `close == low` — volume `uniform(1e4, 1e6)` rounded to 100): **1,478 of 1,500** bars non-NaN (98.53%), exactly `n - 22`. First valid bar 22, **1,478 distinct values**, **718 positive / 760 negative / 0 exact zero**, range `[-67.75, 63.6352]`, median `-0.777843`. Per-bar `VE`: **+650 / −617 / 232 zero** (inside the band) of 1,499 defined `MF` bars. The 900-bar frame of `::test_fires_and_is_not_constant` fires on 878 = 900 − 22 bars (435 positive / 443 negative) |
| D Scale-free | pass | High, low and close ×k scale `MF` and the band `0.003 * close` alike, so no `VE` sign moves; volume ×k scales numerator and denominator alike. Measured: price, volume and both at **×8 / ×64 / ×10 / ×3.7 all bit-identical** (`max\|diff\| = 0`), NaN masks equal. The ×10 / ×3.7 equality is measured, not guaranteed — an `MF` within float64 rounding of the band could flip — so `tests/test_fve.py` asserts `< 1e-9` there. The 900-bar test frame also measured 0 at ×10 / ×3.7. `0 < 1,478 < 1,500` fires |
| E Attribution | **pending** | owed; run by issue-solver after this session. See the risk below |
| F Suites | targeted run green | see **Suite run** |

## Zero volume

A 22-bar all-zero volume stretch at bars 700..721 makes **1** bar newly NaN, bar 721. That is the
only bar whose 22-bar window is entirely zero, so the volume sum is 0 and is masked to NaN.
`inf` count: **0**.

## Non-redundancy (synthetic, not Gate E)

On the 1,500-bar frame, Spearman ρ of `FVE_22` against:

    G191_040_26                        0.7951  (n = 1,474)
    G191_040_22 (not shipped)          0.8714  (n = 1,478)
    VZO_14                             0.6500  (n = 1,478)
    CMF_20                             0.1890  (n = 1,478)

Over 12 further frames (seeds 100..111, 1,500 bars each), the per-frame median |ρ| is
**0.8155** vs `G191_040_26` (min 0.7616, max 0.8674), **0.9012** vs `g191_040` at `length=22`
(not shipped; min 0.8464, max 0.9270), **0.6762** vs `VZO_14` and **0.1478** vs `CMF_20`.

**Gate E risk, disclosed:** `g191_040` (GTJA #40, up-volume over down-volume) is the same
construction up to the sign rule and the dead zone. Without the band and with `MF` replaced by
`diff(close)`, FVE is `100 * (2 * up / total - 1)`, which rises and falls exactly with the ratio of
up to down volume. If the engine's `compute_all` or the `ml_features` manifest carries
`G191_040_26` or any up/down-volume ratio, Gate E may come out DISCLOSE or DISCLOSE_GAP. That is
the launcher's measurement to make.

## Wiring

After rebasing onto `dev` (which had meanwhile added #149's `ttr_snr_20`):
`Category` **380 → 381** (`volume` **43 → 44**). `df.ta.<name>()` accessor count **388 → 389**.
The five touch points are `pandas_ta/volume/fve.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.fve` (accessor) and `tests/test_fve.py` (tests). `README.md`'s headline
counts and its `volume (44)` row are updated. `docs/IndicatorDictionary.md` was regenerated
(632 lines; the new row probes as `FVE_22 SF`, warm-up 22, inputs `H/L/C/V`).
`docs/MLCompanionContract.md` tag count goes **725 → 726 / 359 → 360 `SF`**.
`tests/test_altport2_ports.py`: `CATEGORY_TOTAL` **380 → 381**, `CATEGORY_BUCKETS["volume"]`
**43 → 44**.

## Suite run (this repo)

`python -m pytest -q -x -p no:cacheprovider -W ignore tests/test_fve.py tests/test_altport2_ports.py
tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py tests/test_readme_counts.py
tests/test_ml_companions.py tests/test_wiring_accessors.py`: **1405 passed, 8 skipped**
(26.92 s, after review round 1). One skip is `test_gate_e_ledger.py`'s "Gate E owed ... no Gate E ledger row for
['fve']", which is expected until Gate E is recorded. The full suite was not run in this session.
