# Run manifest — auto-2026-11-20-c22-periodicity

**Mode:** C (batch task execution), `--auto` with one free-form task.
**Invocation:** `/brutally-honest-review --auto "C22-PERIODICITY: port the
indicator of issue #126 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(catch22 Wang's periodicity of returns (100). Source: catch22 (Lubba et al.
2019, Data Min. Knowl. Disc. 33:1821; reference code pycatch22 1.0.2,
GPL-3.0 -- port from the definitions) — `PD_PeriodicityWang_th0_01 on the
last 100 daily returns`). Gate E and the suites are run by the launcher
afterwards."`
**Session:** headless issue-solver, worktree
`PandasTaWork/PandasTa-126-c22-periodicity`, branch
`issue-126-c22-periodicity`.

## Phase 1 — the resolved task list

| id | scope | source |
|---|---|---|
| `c22-periodicity` | Port catch22's `PD_PeriodicityWang_th0_01` over the last 100 daily returns as `pandas_ta/statistics/c22_periodicity.py`, through Gates A–D, five wiring touch points, a test module and `docs/C22PeriodicityMeasured.md`. Gate E and both repos' suites are the launcher's. | the `--auto` argument, which restates GitHub issue #126 (owner's tracker copy: `docs/issues/125-c22-periodicity.md`) |

One task, so Phase 3's execution map is trivial: main thread, no worktree
isolation, no parallel lanes.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless issue-solver session, and the
session rules say to take the most conservative reading and log it. Nothing
was asked. The decisions a human would have been asked about:

| # | open question | conservative reading taken | where it is priced |
|---|---|---|---|
| A1 | **What is "a regression spline with 3 knots"?** The paper and hctsa's operation name `spap2(2, 4, 1:N, y)`; the number and placement of knots is the one thing a reader can get wrong without noticing. | Two cubic PIECES, one interior knot, at the MIDDLE of the window, by least squares — the reading of `spap2(2, 4, ...)` — and then PRICE the four neighbouring structures rather than asserting it. Measurement settled it: the shipped structure agrees with the reference on 99.86% of 2,802 windows and the alternatives on 83.2% to 95.5%. | receipt §A1, §A5b, §P1b; `test_the_detrend_structure_is_load_bearing`, `test_the_same_spline_space_fitted_another_way_agrees` |
| A2 | **Which sample autocorrelation?** ⚠ **This row was WRONG as first written** ("Neither source pins the divisor… the BIASED one, which is what hctsa's own `CO_AutoCorr(y, k, 'Fourier')` computes") and the pre-push review gate caught it in round 1. Both sources pin it, and neither spells `CO_AutoCorr`: `PD_PeriodicityWang` writes `acf(i) = mean(y(1:N-i).*y(i+1:N))` inline and catch22's C divides by `size - tau`, both on a series catch22 z-scores BEFORE the detrend. | The SOURCE's: the lagged products averaged over the `n - k` pairs, divided by the window's PRE-DETREND variance. The biased reading that shipped first is kept in the tables as a priced DEVIATION (6 bars of 2,802; 2,794 against the reference where this reading scores 2,798). What the source line genuinely leaves open — the z-score's `ddof` and whether the residual is re-centred — is measured instead of argued: 0 bars of 2,802 each. | receipt §A5, §P1b; `test_the_shipped_autocorrelation_is_the_source_line_not_the_biased_one`, `test_the_two_conventions_the_source_line_leaves_open_move_nothing` |
| A3 | **May the GPL-3.0 reference be run as an oracle?** The issue forbids porting FROM it, and the owner's own prototype runs it to MEASURE. | The port is written from the definitions and no shipped file imports it (a test sweeps the whole package). The reference is run in ONE opt-in section of the measurement harness, labelled measurement-only, exactly as the prototype does. A bare harness run does not import it. | receipt §1, §P; harness section P; `test_the_reference_implementation_is_not_imported_by_shipped_code` |
| A4 | **What does a window whose detrended residual is numerical noise read?** The sources do not say; the quantity is mathematically defined but meaningless. | NaN (blank the bar) rather than a value, and ONE rule rather than two — the absolute 4096-eps floor applied to the RESIDUAL, which implies the same floor on the window. ⚠ Measured cost, disclosed in three documents: any deterministically SMOOTH path blanks, including a price rising one kurus a bar from 100.00, where the sibling `c22_ami_timescale` fires on all 1,400 bars. | receipt §C3, §G; `test_a_cubic_in_the_returns_never_fires_and_the_window_is_not_flat`, `test_a_deterministically_smooth_path_blanks_where_the_sibling_fires` |
| A5 | **Which value does the feature return — the lag, or an index?** hctsa's operation returns the LAG. | The lag in bars, which is also what the reference measurably returns (99.85% equal, and an exact cosine of period P reads exactly P) — so no off-by-one convention had to be guessed. | receipt §A3, §P1; `test_a_cosine_in_returns_reads_its_own_period` |
| A6 | **`MIN_LENGTH`, and does the lag ceiling scale with `length`?** | The ceiling DOES scale (`ceil(length / 3)` is in the definition, unlike `c22_ami_timescale`'s fixed 40), and `MIN_LENGTH = 30` is the smallest window leaving eight interior lags to scan and 25 residual degrees of freedom after the 5-parameter spline. Smaller or missing falls back to 100. | module docstring `Args`; receipt §H; `test_the_length_guard_band` |
| A7 | **Category and column name.** | `statistics`, following the sibling catch22 port `c22_ami_timescale` rather than `cycles` (where `ht_dcperiod` lives), because the family should not be split; `C22PERIODICITY_{length}`, the squash-the-module-name convention. | `test_the_five_wiring_touch_points` |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `c22-periodicity` | main thread | single task; needs repeated numeric measurement and judgment about what the numbers mean, which is not delegable to a self-contained subagent prompt |

## Gate

One Fletcher reviewer subagent per round, read-only (`Explore`), against the
committed-to-be files. Verdicts are quoted verbatim in
`01-c22-periodicity.md`. Round cap: 4 (session rule, which overrides the
skill's 3).

⚠ The session rule also asks for a Codex review before a push. `codex` is not
in this session's allowed command list (only `python -m pytest`, `python
docs/…` and read-only `git`), so no Codex round was run; the launcher pushes,
not this session.
