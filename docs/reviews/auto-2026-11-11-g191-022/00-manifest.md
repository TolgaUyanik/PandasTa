# Run manifest — `/brutally-honest-review --auto`, 2026-11-11, runid `g191-022`

Mode C (batch task execution), one task. Fletcher reviewer gate on every
round, max 3 REVISE rounds per task. Reports in this folder.

## Phase 1 — resolved task list

| id | scope | source |
|---|---|---|
| `g191-022` | Port GTJA191 alpha `#22` (smoothed 3-day change of the 6-day bias) as `g191_022` through Gates A–D, wire it, test it, write `docs/G191022Measured.md`. Gate E and both repos' suites are the launcher's, not this session's. | issue-solver task for TolgaUyanik/PandasTa #82, quoted verbatim in the session prompt |

Run folder: `docs/reviews/auto-2026-11-11-g191-022/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session (session prompt:
"Where a skill says to ask, take the most conservative reading (the smaller
scope) and log it as an ASSUMPTION"). **No questions were asked.** The gaps
and the conservative reading taken for each:

* **ASSUMPTION 1 — category.** The issue does not name one. `momentum` is
  chosen: the column is a smoothed change of a bias (a close-vs-mean
  deviation), and the fork's own `bias` — the identical inner term at
  `length=6` — is a `momentum` indicator (`pandas_ta/momentum/bias.py`).
  One new module file, the smallest allowed scope (the session prompt
  permits up to 3).
* **ASSUMPTION 2 — literal spelling over the shipped `bias` helper.** The
  inner term `(C-MEAN(C,6))/MEAN(C,6)` is algebraically `bias(close, 6)`
  (`(close / sma) - 1`). The port spells it the SOURCE's way, not the
  helper's, because Gate A compares bit-for-bit against the issue's own
  prototype, which writes the subtraction form. The two spellings' float
  difference is measured rather than assumed (`docs/measure_g191_022.py`,
  and `docs/G191022Measured.md`'s redundancy section).
* **ASSUMPTION 3 — `min_periods` on the GTJA `SMA`.** The prototype's own
  `sma` (`ind_screen.py:57-59`) carries no `min_periods`; this fork's
  sibling GTJA ports do (`g191_109.py:101`, `g191_152.py:144`). The port
  follows the FORK, and both variants are measured so the warm-up is not
  claimed as the source's.
* **ASSUMPTION 4 — Gate E and Gate F.** Not run here. Gate E is written as
  "pending, run by issue-solver after this session" per the session prompt,
  and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  is expected to fail until the receipt session records the row. Gate F is
  this repo's suite only.

No destructive or irreversible step is in scope. Nothing is pushed; the
launcher pushes.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `g191-022` | main thread | Single task, heavy judgment (Gate A reading of the source string, mutant design, measured prose). No parallel lane to isolate, no file-scope conflict to avoid. |

File scope (the session prompt's allowlist):

* add `pandas_ta/momentum/g191_022.py`, `tests/test_g191_022.py`,
  `docs/measure_g191_022.py`, `docs/G191022Measured.md`, this folder;
* modify `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`,
  `pandas_ta/core.py`, `tests/test_altport2_ports.py`, `README.md`,
  `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`.

`docs/gate_e_ledger.csv` is NOT touched: the Gate E run that would feed a
row is the launcher's.
