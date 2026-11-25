# vpci — measured (issue #264)

> **Status: Gates A–E cleared, wired, tests green. Gate E measured 2026-11-22 by the
> owner: SHIP, max |ρ| 0.4672 vs `PVT_Slope_norm`; ledger row `pr348-vpci`.** Gate F: the targeted guard
> run below is green; the full suite and the parent repo are the launcher's run, not this
> session's.

Volume Price Confirmation Indicator, price-normalised: Buff Dormeier, *Technical Analysis of
Stocks & Commodities*, July 2007, per issue #264 (split out of #32 LIBSINGLES). Module
`pandas_ta/volume/vpci.py`, column `VPCI_5_20`. Tests: `tests/test_vpci.py` (24, all passing).
Numbers below come from `python docs/measure_vpci.py` unless another source is named.
Environment: pandas 2.3.3 / numpy 1.26.4. Measured 2026-11-18.

## Gate A: derivation from the issue's formula

Issue #264 states, citing the CMT Association's summary (https://cmtassociation.org/?p=74895)
and jesse's `vpci` (MIT):

    VPCI = (VWMA_20 - SMA_20) / SMA_20 * (VWMA_5 / SMA_5) * (VMA_5 / VMA_20)

**What this session could NOT do:** it read none of these: Dormeier's article, his Dow Award
paper (404 for the issue's author on 2026-11-08), the CMT summary, or jesse's source. The derivation
starts from the issue body, as the issue says it should. The lengths 5/20 and the division of VPC by
`SMA_20` are the owner's choices of 2026-11-08, not checked against the original.

* `VWMA_n = SUM(close*volume, n) / SUM(volume, n)`, trailing, current bar included: the
  issue's own spelling, computed as a ratio of rolling sums.
* `SMA_n` / `VMA_n`: trailing means of close / volume.
* `VPC = (VWMA_20 - SMA_20) / SMA_20`, `VPR = VWMA_5 / SMA_5`, `VM = VMA_5 / VMA_20`,
  `VPCI = VPC * VPR * VM`.

No interpretation choice is left open by the formula.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | 5-bar hand-derived example at `short=2, long=3` (`::test_hand_derived_five_bars`): bars 2..4 = `0.0, -0.014386189258312122, -0.03833333333333337` against the hand-computed `0, -45/3128 = -0.01438618925831202, -23/600 = -0.03833333333333333`. Bar 2 is an exact tie (`VWMA_3 == SMA_3 == 11`). The formula rebuilt from `pandas_ta.overlap.vwma` / `.sma` (VWMA as a ratio of rolling **means**): NaN masks equal, 1,481 overlapping bars, `max\|diff\| = 3.14e-16`, 897 of the 1,481 bars bit-identical. The max relative diff is 1.12e-10, because near zero VPC is a difference of two nearly equal numbers. Plain-numpy per-bar loop at bars 300 / 900 / 1499: `\|diff\|` 1.6e-16 / 0 / 0 |
| B Causality | pass | Future-perturbation: close (tick-rounded) and volume rewritten from bar `j` onward, 35 offsets `range(100, 1500, 40)`. The real module leaks at **0 of 35**. Mutant (`importlib` source read, `exec`'d in memory, final write `.shift(-1)`, a 1-bar look-ahead) leaks at **35 of 35**. The test file repeats this on 900 bars over `range(40, 900, 25)` |
| C Reachability | pass on synthetic data. Real data waits for Gate E | 1,500-bar frame (seed 11, close rounded to 0.01, volume `uniform(1e4, 1e6)` rounded to 100): **1,481 of 1,500** bars non-NaN (98.73%), exactly `n - 19`. First valid bar 19, **1,481 distinct values**, **729 positive / 752 negative / 0 exact zero**, range `[-0.0166045, 0.0136826]`, median `-6.00157e-05`. The 900-bar frame of `::test_fires_and_is_not_constant` fires on 881 = 900 − 19 bars |
| D Scale-free | pass | Close ×k scales `VWMA` and `SMA` together, so `VPC` and `VPR` stay the same and `VM` never reads close. Volume ×k cancels inside each `VWMA` and inside `VM`. Measured: close, volume and both at **×8 / ×64 are bit-identical** (`max\|diff\| = 0`), NaN masks equal. At ×10 / ×3.7 the max `\|diff\|` is 5.71e-16 / 6.13e-16 (close), 3.42e-16 / 3.42e-16 (volume), 5.55e-16 / 6.91e-16 (both), NaN masks equal. `0 < 1,481 < 1,500` fires |
| E Attribution | **SHIP**, measured 2026-11-22 by the owner | max \|ρ\| **0.4672** vs the manifest's `PVT_Slope_norm` over n = 396,825; top-five per-frame max median 0.4517. See Gate E below |
| F Suites | targeted run green | see **Suite run** |

## Zero volume and exact ties

* A 5-bar all-zero volume stretch at bars 700..704 makes **1** bar newly NaN, bar 704. That is
  the only bar whose 5-bar window is entirely zero, so `VWMA_5 = 0/0`. `inf` count: **0**. For
  non-negative volume, `VMA_20 = 0` implies `VWMA_20` is already `0/0`, so no `inf` can arise
  and the module has no `inf -> NaN` guard. A signed volume series (`vol_delta`, `vsumd`) is
  outside the definition.
* Exact ties do not land on exactly 0. With constant volume over a 30-bar slice, `VWMA` and `SMA`
  are equal in exact arithmetic, but the module returns values up to `\|1.38e-16\|` over the 11
  defined bars, because the sums ratio and the plain mean round differently. Rounding noise
  around zero, not signal.

## Non-redundancy (synthetic, not Gate E)

On the 1,500-bar frame, Spearman ρ of `VPCI_5_20` against:

    PVCORR_20                         0.2842  (n = 1,480)
    CMF_20                           -0.0724  (n = 1,481; high/low = close ± 0.5%)
    VPC factor alone (not shipped)    0.9925  (n = 1,481)

Over 12 further frames (seeds 100..111, 1,500 bars each), the per-frame median |ρ| is
**0.3532** vs `PVCORR_20` (max 0.5036) and **0.9910** vs the VPC factor alone (min 0.9896).

The analysis step's wider screen ran 12 synthetic tick-rounded frames against every
`Category["volume"]` indicator plus `pvo`, `vwmacd`, `cmf`, `mfi`, `vfi`, `vzo` and `efi`. Its
best shipped column was `PVCORR_20` at per-frame median |ρ| 0.370. That screen was a throw-away
script outside the repo, so its number is quoted, not reproduced here.

**Gate E risk, disclosed:** nearly all of the column's rank order is its first factor,
`(VWMA_20 - SMA_20) / SMA_20`. The package ships no such column (`vwma` is price-level `PX`).
If the engine's `compute_all` or the `ml_features` manifest has a VWMA-distance column, Gate E
may come out DISCLOSE_GAP or STRUCK. That is the launcher's measurement to make.
(Measured 2026-11-22: it did not. No VWMA-distance column came near; see Gate E below.)

## Gate E — attribution: SHIP

Measured 2026-11-22 by the owner with `scripts/analysis/gate_e_overlap.py run --module
pandas_ta.volume.vpci --name pr348-vpci` on the S&P 500 daily cache, after `dev` was merged
into this branch. Ledger row `pr348-vpci` in `docs/gate_e_ledger.csv`.

| column | max \|ρ\| | against | set | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|---|
| `VPCI_5_20` | 0.4672 | `PVT_Slope_norm` | manifest | 396,825 | 0.4517 | SHIP |

The next four: `efi_norm` 0.4307, `PVT_Slope_norm_Pctl` 0.3771, `efi_norm_Pctl` 0.3630,
`Dist_to_ATR_Lower_pct` 0.3620. All are below the 0.76 DISCLOSE band.

## Wiring

`Category` **357 → 358** (`volume` **42 → 43**). `df.ta.<name>()` accessor count **365 → 366**.
The five touch points are `pandas_ta/volume/vpci.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.vpci` (accessor) and `tests/test_vpci.py` (tests). `README.md`'s headline
counts and its `volume (43)` row are updated. `docs/IndicatorDictionary.md` was regenerated
(609 lines; the new row probes as `VPCI_5_20 SF`, warm-up 19, inputs `C/V`).
`docs/MLCompanionContract.md` tag count goes **702 → 703 / 340 → 341 `SF`**.
`tests/test_altport2_ports.py`: `CATEGORY_TOTAL` **357 → 358**, `CATEGORY_BUCKETS["volume"]`
**42 → 43**.

## Suite run (this repo)

`python -m pytest -q -x -p no:cacheprovider -W ignore tests/test_vpci.py tests/test_altport2_ports.py
tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py tests/test_readme_counts.py
tests/test_ml_companions.py tests/test_wiring_accessors.py`: **1229 passed, 8 skipped**
(25.15 s). The full suite was not run in this session.
