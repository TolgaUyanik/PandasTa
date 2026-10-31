# volcv — measured

> **Status: Gates A, B, D measured; Gate E pending, run by issue-solver after this session.**
> Gate C is synthetic only (no real-data frame available in this session). Gate F (both repos'
> suites) is run by the launcher. Merging is the owner's call, and depends on the Gate E verdict
> this session could not produce.

`VOLCV_20 = std(volume, 20) / mean(volume, 20)`, `ddof=1` (pandas' default sample std). The window
ends at, and includes, the current bar. The value is NaN where the mean is <= 0 (an all-zero-volume
stretch). Module `pandas_ta/volume/volcv.py`, tests `tests/test_volcv.py`.

## Source

Issue #19 (migrated from the owner's local tracker, `docs/issues/021-VOLUME-VARIABILITY.md`),
citing Alpha Architect, "How Volatility and Turnover Affect Return Reversals" (the volume-dispersion
half of its turnover variable) and Kissell, R., *The Science of Algorithmic Trading and Portfolio
Management*, 2013, ch. 5 (volume variability as a participation-risk input). Both sources are cited
by the issue as *describing* the feature; the issue states explicitly that a source hit means a
feature is described, not that any claim about it was tested. No formula, window length or `ddof`
choice is fixed by either source -- the issue gives only the ratio `std(volume) / mean(volume)` over
"a rolling window". `length=20` is this port's choice, matching the window already used by several
shipped volume/volatility columns in this fork (`Volume_Ratio_20` in the parent engine's manifest,
`ROLL_20`, `TFCENTROID_20`, `MEDABSDIFF_20`), not a value from either source.

## Is it already shipped? (checked before porting)

**Not in pandas_ta.** A grep of the `volume` and `volatility` categories for `rolling(...).std()` /
`rolling(...).mean()` on raw volume found no existing coefficient-of-variation column. The issue
itself names the overlap it expects: the engine's volume **level** columns (`Volume_Ratio_20`,
`Volume_Pctl`, `Volume_State`, per the manifest) measure *how high* volume is; this measures *how
erratic* it is, over the same kind of window. The issue flags this as a guess, not a measurement,
and says Gate E should look at `Volume_Ratio_20` first -- which this session cannot run (see Gate E,
below).

## Gates

Environment: this worktree's Python (3.12), pandas and numpy as pinned by `setup.py`/`requirements`.
The synthetic numbers come from `tests/test_volcv.py` and `docs/measure_volcv.py`: 1,200 bars of
rounded lognormal(10, 0.6) volume, seed 11 (same frame as `maxvol_adv`'s suite, for comparability).

| Gate | Result |
|---|---|
| A | No Pine or vendor source exists to check line numbers against -- the issue gives only the ratio. Checked against that definition: a hand-computed 3-bar window (`std(ddof=1)/mean`, matched to `numpy.std(ddof=1)` and `numpy.mean`, `rtol=1e-12`), an independent 1,200-bar loop (`rtol=1e-12`), the 19-bar warm-up (`length - 1`), a zero-mean window reading NaN rather than inf, a NaN volume bar blanking its own output and the next `length - 1` bars (20 bars in all at the default), `offset`, and `fillna`. |
| B | Future perturbation at 31 offsets, using two futures (another walk, and the same walk x1000). The real module leaks at 0 of 31. Two one-bar look-ahead mutants (`volume.shift(-1)` feeding the mean, and the same feeding the std) are each shown to change the output, then caught at 31 of 31. |
| C | Synthetic only: 1,200-bar seed-11 walk, 1,181 non-NaN bars (1,200 - 19 warm-up), 1,181 distinct values, range 0.2867 to 1.4415. No real-data (BIST) frame is available in this session; real-data counts are Gate E's job (owed, see below). |
| D | The column reads no price. Volume x8 and x64 are bit-identical (measured: exact equality on all 1,181 non-NaN bars at both factors). x10 and x3.7 differ by at most 7.26e-15 and 1.85e-14 relative (max \|Δ\| / \|base\|) -- float rounding from the ratio's near-but-not-exact algebraic cancellation, not a correctness issue. NaN masks match in all four. `0 < fires < n`: 1,181 of 1,200 bars fire (the column is continuous, so `fires` is read as non-NaN, matching the convention `maxvol_adv` and `tf_centroid_20` use for continuous columns). |
| E | **Pending.** This session cannot reach `../Backtesting` (rule in this session's system prompt: no reads or writes outside this worktree, and Gate E is run by the launcher after this session, not by me). The issue's own "guess, not measured" is that `VOLCV_20` may correlate with `Volume_Ratio_20` on spike days; that comparator is where the launcher's run should look first. No number is stated here because none was run. |
| F | Not run here. The launcher runs both repos' suites in clean worktrees after this session. This worktree's own `python -m pytest -q` is reported below as a sanity check, not as Gate F. |

### This worktree's suite (sanity check, not Gate F)

`python -m pytest -q` in this worktree: see the commit's accompanying run. The one known
pre-existing failure is `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(CLAUDE.md "Known breaks"), unrelated to this change. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is expected to fail until the receipt session records `volcv`'s Gate E run in
`docs/gate_e_ledger.csv` -- that is the documented, expected state for an indicator with Gate E
pending, not a regression.

## Next step

A later "receipt" session runs Gate E (`gate_e_overlap.py run --module pandas_ta.volume.volcv`),
records the result in `docs/gate_e_ledger.csv`, and fills in this file's Gate E and Gate C
(real-data) rows with the measured numbers. If Gate E strikes `volcv` against `Volume_Ratio_20` or
anything else at or above the `r3-perframe-0.90` ship line, that receipt session reverts the module
and keeps this file as the record -- a measured revert closes issue #19 exactly as well as a ship.
