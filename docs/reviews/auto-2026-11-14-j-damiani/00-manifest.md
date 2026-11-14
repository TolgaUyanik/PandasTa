# Auto-run manifest — J-DAMIANI (PandasTa issue #105)

`/brutally-honest-review --auto "J-DAMIANI: port the indicator of issue
#105 through Gates A-D, the wiring, the tests and docs/<Name>Measured.md,
per the issue and the rules in your system prompt (Damiani volatmeter,
volatility line. Source: jesse indicators (MIT) -- damiani_volatmeter:
vol = ATR13/ATR40 + 0.5*(vol[-1] - vol[-3]).). Gate E and the suites are
run by the launcher afterwards."`

Mode **C** (batch task execution): the argument is one free-form task,
not a plan file, so there is no step-0 pre-gate. `--fletcher` is on
automatically. Date: 2026-11-14. Run folder:
`docs/reviews/auto-2026-11-14-j-damiani/`.

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `j-damiani` | Port jesse's `damiani_volatmeter` volatility line as `pandas_ta/volatility/j_damiani.py` through Gates A-D, the five wiring touch points, `tests/test_j_damiani.py` and `docs/JDamianiMeasured.md`. Gate E and both repos' suites are the launcher's. | issue #105, quoted verbatim in the session's system prompt; local tracker copy at `docs/issues/104-j-damiani.md` (gitignored) |

One task, so the Phase 3 execution map is trivial: **main thread**, no
parallel lanes, no worktree isolation.

## Phase 2 — clarifications

**None were asked.** `AskUserQuestion` is unavailable in this headless
run, and the skill's rule for a mid-run ambiguity is the most
conservative reading (the SMALLER scope), logged as an ASSUMPTION. Nine
were needed:

1. **ASSUMPTION — one column, the volatility line.** Issue #105's title
   ("volatility line") and its quote (`vol = ...`) name one series.
   Whether jesse's own `damiani_volatmeter` also returns a threshold
   line is not visible from this worktree (jesse is not installed, web
   access is unavailable), and no threshold line was screened at Gate E,
   so shipping one would be both the wider scope and the unmeasured one.
2. **ASSUMPTION — no parameter surface.** `FAST = 13`, `SLOW = 40`,
   `LAG_S = 0.5`, `NEAR = 1`, `FAR = 3` are module constants. A
   `fast=`/`slow=` surface would ship parameter combinations nothing has
   measured. Pinned by
   `tests/test_j_damiani.py::test_the_constants_are_the_issues_numbers`,
   which also pins the signature.
3. **ASSUMPTION — "ATR" is Wilder's `alpha = 1/n`, `adjust=False`,
   seeded at the first true range.** The issue's word and the screen
   prototype's spelling. `docs/JDamianiMeasured.md` §A4 prices the four
   alternatives in reach — SMA-seeded (`wilder_rma`/Pine `ta.rma`), this
   fork's `rma`, a plain EMA, this fork's `true_range` — and the alpha
   is the load-bearing one (0 bars in common, Spearman 0.8278 ..
   0.8885).
4. **ASSUMPTION — the true range is spelled in the module, not
   imported.** This fork's `true_range` adds an epsilon to EVERY bar of
   the series once any bar has `high == low`, and NaNs bar 0. §A4(d)
   measures both divergences instead of assuming they are negligible
   (Spearman 0.7401 .. 0.9958 on the varying frames; on a flat frame the
   fork's spelling fires on 1,496 bars where the module fires on 0).
5. **ASSUMPTION — category `volatility`**, where `natr`, `massi` and
   `atr` live. The issue does not fix one.
6. **ASSUMPTION — name `j_damiani`, column `J_DAMIANI_13_40`.** The
   issue's candidate id, and the suffix is the two ATR lengths.
7. **ASSUMPTION — no invented warm-up.** The column fires from bar 3 (the
   loop's `vol[-3]`), as the formula and the prototype do; the early
   transient is kept rather than NaN'd, because NaN-ing it would depart
   from the form Gate E measured. §A3.
8. **ASSUMPTION — one guard, on the divisor only**
   (`slow.where(slow > 0.0)`). §G2 measures that an infinite price needs
   no guard of its own, §G3 what the guard buys at a real price scale
   (numpy raises on the bare `0 / 0`; pandas currently suppresses it, so
   the guard is what makes the behaviour the module's own), and §G5(d) —
   added in review round 1 — the subnormal regime where the unguarded
   form reads `inf`, which is why the division's RESULT needs no guard
   of its own.
9. **ASSUMPTION — Gate A is a 1e-12 bound against the independent oracle
   and bit-equality against the prototype.** The oracle is a different
   spelling and is not obliged to round the same way; the prototype is
   the same operations in the same order, and that limb is what ties
   this port to the screen's Gate E figures.

Two rules from the system prompt also shaped the work and are not
assumptions:

* **Gate E is the launcher's.** `../Backtesting` is never read; §E says
  "pending, run by issue-solver after this session", the ledger has no
  row, and `test_the_gate_e_row_is_owed` asserts that.
* **Gate F is the launcher's** for both repos in clean worktrees. This
  session ran the module's tests, the same tests under
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, and the
  full suite here.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `j-damiani` | main thread | one task; it needs repo-wide judgment (five wiring touch points, three docs, the measurement script) and nothing runs in parallel with it |

## Files this run touches

Added:

* `pandas_ta/volatility/j_damiani.py`
* `tests/test_j_damiani.py`
* `docs/measure_j_damiani.py`, `docs/measure_j_damiani_cpu.py`
* `docs/JDamianiMeasured.md`
* `docs/reviews/auto-2026-11-14-j-damiani/` (this folder)

Modified:

* `pandas_ta/volatility/__init__.py` (export)
* `pandas_ta/__init__.py` (`Category["volatility"]`)
* `pandas_ta/core.py` (`df.ta.j_damiani()`)
* `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 343 → 344,
  `CATEGORY_BUCKETS["volatility"]` 35 → 36)
* `README.md` (343 → 344, 351 → 352, `volatility (35)` → `(36)`)
* `docs/IndicatorDictionary.md` (regenerated by its own script)
* `docs/MLCompanionContract.md` (688 → 689 tagged, 327 → 328 `SF`)

Nothing outside the system prompt's allowed list; `docs/issues/` is read
only and never staged.

## Phase 4 — the gate

Per task log in `01-j-damiani.md`; summary in `99-summary.md`.
