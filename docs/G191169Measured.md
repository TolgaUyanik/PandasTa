# g191_169 — measured (issue #72)

> **Status: Gates A-D cleared, this repo's suite green except the pre-existing breaks
> below. Gate E: pending, run by issue-solver after this session.**

MACD of the smoothed lagged one-day change: Guotai Junan's (2017, "GTJA191", internal
quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#169`, per issue #72's own
instruction. Module `pandas_ta/momentum/g191_169.py`, column `G191_169_9_1_12_26_10_1`.
Tests: `tests/test_g191_169.py` (16, all passing). Numbers below: `python
docs/measure_g191_169.py`. Environment: this worktree's pinned pandas/numpy (pandas 2.3.3 /
numpy 2.x, per `docs/IndicatorDictionary.md`'s header). Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #72 states GTJA191 alpha `#169`:

    SMA(MEAN(DELAY(SMA(C-C1,9,1),1),12) - MEAN(same,26), 10, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are
both unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading
(MIT) -- was never read. Everything below is derived from the issue's own stated formula
string, per the issue's own rule ("Gate A starts from the source formula, not the
prototype"), then cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:537-541`):

    @cand("g191_169", "MACD of the smoothed lagged one-day change", G,
          "#169: SMA(MEAN(DELAY(SMA(C-C1,9,1),1),12) - MEAN(same,26), 10, 1)", "/close")
    def _(o, h, l, c, v):
        a = delay(sma(delta(c, 1), 9, 1), 1)
        return sma(mean(a, 12) - mean(a, 26), 10, 1) / c

No disclosed interpretation choice was needed -- the issue's own string and the prototype
agree exactly, including every window length and the issue's own `/close` scale-free
conversion. Operators, each read directly off the prototype's own module source:
`DELAY(X,n) = X.shift(n)` (`ind_screen.py:45`), `C-C1 = delta(c,1) = c.diff(1)`, `MEAN(x,d)
= x.rolling(d).mean()` (`ind_screen.py:47`), and `SMA(A,n,m)` -- NOT this fork's plain
simple-moving-average `sma` but GTJA's own recursive smoother, called out explicitly in
the prototype's own docstring (`ind_screen.py:55-58`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`,
an EMA with `alpha = m/n`. The same operator and the same `ewm(alpha=m/n, adjust=False,
min_periods=n)` implementation already ships in `g191_146`/`g191_152` for the identical
GTJA `SMA` operator.

### The structure: a classic MACD, applied to a smoothed price change instead of price

Expanding the formula names a fast 12-bar mean minus a slow 26-bar mean, itself smoothed
by a 10-bar recursive `SMA` -- the textbook MACD shape (fast-minus-slow spread, then a
signal-line smoother). What is new here is what gets fed into that shape: not price, but
`a`, a once-lagged, GTJA-recursively-smoothed version of the one-day price change `C-C1`.
Unlike `g191_152` (whose inner quantity, `C/C9`, is already dimensionless, so no final
division is needed), `C-C1` is a price-unit term, so the issue's own prototype divides the
final `SMA` by `C` -- the same `/close` conversion `g191_167`/`g191_151` already ship for
their own price-unit GTJA191 alphas. This naming (`delta_c`, `s9`, `a`, `fast`, `slow`,
`diff`) is used throughout the module and this document.

### Warm-up: a disclosed necessary condition

`delta_c = C - DELAY(C,1)` is undefined for bar 0 (no prior bar), valid from `t>=1`. `s9`,
GTJA's recursion with `min_periods=9`, needs 9 CONSECUTIVE valid `delta_c` values, so it is
defined from `t>=9`. `a = DELAY(s9,1)` needs one more bar, from `t>=10`. `fast`/`slow`,
trailing means of `a` over 12 / 26 bars, need `fast_length-1` / `slow_length-1` more
CONSECUTIVE valid bars, so from `t>=21` / `t>=35`; `diff` needs both, so `t>=35`. The final
`SMA`, `min_periods=10`, needs 10 more CONSECUTIVE valid `diff` values, so from `t>=44`.
Total: `min_length = smooth1_length + max(fast_length,slow_length) + smooth2_length` =
`9+26+10` = **45** bars at the shipped defaults, enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line | A hand-derived 10-bar example (`smooth1_length=2, smooth1_weight=1, fast_length=2, slow_length=3, smooth2_length=2, smooth2_weight=1`) replayed independently with `fractions.Fraction` (no floats, no pandas `.ewm()`/`.rolling()`), matching the module's float64 output to ~1e-13 at bars 6-9 (`python docs/measure_g191_169.py`), plus an independent per-bar loop (plain Python, not the module's own `.ewm()`/`.rolling()` calls) spot-checked at the shipped defaults on a 900-bar frame at bars 300/600/899 |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward), 34 offsets past the 44-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final GTJA-`SMA`/division write index `smooth2_length=10` bars into the future): caught **34 of 34**. Centered-mean mutant (`fast = a.rolling(fast_length, center=True).mean()`, the `bos` look-ahead bug class): caught **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, lognormal walk, `docs/measure_g191_169.py:_walk`), shipped default: **1,456 of 1,500** bars non-NaN (97.07%), first valid at bar 44 (exactly the structural warm-up boundary, `min_length - 1`). **1,456 distinct values**. Range `[-0.003517, 0.002713]`, median `-0.000076` |
| D Scale-free | pass | `delta_c = C - DELAY(C,1)` is linear in `C` (subtraction of two linearly-scaled terms), and every downstream term built only from it (`s9`, `a`, `fast`, `slow`, `diff`, the final `SMA`) is linear too, so the whole pre-division column scales by the same `k` as `C` under a positive price rescale, cancelling exactly against the final division by `C`. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 4.77e-18 / 3.04e-18). `0 < 1456 fires < 1500` and `1456 > 1` distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | — |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **306 -> 307** (`momentum` **77 -> 78**); `df.ta.<name>()` accessor count **314
-> 315**. Touch points: `pandas_ta/momentum/g191_169.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["momentum"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_169` (accessor),
`tests/test_g191_169.py` (tests). `README.md`'s headline (`306 -> 307` / `314 -> 315`) and
`momentum (77 -> 78)` row, and `docs/IndicatorDictionary.md` (regenerated, `308 -> 309`
probed), both updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **651 -> 652 / 294 -> 295 `SF`**
(`G191_169_9_1_12_26_10_1` probes cleanly at the dictionary's 600-bar synthetic frame and
takes many distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (`306 -> 307`); the
`momentum` bucket is not tracked in `CATEGORY_BUCKETS` (only `trend`/`volatility`/`volume`
are), so no change needed there.

`g191_169`'s Gate E row is NOT YET recorded: this session does not run `gate_e_overlap.py`
(CLAUDE.md override for this worktree). `tests/test_gate_e_ledger.py::
test_every_indicator_that_needs_a_row_has_one` therefore fails locally on exactly
`['g191_169', 'mtd_ret']` -- the second name pre-dates this session (carried over from
issue #206, per `docs/G191167Measured.md`'s identical note, unrelated to this port). This
is expected per this session's own rules: a later receipt session fills in the measured
Gate E numbers and records the ledger row once the launcher has run Gate E.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 5021 passed, 83
skipped**. `g191_169`'s own tests (`tests/test_g191_169.py`): **16 passed**. The 3
failures, all pre-existing or expected-for-this-session (CLAUDE.md "Known breaks" plus the
owed Gate E ledger row above):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed list
above), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
