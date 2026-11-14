# 00 — manifest · `/brutally-honest-review --auto` · J-GATOR (issue #104)

**Run id:** `j-gator` · **Date:** 2026-11-14 · **Mode:** C (batch task execution)
**Branch:** `issue-104-j-gator` · **Worktree:** `PandasTaWork/PandasTa-104-j-gator`

## Phase 1 — the resolved task list

| # | task | scope | source |
|---|------|-------|--------|
| 01 | `j-gator` | Port the Bill Williams gator oscillator of PandasTa issue #104 through Gates A–D, the five wiring touch points, `tests/test_j_gator.py` and `docs/JGatorMeasured.md`. Gate E and both repos' suites are the launcher's. | the session prompt's `--auto` argument, quoting issue #104 |

One task, so Phase 3's parallel map is trivial: **main thread**, no worktree isolation.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session (system prompt), so the
skill's rule applies: take the **most conservative reading — the smaller scope —
and log it as an ASSUMPTION**. Eight were needed.

* **A1 — one column.** The issue quotes the source as
  `gatorosc: |jaw-teeth| - |teeth-lips|`, a single series, and the screen
  prototype (`docs/issues/screen/ind_screen.py`, candidate `j_gator`) returns one
  column. That single difference is therefore both the smaller scope and the
  only form Gate E has ever been measured on. ⚠ What jesse's own `gatorosc`
  returns is NOT visible from this worktree (not installed, no web access), so
  it plays no part in the decision; §L2 prices the two spreads the formula is
  built from, which is the scope question this answers.
  ⚠ Corrected in review round 2: the first version of this line asserted that
  jesse returns `upper`/`lower` and their changes separately — a fact about an
  unread source, the same defect as A3's.
* **A2 — no new parameter surface.** The three SMMA lengths (13, 8, 5) and their
  three forward lags (8, 5, 3) are Bill Williams' constants and are module
  constants here, not arguments. A six-parameter signature would admit
  length/lag pairs the source never defines.
* **A3 — SMMA is read as Wilder's `alpha = 1/n`, `adjust=False`, seeded at the
  first value.** That is the screen prototype's spelling and the usual reading
  of the issue's `SMMA(mid,n)`. ⚠ **jesse's own smoother is not read here** —
  jesse is not installed and web access is unavailable — so nothing in this
  port is evidence about what jesse computes; the reading rests on the issue's
  wording and on the prototype Gate E measured. The three alternatives are
  measured rather than dismissed (§A4 of `docs/JGatorMeasured.md`): the
  SMA-seeded "smoothed MA" (TradingView's `ta.rma`) and this fork's `rma`
  (`adjust=True, min_periods=length`) are WARM-UP differences, Spearman
  0.9932 .. 0.9998; the `alpha = 2/(n+1)` plain-EMA reading is a different
  column, Spearman 0.5165 .. 0.7075, and is the one the issue's word "SMMA"
  excludes.
  ⚠ Corrected in review round 1: the first version of this line, and of the
  module docstring, cited "jesse's `numpy_ewma`" as corroboration. That
  function name appears nowhere in the issue, in the screen's
  `candidates.csv`, or in the prototype — it was asserted from outside the
  evidence, which is this repo's named dominant defect. The citation is gone
  and the alpha reading is now priced against the EMA alternative instead.
* **A4 — category `momentum`.** It is an oscillator built from `(high + low)/2`,
  which is where `ao` (the other Bill Williams oscillator) lives.
* **A5 — name `j_gator`, column `J_GATOR_13_8_5`.** The issue's own candidate
  name (as `TS-REOCCUR-20` → `ts_reoccur_20`); the suffix is the three SMMA
  lengths, with the lags documented as the constants they are.
* **A6 — no invented warm-up.** The column first fires at bar 8 (the longest
  lag), exactly as the source and the prototype do: the seeded EWMA is defined
  from bar 0. The early-bar transient that follows is measured and disclosed,
  not NaN'd away, because NaN'ing it would depart from the form Gate E measured.
* **A7 — ONE guard, on the divisor only.** `close` must be finite and at least
  `np.finfo(float).tiny`, else the bar is NaN (it empties its own bar and no
  other, §G1). A `mid` guard — `mid.where(np.isfinite(mid))` — was written
  first and then **measured to be a no-op and removed**: pandas'
  `_prep_values` converts an infinity to NaN before the `ewm` kernel runs and
  `ewm` skips a NaN observation, so an inf bar and a NaN bar give
  bit-identical columns with 0 non-finite readings (§G3). That pandas
  behaviour is now something the module relies on, so
  `tests/test_j_gator.py::test_an_infinite_price_never_reaches_the_output`
  pins it, and the module's comment names the one-line fix if an upgrade ever
  breaks it. No other rule is invented: the recursion SKIPS a bad bar and the
  contamination decays with the filter's memory (§G2) instead of NaN'ing the
  whole tail, which is what an infinite-memory filter would otherwise require.
  §G5 names what stays unguarded (a frame whose high/low and close are
  hundreds of orders of magnitude apart overflows the division).
  ⚠ Corrected in review round 1: this line described the mid guard as shipped
  after it had been measured away.
* **A8 — Gate A is a bound against the independent oracle, bit-equality
  against the prototype.** pandas' `ewm` divides by `(1 - alpha) + alpha`, which
  is not exactly 1.0 for every alpha, so an independently spelled recursion is
  not OBLIGED to be bit-equal to it. §A1 measures 0.000e+00 on all seven frames
  — that sum is exactly 1.0 for alpha = 1/13, 1/8 and 1/5 here — and the test
  still asserts a bound (absolute and relative, 1e-12), so the limb does not
  pin this machine's kernels.
  ⚠ Corrected after review round 4: the first version of this line said the
  oracle "is not bit-equal to it", flatly, above a table of zeros.

Two constraints from the session prompt, recorded because they shape the task's
"done":

* **Gate E is the launcher's.** `gate_e_overlap.py` is not run here and
  `../Backtesting` is never read. `docs/JGatorMeasured.md` §E says
  "pending, run by issue-solver after this session", and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails until the receipt session records the row. That failure is expected.
* **Gate F is the launcher's.** `python -m pytest -q` is run here; both repos'
  clean-worktree suites are not.

## Phase 3 — execution map

| task | lane | why |
|------|------|-----|
| 01 `j-gator` | main thread | single task; needs main-context judgment on the gate protocol in `CLAUDE.md`; nothing to parallelise against |

Gate: a fresh Fletcher reviewer subagent (`Explore`, read-only) per round, cap 3
REVISE rounds, verdicts quoted verbatim in `01-j-gator.md`.
