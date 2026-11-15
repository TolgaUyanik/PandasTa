# Auto run — SK-FCB-POS (PandasTa issue #108)

**Mode:** `/brutally-honest-review --auto "<task>"` → **Mode C**, batch task
execution, one task. `--fletcher` theatrics on automatically. No pre-gate: Mode
C resolves task references, not plans carrying load-bearing reasoning.

**Date:** 2026-11-15 · **Run folder:** `docs/reviews/auto-2026-11-15-sk-fcb-pos/`
· **Branch:** `issue-108-sk-fcb-pos`

## Phase 1 — Select

| id | scope | source |
|---|---|---|
| `sk-fcb-pos` | Port `sk_fcb_pos` — close's position inside the Fractal Chaos Bands (span 2), Skender Stock.Indicators' `Fcb` (Apache-2.0) — through Gates A–D, the five wiring touch points, tests and `docs/SkFcbPosMeasured.md`. Gate E and both repos' suites are run by the launcher afterwards. | the `--auto` argument, which restates PandasTa issue #108 and the issue-solver rules in the session prompt |

One task, so Phase 3's execution map is trivial: **main thread**, no worktree
isolation, no parallel lanes.

## Phase 2 — Clarify (once, batched)

`AskUserQuestion` is **unavailable** in this headless session, and the session
rules say: take the most conservative reading (the smaller scope) and log it as
an ASSUMPTION. Three gaps were found and all three were resolved that way.

### ASSUMPTION 1 — category is `momentum`

The issue does not name a category; the Gate E command template in it reads
`pandas_ta.<category>.<name>`. The sibling width (#107) went to `volatility`.

**Taken:** `momentum`. The column is a *position in a range*, which is what
`willr`, `stoch`, `cci` and `pgo` are — and those are exactly the comparators
the 2026-10-24 screen found nearest (`pgo` 0.8348, `willr` 0.8303,
`kdj_J_9_3` 0.8256). The conservative reading is the one that puts the column
next to the indicators it measures like, so a category sweep groups it with its
neighbours rather than with a width.

**Blast radius if wrong:** the module path and `Category` bucket only. The
column name `SK_FCB_POS_2` does not encode the category, so a later move would
not rename a shipped column. Recorded in `docs/SkFcbPosMeasured.md` §W.

### ASSUMPTION 2 — the inverted band is KEPT, not masked

`upper - lower` can be negative (the sibling measured the same difference
negative on 5…91 bars per frame). A "position" with a negative denominator is
inverted, and masking it would be defensible.

**Taken:** keep it, exactly as the screen prototype does
(`sdiv(c - lo, up - lo)`, `docs/issues/screen/ind_screen_r2.py:170-172`, whose
only guard is `±inf → NaN`). That is the smaller change: it is the expression
Gate E's 0.8348 was measured on, so keeping it preserves the tie between the
port and the figure the issue quotes. Masking would make the port a *different*
column from the one the screen measured, which is a larger scope, not a
smaller one.

**Priced rather than assumed away:** §C4 measures the alternative. Masking
differs on exactly the crossed bars and nowhere else (Spearman 1.0000, 0.0 max
difference on the bars both fire), and
`test_masking_the_inverted_band_differs_only_on_those_bars` asserts that
identity on every firing frame.

### ASSUMPTION 3 — the band helper is IMPORTED, not copied

`_last_fractal` already ships in `pandas_ta/volatility/sk_fcb_width.py` from
#107, and the session rules forbid editing an existing helper module.

**Taken:** import it. `CLAUDE.md` says "Do not add a fourth copy: import the
function", and a copy would let the two columns drift to different spans.
Importing touches no existing file, which is the smaller blast radius.

**The cost, stated rather than discovered later:** an edit to `_last_fractal`
moves this column without moving this module's file. What catches that is the
Gate E ledger's `output_fp`, a live fingerprint on a fixed frame rather than a
file hash (`docs/gate_e_ledger.py`), plus
`test_the_band_helper_is_the_shipped_sibling` and the three Gate B mutants that
edit that file deliberately.

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `sk-fcb-pos` | main thread | one task, and the measurement script, the module docstring, the receipt and the tests all have to agree number for number — that is main-context judgment, not a parallelisable edit |

## Out of scope, by the session rules rather than by choice

* **Gate E** — the launcher runs `gate_e_overlap.py`. This session never reads
  or writes `../Backtesting`, writes the Gate E section as *pending*, and does
  **not** add a ledger row.
* **Gate F** — the launcher runs both repos' suites in clean worktrees. This
  session runs `python -m pytest -q` here and the reduced-CPU re-run.
* **The push and the PR** — the launcher's.

## Files the run may touch

Per the session rules. Modify: `README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md`, `docs/gate_e_ledger.csv`,
`pandas_ta/__init__.py`, `pandas_ta/core.py`,
`pandas_ta/{category}/__init__.py`, `tests/test_altport2_ports.py`. Add:
`pandas_ta/{category}/*.py`, `tests/test_*.py`, `docs/*Measured.md`,
`docs/measure_*.py`, `docs/reviews/**`.

`docs/gate_e_ledger.csv` was **not** touched: Gate E is owed, so there is no
row to record.
