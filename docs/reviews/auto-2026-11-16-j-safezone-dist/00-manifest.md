# auto run 2026-11-16 — J-SAFEZONE-DIST

`/brutally-honest-review --auto "J-SAFEZONE-DIST: port the indicator of
issue #121 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(distance to Elder's SafeZone stop, long (22, 2.5, lookback 3). Source:
jesse (MIT) — safezonestop.py (Rust core; Elder's definition used): L1 -
2.5*mean(down-penetrations, 22), max over 3). Gate E and the suites are
run by the launcher afterwards."`

**Mode C** (batch task execution): the argument is a free-form task, not a
plan file, so there is no Mode B pre-gate. One task.

## Phase 1 — Select

| id | scope | source |
|---|---|---|
| `J-SAFEZONE-DIST` | port jesse's `safezonestop` long-side distance as `j_safezone_dist` through Gates A–D, the five wiring touch points, `tests/test_j_safezone_dist.py` and `docs/JSafezoneDistMeasured.md` | PandasTa issue [#121](https://github.com/TolgaUyanik/PandasTa/issues/121), local copy `docs/issues/120-j-safezone-dist.md` (gitignored) |

Run folder: `docs/reviews/auto-2026-11-16-j-safezone-dist/`.

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this headless session (system prompt:
*"Where a skill says to ask, take the most conservative reading (the
smaller scope) and log it as an ASSUMPTION"*). **No questions asked.**
Four decisions took the smaller-scope reading; all four are logged in the
ASSUMPTIONS section of `docs/JSafezoneDistMeasured.md` and repeated here:

1. **Category `trend`.** The alternative was `volatility` — the stop is
   built from a downside-range average. `trend` taken on the PRECEDENT:
   the shipped column is a position relative to a trailing stop, and the
   fork's other stops (`cksp`, `vstop`, `vstop2`, `tvstop`, `psar`) are
   all in `trend`. ⚠ §L of the receipt does not settle it either way, and
   review round 1 struck the sentence that said it did: the nearest of
   the seven neighbours is a channel distance (0.7040) but the
   second-nearest is `pandas_ta/volatility/rvi` at 0.5174, with `natr`
   and `massi` at 0.2053 and 0.0911.
2. **One column, long side only.** The issue's title and quote name the
   long stop; a short-side column would be a second feature that nothing
   has screened.
3. **22 / 2.5 / 3 as module constants, not arguments.** The smaller
   surface. Same reasoning as `j_damiani` (#105), and
   `docs/gate_e_ledger.py` refuses a Gate E run taken at non-default
   parameters anyway.
4. **Column name `J_SAFEZONE_DIST_22_2.5_3`.** The fork puts parameters in
   the column name even where they are constants (`J_DAMIANI_13_40`), and
   a decimal point in a name has upstream precedent (`BBU_20_2.0`).

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `J-SAFEZONE-DIST` | main thread | one task, one file scope, and the work is judgment-heavy (a formula reading, a category choice, a mutant design). Nothing to parallelise. |

## Phase 4/5

Per-task log and every review round verbatim:
`01-j-safezone-dist.md`. Summary: `99-summary.md`, written when the loop
closes.

## Out of scope by the launcher's rules, not by choice

* **Gate E.** The launcher runs `gate_e_overlap.py` after this session.
  This session never reads or writes `../Backtesting`. The receipt says
  `Gate E: pending, run by issue-solver after this session`, and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails until the receipt session records the row — expected, and reported
  in §F1 of the receipt.
* **Gate F's parent-repo half.** The launcher runs both suites in clean
  worktrees. PandasTa's suite is run here and recorded.
* **Pushing.** The launcher opens the PR.
