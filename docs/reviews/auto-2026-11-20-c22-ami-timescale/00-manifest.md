# Run manifest — auto-2026-11-20-c22-ami-timescale

**Mode:** C (batch task execution), `--auto` with one free-form task.
**Invocation:** `/brutally-honest-review --auto "C22-AMI-TIMESCALE: port the
indicator of issue #125 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(catch22 first minimum of Gaussian automutual information (100). Source:
catch22 (Lubba et al. 2019, Data Min. Knowl. Disc. 33:1821; reference code
pycatch22 1.0.2, GPL-3.0 -- port from the definitions). Gate E and the suites
are run by the launcher afterwards."`
**Session:** headless issue-solver, worktree
`PandasTaWork/PandasTa-125-c22-ami-timescale`, branch
`issue-125-c22-ami-timescale`.

## Phase 1 — the resolved task list

| id | scope | source |
|---|---|---|
| `c22-ami-timescale` | Port catch22's `IN_AutoMutualInfoStats_40_gaussian_fmmi` over the last 100 daily returns as `pandas_ta/statistics/c22_ami_timescale.py`, through Gates A–D, five wiring touch points, a test module and `docs/C22AmiTimescaleMeasured.md`. Gate E and both repos' suites are the launcher's. | the `--auto` argument, which restates GitHub issue #125 (owner's tracker copy: `docs/issues/124-c22-ami-timescale.md`) |

One task, so Phase 3's execution map is trivial: main thread, no worktree
isolation, no parallel lanes.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in a headless issue-solver session, and the
session rules say to take the most conservative reading and log it. Nothing
was asked. The decisions that a human would have been asked about:

| # | open question | conservative reading taken | where it is priced |
|---|---|---|---|
| A1 | **Which sample correlation does "Gaussian AMI" mean?** The paper names the hctsa operation; neither pins an estimator. Three readings are defensible (lagged-pair Pearson, biased ACF, adjusted ACF). | Ship the reading the DEFINITION source spells (hctsa's `corr(y(1:end-tau), y(1+tau:end))`), and price the other two rather than asserting equivalence. ⚠ The first draft shipped the biased ACF; the black-box measurement in §A1/§A5 of the receipt is what changed it, and it changed shipped values on up to 51 bars in 1,400. | receipt §A1, §A5; `test_the_biased_reading_is_a_different_column` |
| A2 | **May the GPL-3.0 reference be run as an oracle?** The issue forbids porting FROM it, and the owner's own prototype runs it to MEASURE. | The port is written from the definitions and no shipped file imports it (a test sweeps the whole package). The reference is run in ONE opt-in section of the measurement harness, labelled measurement-only, exactly as the prototype does. A bare harness run does not touch it. | receipt §1, §A5; harness section P; `test_the_reference_implementation_is_not_imported_by_shipped_code` |
| A3 | **What does a window with an undefined correlation read?** A constant limb has no Pearson correlation; the sources do not say. | NaN (blank the bar) rather than inventing a value — the narrower behaviour. Measured cost: a flat run blanks 40 bars earlier than the "whole window flat" rule would. | receipt §C3, §G; `test_a_constant_limb_blanks_the_bar_even_when_the_window_varies` |
| A4 | **Does `TAU_MAX` scale with `length`?** | No: 40 is the operation's own parameter (it is in the feature's name), so a non-default `length` searches the same 40 lags. `MIN_LENGTH = 2 * TAU_MAX` keeps two returns per lag at the longest lag, which also makes hctsa's `ceil(n/2)` cap unreachable. | module docstring `Args`; `test_the_length_guard_band` |
| A5 | **Column name.** | `C22AMITIMESCALE_{length}`, the squash-the-module-name-and-append-the-length convention of `tf_autocorr_1e_60` → `TFAUTOCORR1E_60`. | `test_the_five_wiring_touch_points` |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `c22-ami-timescale` | main thread | single task; needs repeated numeric measurement and judgment about what the numbers mean, which is not delegable to a self-contained subagent prompt |

## Gate

One Fletcher reviewer subagent per round, read-only (`Explore`), against the
committed-to-be files. Verdicts are quoted verbatim in `01-c22-ami-timescale.md`.
Round cap: 4 (session rule, which overrides the skill's 3).
