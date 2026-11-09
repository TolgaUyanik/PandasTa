# g191_152 — measured (issue #66)

> **Status: Gates A-D cleared, this repo's suite green except the pre-existing/owed breaks
> below. Gate E: pending, run by issue-solver after this session.**

MACD of the smoothed lagged 9-day ratio: Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#152`, per issue #66's own
instruction. Module `pandas_ta/momentum/g191_152.py`, column `G191_152_9_9_1_12_26_9_1`. Tests:
`tests/test_g191_152.py` (17, all passing). Numbers below: `python docs/measure_g191_152.py`.
Environment: this worktree's pinned pandas/numpy (pandas 2.3.3 / numpy 2.x, per
`docs/IndicatorDictionary.md`'s header). Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #66 states GTJA191 alpha `#152`:

    SMA(MEAN(DELAY(SMA(DELAY(C/C9,1),9,1),1),12) - MEAN(same,26), 9, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:510-514`):

    @cand("g191_152", "MACD of the smoothed lagged 9-day ratio", G,
          "#152: SMA(MEAN(DELAY(SMA(DELAY(C/C9,1),9,1),1),12) - MEAN(same,26), 9, 1)")
    def _(o, h, l, c, v):
        a = delay(sma(delay(c / delay(c, 9), 1), 9, 1), 1)
        return sma(mean(a, 12) - mean(a, 26), 9, 1)

No disclosed interpretation choice was needed -- the issue's own string and the prototype agree
exactly, including every window length. `C9` is read as GTJA notation for `DELAY(C,9)`, the
same convention every other `g191_*` port in this fork already relies on. Operators, each read
directly off the prototype's own module source: `DELAY(X,n) = X.shift(n)` (`ind_screen.py:45`),
`MEAN(x,d) = x.rolling(d).mean()` (`ind_screen.py:47`), and `SMA(A,n,m)` -- NOT this fork's
plain simple-moving-average `sma` but GTJA's own recursive smoother, called out explicitly in
the prototype's own docstring (`ind_screen.py:55-58`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`, an
EMA with `alpha = m/n`. The same operator and the same `ewm(alpha=m/n, adjust=False,
min_periods=n)` implementation already ships in `g191_146` for the identical GTJA `SMA`.

### The structure: a classic MACD, applied to a smoothed ratio instead of price

Expanding the formula names a fast 12-bar mean minus a slow 26-bar mean, itself smoothed by a
9-bar recursive `SMA` -- the textbook MACD shape (fast-minus-slow spread, then a signal-line
smoother). What is new here is what gets fed into that shape: not price, but `s9_1`, a
once-lagged, GTJA-recursively-smoothed version of the 9-day close ratio `C/C9`. This naming
(`ratio`, `r1`, `s9`, `s9_1`, `fast`, `slow`, `diff`) is used throughout the module and this
document.

### Warm-up: a disclosed necessary condition

`ratio = C/DELAY(C,9)` is undefined for the first 9 bars (no bar 9 back). `r1 = DELAY(ratio,1)`
needs one more bar. `s9`, GTJA's recursion with `min_periods=9`, needs 9 CONSECUTIVE valid `r1`
values. `s9_1 = DELAY(s9,1)` needs one more bar. `fast`/`slow`, trailing means of `s9_1` over 12
/ 26 bars, need `max(12,26)-1` more CONSECUTIVE valid bars. The final `SMA`, `min_periods=9`,
needs 9 more CONSECUTIVE valid `diff` values. Total: `min_length = delay_length + smooth1_length
+ max(fast_length, slow_length) + smooth2_length` = `9+9+26+9` = **53** bars at the shipped
defaults, enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | A hand-derived 14-bar example (`delay_length=3, smooth1_length=2, smooth1_weight=1, fast_length=2, slow_length=3, smooth2_length=2, smooth2_weight=1`) replayed independently with `fractions.Fraction` (no floats, no pandas `.ewm()`/`.rolling()`), matching the module's float64 output to ~1e-13 at bars 9-13 (`python docs/measure_g191_152.py`), plus an independent per-bar loop (plain Python, not the module's own `.ewm()`/`.rolling()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward), 34 offsets past the 52-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final GTJA-`SMA` write index `smooth2_length=9` bars into the future): caught **34 of 34**. Centered-mean mutant (`fast = s9_1.rolling(fast_length, center=True).mean()`, the `bos` look-ahead bug class): caught **34 of 34**. A third construction (`r1 = ratio.shift(-1)`, a genuine one-bar look-ahead) is live-different from the real module but caught **0 of 34** -- the pipeline's own further `DELAY`s push its first visible output effect one bar past the checked window; disclosed in the module docstring and pinned as a negative result (`tests/test_g191_152.py::test_forward_inner_delay_mutant_is_live_but_not_caught_by_this_sweep`), not used as a Gate B pin |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, lognormal walk, `docs/measure_g191_152.py:_walk`), shipped default: **1,448 of 1,500** bars non-NaN (96.53%), first valid at bar 52 (exactly the structural warm-up boundary, `min_length - 1`). **1,448 distinct values**. Range `[-0.029103, 0.025660]`, median `-0.000714` |
| D Scale-free | pass | `ratio = C/DELAY(C,9)` is linear-cancelling under a positive price rescale (`k*C / (k*DELAY(C,9)) = C/DELAY(C,9)`), so every downstream term built only from `ratio` is untouched for any `k > 0`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 2.02e-16 / 1.82e-16). `0 < 1448 fires < 1500` and `1448 > 1` distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | -- |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **300 -> 301** (`momentum` **75 -> 76**); `df.ta.<name>()` accessor count **308 ->
309**. Touch points: `pandas_ta/momentum/g191_152.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["momentum"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_152` (accessor),
`tests/test_g191_152.py` (tests). `README.md`'s headline and `momentum (76)` row, and
`docs/IndicatorDictionary.md` (regenerated, `302 -> 303` probed), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated **645 ->
646 / 288 -> 289 `SF`** (`G191_152_9_9_1_12_26_9_1` probes cleanly at the dictionary's 600-bar
synthetic frame and takes many distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (300 -> 301); no
`CATEGORY_BUCKETS` entry needed (that dict only tracks `trend`/`volatility`/`volume`, not
`momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` now owes a row for
`['g191_152', 'mtd_ret']` (expected -- this is the "Gate E owed, not failed" skip described in
CLAUDE.md, surfaced as a hard failure in this local run because `GATE_E_PENDING_OK` is not set
outside CI). `mtd_ret` pre-dates this session (carried over from issue #206, per
`docs/G191146Measured.md`'s identical note); `g191_152` is this port's own pending row, closed by
the receipt session after the launcher's Gate E run.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4867 passed, 83
skipped**. `g191_152`'s own tests (`tests/test_g191_152.py`): **17 passed**. The 3 failures, all
pre-existing and unrelated to this port (CLAUDE.md "Known breaks" plus the owed Gate E ledger
row): `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed list
above), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs
the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
