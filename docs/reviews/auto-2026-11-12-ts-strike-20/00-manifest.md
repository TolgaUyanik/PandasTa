# Auto run — TS-STRIKE-20 (PandasTa issue #90)

`/brutally-honest-review --auto "TS-STRIKE-20: port the indicator of issue #90
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md ..."`

Mode C (batch task execution), one task, run 2026-11-12 on branch
`issue-90-ts-strike-20`.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `ts-strike-20` | Port *longest strike of returns above their mean (20)* — tsfresh `longest_strike_above_mean` on 20 returns — through Gates A–D, the five wiring touch points, a test module and `docs/TsStrike20Measured.md`. Gate E and both repos' suites are the launcher's. | PandasTa issue #90, quoted verbatim in the session prompt |

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so every gap is
resolved by the most conservative reading (the smaller scope) and logged as an
ASSUMPTION here.

* **ASSUMPTION 1 — the comparison is STRICT (`>`).** Decided from the only two
  artefacts this session can read: issue #90's line ("longest strike of returns
  **above** their mean") and the screen prototype's
  `b = W > W.mean(1, keepdims=True)` (`docs/issues/screen/ind_screen.py:124`).
  tsfresh is not installed and there is no web access, so how tsfresh itself
  spells the comparison is **unverified here** and is not asserted anywhere in
  this port. `>=` is the larger-scope reading (it marks ties), and it is
  **priced** in
  `docs/TsStrike20Measured.md` §Gate A, A5 rather than dismissed: it is
  bit-equal on 1,480 of 1,480 bars of a walk and reads 20 against this
  column's 0 on a window of equal returns.
* **ASSUMPTION 2 — the count is RAW, not divided by `length`.** The screen
  prototype returns the run length itself (the neighbouring candidate
  `ts_above_mean_20` divides, and the screen spells that division out
  explicitly, which is evidence that the absence here is deliberate).
  Normalising is a strict rescaling and is priced in §Gate A, A5.
* **ASSUMPTION 3 — the column name is `TS_STRIKE_{length}`.** The issue names
  the candidate `ts_strike_20` and does not name the column. The fork's
  convention is that the name carries the effective parameters, and this
  indicator has exactly one (`LEAN_MOMERSION_20` is the one-parameter
  precedent; `TS_C3_20_1` and `TS_BINENT_20_5` carry two).
* **ASSUMPTION 4 — a window whose returns are constant to rounding level
  reads 0, not NaN.** This is the one place the port adds something the
  prototype does not have, and it is the *smaller* scope of the two available:
  0 is the value constant returns mathematically imply (nothing can be
  strictly above their own mean), so the guard removes a reading taken off
  float64 noise without introducing a new NaN cause. Measured both ways in
  §*The rounding-noise floor*, including what the floor costs on a monotone
  fine-tick path, where the mathematical answer is **not** 0.
* **ASSUMPTION 5 — category `statistics`.** The two shipped tsfresh ports from
  the same screen (`ts_c3_20`, `ts_binent_20`) are both in `statistics`, and
  this is a statistic of the return series, not a momentum or volatility
  construction.
* **ASSUMPTION 6 — Gate E is the launcher's.** The session prompt forbids
  running `gate_e_overlap.py` or reading `../Backtesting`, so
  `docs/TsStrike20Measured.md` carries *Gate E: pending, run by issue-solver
  after this session* and `tests/test_gate_e_ledger.py` fails here until a
  later receipt session records the row.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-strike-20` | main thread | One indicator, five wiring touch points plus four docs files, all overlapping; every number in the receipt has to come from a run made in this context. No independent scope to parallelise. |

Gate per task: a fresh `/brutally-honest-review` Fletcher reviewer subagent,
read-only, every verdict quoted in `01-ts-strike-20.md`. Cap 3 REVISE rounds
per the skill, raised to 4 rounds total by the user's global review-loop rule.

## Sequencing, recorded rather than tidied

The skill writes this manifest in Phase 2, before the work. In this run it was
written after the implementation and before the first review gate, so the six
assumptions above are a record of decisions already taken in code, not a plan
the code then followed. Each one names the measurement that prices it, which is
the part that matters; the ordering is logged because this run folder is
supposed to be reconstructable, and a reader who assumed the manifest came
first would mis-read how the decisions were reached.
