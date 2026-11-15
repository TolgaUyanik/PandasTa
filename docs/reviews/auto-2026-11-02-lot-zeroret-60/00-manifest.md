# Auto run lot-zeroret-60 — 2026-11-02

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | LOT-ZERORET-60 | issue #39 (verbatim in session system prompt) | Port `lot_zeroret_60` (share of zero-return days, length 60) through Gates A-D, wiring, tests and `docs/LotZeroret60Measured.md`; Gate E and both repos' suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- `AskUserQuestion` is unavailable in this issue-solver session (system-prompt rule);
  per that rule, gaps are resolved with the most conservative reading and logged as
  ASSUMPTIONs below instead of asked.

### ASSUMPTIONs logged in place of clarification
- **Category = `statistics`.** The issue doesn't name a category. `lot_zeroret_60` is a
  rolling count/share statistic of daily returns, the same family as this repo's own
  `osap_retskew_21` (#36), `kpss`, and `cusum` — all return/price-based statistics,
  all in `statistics`. No sibling category (`performance`, `volume`, `momentum`) fits
  as well: `performance` ships raw returns, not derived statistics of them; `volume`
  is explicitly the wrong axis per the issue itself (zero-volume days are the OSAP
  analogue this port deliberately substitutes away from).
- **Column name = `LOT_ZERORET_{length}`.** Follows the existing
  `OSAP_RETSKEW_{length}` / `VOLTREND_{length}` convention (uppercase name + length
  suffix), not a judgment call beyond that pattern match.
- **Gate B test design.** A first attempt built the future-perturbation sweep on a
  plain sparse random walk (same style as `osap_voltrend_60`/`osap_retskew_21`'s
  fixtures) and only caught 3 of 28 offsets against a `center=True` mutant, because
  exact zero-return ties are rare by chance, so most perturbed windows carried the
  same (zero) count in both arms by luck, not by causality. Replaced with a
  deterministic tie-every-4th-bar series spliced with a tie-free tail at each offset,
  which catches 28 of 28. Logged in the module's test docstring and
  `docs/LotZeroret60Measured.md`, not silently swapped.
- **`CONST` tag on the generated dictionary.** The 600-bar synthetic probe frame is a
  continuous-valued random walk that (bar engineered exceptions) essentially never
  produces an exact price tie, so `docs/gen_indicator_dictionary.py` tags
  `LOT_ZERORET_60` `CONST` on that probe. `cdl_pattern`'s 23 `CONST` columns get an
  explicit "fixture artifact, not a defect" line in the generated dictionary itself,
  via a `DEAD_TASKS` dict entry inside `docs/gen_indicator_dictionary.py` -- that file
  is NOT on this session's allowed-modify list (`pandas_ta/{category}/*.py`,
  `tests/test_*.py`, `docs/*Measured.md`, `docs/measure_*.py` and a short fixed list of
  other files are the only touchable ones), so no `DEAD_TASKS` entry was added and the
  committed `docs/IndicatorDictionary.md` "Never fires on the probe" table still shows
  `lot_zeroret_60` under the script's generic fallback, "— unregistered, file one" --
  the same boilerplate several already-shipped, genuinely-registered indicators carry
  (e.g. `vfi`, `xsignals`), not something unique to this port, and not a claim that the
  column is actually unregistered (`tests/test_lot_zeroret_60.py::test_name_registration_and_accessor`
  proves it is). The real disclosure -- that the column fires and is non-constant once
  exact ties exist -- lives in `docs/LotZeroret60Measured.md` and the narrative
  paragraph added to `docs/MLCompanionContract.md`, not in that table row.
- **Gate E.** Left pending per the issue-solver system prompt's override rule — the
  launcher runs it after this session; `docs/LotZeroret60Measured.md` says so
  explicitly rather than fabricating a number.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| LOT-ZERORET-60 | main thread | single indicator port; the five wiring touch points and the docs are sequentially dependent (module before export before Category before accessor before tests before docs), no parallelizable sub-scope |
