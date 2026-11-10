# g191_111 — measured (issue #71)

> **Status: Gates A-D cleared. Gate E: pending, run by issue-solver after this session.**

Volume x close-location oscillator: Guotai Junan's (2017, "GTJA191", internal quant report, read
via the HKUDS/Vibe-Trading copy, MIT) alpha `#111`, per issue #71's own instruction. Module
`pandas_ta/volume/g191_111.py`, column `G191_111_11_2_4_2_20`. Tests:
`tests/test_g191_111.py` (20, all passing). Numbers below: `python docs/measure_g191_111.py`.
Environment: this worktree's pinned pandas/numpy, per `docs/IndicatorDictionary.md`'s header.
Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #71 states GTJA191 alpha `#111`:

    SMA(V*CLV,11,2) - SMA(V*CLV,4,2)

scale-free conversion stated on the same line: `/mean(V,20)`.

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:466-470`,
`clv` itself at `ind_screen.py:110`):

    @cand("g191_111", "volume x close-location oscillator", G,
          "#111: SMA(V*CLV,11,2) - SMA(V*CLV,4,2)", "/mean(V,20)")
    def _(o, h, l, c, v):
        x = v * clv(h, l, c)
        return sdiv(sma(x, 11, 2) - sma(x, 4, 2), mean(v, 20))

    def clv(h, l, c): return sdiv((c - l) - (h - c), h - l)

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including both window lengths/weights and the `/mean(V,20)` scale-free
conversion the issue's own candidate line states. Operators, each read directly off the
prototype's own module source: `CLV = ((C-L)-(H-C))/(H-L)` (the standard Accumulation/
Distribution close-location term, `[-1, 1]` whenever `H > L`), `MEAN(X,n) = X.rolling(n).mean()`
(`ind_screen.py:48`), and `SMA(A,n,m)` -- NOT this fork's plain simple-moving-average `sma` but
GTJA's own recursive smoother, called out explicitly in the prototype's own docstring
(`ind_screen.py:57-58`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`, an EMA with `alpha = m/n`. The same
operator and the same `ewm(alpha=m/n, adjust=False, min_periods=n)` implementation already
ships in `g191_152`, `g191_146` and `g191_160` for the identical GTJA `SMA`, applied here TWICE
to the same series `x = V*CLV` at two different `(n, m)` pairs (`11,2` and `4,2`).

### The structure: two speeds of the same volume-weighted close-location series

`x = V*CLV` is a single per-bar series (volume signed by how close the bar closed to its own
high vs. its own low); the formula smooths it at two different GTJA `SMA` speeds and takes the
difference -- a MACD-style spread of the same underlying series, not two different series. The
issue's own candidate line divides the whole spread by the trailing 20-bar mean volume for a
scale-free result. This naming (`clv`, `x`, `sma1`, `sma2`, `mean_v`) is used throughout the
module and this document.

### Warm-up: a disclosed necessary condition

`sma1 = SMA(x,11,2)` needs 11 valid `x` observations (`min_periods=11`); `sma2 = SMA(x,4,2)`
needs 4 (`min_periods=4`); `mean_v = MEAN(V,20)` needs 20 CONSECUTIVE bars of `V`
(`min_periods=20`, a plain `.rolling()`, which cannot be satisfied by scattered valid
observations the way `.ewm()` can). At the shipped defaults `mean_v`'s `mean_length=20` is the
binding constraint, so `G191_111` is defined from `t >= 19` UNLESS more than
`mean_length - 1 - smooth1_length = 8` of bars `0..18` are `H==L` ties (the only way `sma1`'s
11-observation count fails to clear by bar 18) -- measured: a single tie injected at bar 5 of a
1500-bar synthetic walk (no other ties) leaves the first valid index at 19, UNCHANGED from the
no-tie case. `min_length = max(smooth1_length, smooth2_length, mean_length)` = `max(11,4,20)` =
**20** bars at the shipped defaults, enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | An 8-bar hand-derived example (`smooth1_length=3, smooth1_weight=1, smooth2_length=2, smooth2_weight=1, mean_length=3`, no `H==L` ties) checked against an independent computation of `CLV`/`x`/both GTJA `SMA`s/`MEAN` (`python docs/measure_g191_111.py`), matching the module's float64 output exactly at bars 2-7, plus an independent per-bar loop (plain numpy, not the module's own `.rolling()`/`.ewm()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 (differences ~2e-14 to 1e-13, within float round-off) |
| B Causality | pass | Future-perturbation sweep (every OHLCV bar rewritten from `j` onward), 37 offsets past the 19-bar warm-up: real module **0 of 37** leaks. Write-shift mutant (final division's write index `mean_length=20` bars into the future): caught **37 of 37**. Centered-`mean_v` mutant (`mean_v = volume.rolling(mean_length, center=True).mean()`, the `bos` look-ahead bug class): caught **37 of 37** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLCV series (seed 11, lognormal price walk with independently-seeded high/low spread and uniform volume, `docs/measure_g191_111.py:_walk`), shipped default: **1,481 of 1,500** bars non-NaN (98.73%), first valid at bar 19 (exactly the structural warm-up boundary, `min_length - 1`). **1,481 distinct values**. Range `[-0.358276, 0.285084]`, median `0.000167` |
| D Scale-free | pass | `CLV` is exactly invariant under a positive PRICE rescale (its numerator and denominator are both linear in price, the factor cancels algebraically), so `x = V*CLV` and every downstream term is price-rescale invariant; `x`, both GTJA `SMA`s and `MEAN(V,...)` are each linear in a positive VOLUME rescale, so the final ratio's volume factor cancels exactly. Measured on the 1,500-bar series: PRICE-only, VOLUME-only, and BOTH x8/x64 **all bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 2.9e-14 PRICE, 1.4e-16 VOLUME, 2.9e-14 BOTH). `0 < 1481 fires < 1500` and `1481 > 1` distinct values rule out a constant column |
| E Attribution | pending | Gate E: pending, run by issue-solver after this session |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **305 -> 306** (`volume` **39 -> 40**); `df.ta.<name>()` accessor count **313 ->
314**. Touch points: `pandas_ta/volume/g191_111.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` -> `Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_111` (accessor), `tests/test_g191_111.py` (tests). README.md's headline
(`305 -> 306` / `313 -> 314`) and `volume (39 -> 40)` row, and `docs/IndicatorDictionary.md`
(regenerated, probe `307 -> 308`), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **650 -> 651 / 293 -> 294 `SF`**
(`G191_111_11_2_4_2_20` probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`305 -> 306`) and
`CATEGORY_BUCKETS["volume"]` updated (`39 -> 40`).

`g191_111`'s Gate E row will be recorded in `docs/gate_e_ledger.csv` by a later receipt session,
once the launcher's Gate E run lands.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4997 passed, 83
skipped**. `g191_111`'s own tests (`tests/test_g191_111.py`): **20 passed**. The 3 failures,
all pre-existing and unrelated to this port (CLAUDE.md "Known breaks" plus the owed Gate E
ledger row, see above): `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed list above, now including `g191_111`), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
