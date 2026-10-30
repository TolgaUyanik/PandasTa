# max_return — measured

> **Status: Gates A, B and D pass; C and E are owed (issue [#12](https://github.com/TolgaUyanik/PandasTa/issues/12)).**
> Gate E and Gate C's real-data counts need the private Backtesting engine and the BIST cache,
> which the author's machine does not have. Until a Gate E run is recorded in
> `docs/gate_e_ledger.csv`, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails on this branch, and that is the one failure (see Gate F). Merging is the owner's call.

`MAXRET_21` is the largest one-bar simple return, `close_t / close_{t-1} - 1`, over the last 21
bars, the current bar included. It is the "MAX" lottery measure: stocks with a recent extreme
up-day have been found to earn lower returns afterwards. Module
`pandas_ta/performance/max_return.py`, tests `tests/test_max_return.py`, branch
`issue-12-max-lottery`.

## Source

Bali, Cakici and Whitelaw (2011), "Maxing out: Stocks as lotteries and the cross-section of
expected returns", *J. Financial Economics* 99: MAX is the maximum daily return within the past
month. The issue found it through Alpha Architect (*Hot off the JFE Press: Maxing Out…your
returns?*) and Quantpedia (*Lottery Effect in ETFs Across Several Asset Classes*). The definition
above is the paper's as those sources describe it; the paper was not re-opened for this port.

**Port vs. source, two deliberate differences.**

1. **Rolling window, not calendar month.** The paper takes the maximum within each calendar month.
   The port takes it over a rolling `length`-bar window, default 21 (about one trading month, the
   issue's `n ≈ 21`), so every bar has a value.
2. **MAX(k) is not ported.** The issue lists "optionally the mean of the top-k" (the paper's MAX(k)
   variant). One column means one Gate E row; MAX(k) can follow if MAX(1) survives Gate E.

The column is a simple return as a fraction (0.05 = +5%), the same unit as `percent_return`'s
`PCTRET_1`. Returns are computed as a price ratio minus one, which keeps the column bit-identical
under ×8 and ×64 (Gate D).

## Is it already shipped? (checked before porting, 2026-10-30)

**Not in pandas_ta.** `git grep -i -E "lottery|max_return|maxret|bali|cakici" origin/dev` (excluding
the untracked `docs/pine/`) returns no hits. `git grep -E "pct_change\(.*\)\.rolling|rolling\(.*\)\.max\(\)" origin/dev -- pandas_ta`
returns 45 lines, read through by hand: maxima of price (`high`, `close`, `hl2`), of volume
(`maxvol_adv`, `pocket_pivot`), of an oscillator or OBV (`stochrsi`, `stc`, `aobv`), and the
generic Pine `highest` helper in `utils/_pine.py`, whose callers (`frama`) pass `high`. None is a
maximum of one-bar returns, and no `pct_change(...).rolling` matched. The issue records the engine's side: `Ret_*_pct` and
`natr` in the manifest, neither a rolling maximum. The issue's guess, not measured here, is that
this column correlates with `natr` and `Ret_21d_pct`; Gate E measures it. Over a window, the
largest return grows with volatility, so a high ρ against `natr` would not be surprising. If Gate E
strikes it, a measured revert closes the issue as well as a ship does.

## Gates

Environment for Gates A, B and D: the author's machine, Windows, Python 3.13.14. Two venvs:
`.venv-pd2` with pandas 2.3.3, numpy 2.5.4 and TA-Lib 0.7.1, and `.venv` with pandas 3.0.0 and
numpy 2.4.2. `tests/test_max_return.py` passes in both: 16 of 16. The synthetic numbers come from
`tests/test_max_return.py`: 1,200 bars of a geometric random walk, σ = 1.5%, rounded to 0.01,
seed 11.

| Gate | Result |
|---|---|
| A | **Against the definition:** a pure-Python loop of `(c_i - c_{i-1}) / c_{i-1}` and `max`, on a 400-bar walk: max absolute difference 1.1e-16 at lengths 21, 5 and 1, NaN masks identical (asserted atol 1e-15). `close.pct_change().rolling(length).max()` matches exactly (`assert_series_equal`). **Hand-computed:** closes 100, 110, 99, 99, 108.9 at length 3 → 0.1, 0.1, arithmetic in the test. **Behaviour:** a single +10% step reads 0.10 on exactly the 21 bars whose window holds it, 0 before and after. **Edges:** a NaN, zero or negative close removes the two returns that touch it and blanks 22 bars at the default (never inf). The warm-up is 21 bars. `length` below 1 falls back to 21; 21 closes return None, 22 return one value. `offset` and `fillna` are covered. |
| B | Future perturbation at 31 offsets, with two futures (another walk, and the same walk ×1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`importlib` source read, `exec`'d in memory) are each shown to change the output, then caught at 31 of 31: the return series read one bar ahead, and the output written one bar early (`.shift(-1)`). There is no recursive stage, so the taint reach is exactly the `length + 1`-close window. |
| C | **Owed.** Real-data counts come from the Gate E run. Synthetic: 1,179 non-NaN bars, 109 distinct values (a maximum holds until it leaves the window), range 0.0090 to 0.0559. None is zero or negative on this walk, but the column can be: in a window where every bar falls, the largest return is negative. |
| D | Close ×8 and ×64 are bit-identical. ×10 and ×3.7 differ by at most 2.2e-16 absolute; the test asserts ≤ 1e-14. NaN masks match in all four. The column is continuous, so `0 < fires < n` is replaced by nunique = 109 over 1,179 non-NaN bars (see C). |
| E | **Owed.** From `../Backtesting/Backtesting`, with `issue-12-max-lottery` checked out as the PandasTa sibling (`record` checks the run's `pandas_ta_src_sha1` against this tree): `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.performance.max_return --name <run name>`, then `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`. No prototype measurement exists for this candidate. |
| F | **No regressions in this repo** (below). Backtesting not run. |

### Gate F (2026-10-30, the author's machine, `.venv-pd2`)

Run with CI's two `--deselect`s:

* `dev` at `9b964a8`: 0 failed, 3258 passed, 83 skipped.
* this branch: 1 failed, 3274 passed, 83 skipped. The +16 passes are `tests/test_max_return.py`.

The one failure is `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, for
`max_return`, and it clears when the Gate E row lands.

## Dictionary row provenance

`docs/IndicatorDictionary.md` was **fully regenerated**, not hand-patched, with
`.venv-pd2/Scripts/python docs/gen_indicator_dictionary.py` (pandas 2.3.3, numpy 2.5.4, TA-Lib
0.7.1). The diff against `dev` (`git diff origin/dev -- docs/IndicatorDictionary.md`, enumerated
line by line on 2026-10-30) is:

* the `max_return` row (`MAXRET_21` SF, warm-up 21) and the heading `performance (4)` →
  `performance (5)` (the dictionary counts `drawdown`, which is outside `Category`);
* the counts: 240 probed, 238 in `Category`, 246 callable as `df.ta`;
* the *Feed-ready shortlist* gains two entries, `max_return` and `range_compress_run`. The second
  is not this port's: the 2026-10-26 hand-patch added the `range_compress_run` row but not its
  shortlist entry, and the regeneration fills that gap (PRs #209 and #212 do the same);
* the probe date, and the numpy version in *Known breaks*;
* the removal of the header notes about hand-patched rows, because the rows they covered (`pfe`,
  `kalman_trend`, `range_compress_run`, `dpo`, `maxvol_adv`) came out unchanged.

README: 238 in `Category`, 246 callable, `performance (4)`. `docs/MLCompanionContract.md` follows
the dictionary: 571 tagged columns, 217 `SF`.

**Conflicts with PRs #209 (kpss) and #212 (cusum).** All three raise the same counters from the
same base. `max_return` is wired in `performance`, which neither of the others touches, so the
code wiring merges cleanly. `git merge-tree` against each branch (2026-10-30) conflicts in
`docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` and `tests/test_altport2_ports.py`.
⚠ `README.md` does **not** conflict, and that is the trap: both sides make the identical change
237 → 238 / 245 → 246, so git keeps one copy and the merged README says 238 where it should say
239. `tests/test_readme_counts.py` compares the README to the live package and fails on it, so CI
catches it, but it must be fixed by hand. Each later merge: rebase, regenerate the dictionary, and
add one per port already merged to the README headline and callable counts, the
`MLCompanionContract.md` tagged and `SF` counts, and `CATEGORY_TOTAL`.

`docs/indicators/max_return.md` was not generated. `docs/gen_indicator_pages.py` reads Gate E runs
from `../Backtesting`, which is absent here, so on this machine it rewrites unrelated pages.
