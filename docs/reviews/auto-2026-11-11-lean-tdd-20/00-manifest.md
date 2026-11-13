# Run manifest — `/brutally-honest-review --auto`, 2026-11-11

Mode C (batch task execution) with a single task. `--fletcher` theatrics on
automatically. No pre-gate: Mode C resolves task references, not a plan
carrying load-bearing reasoning.

## Phase 1 — the resolved task

| id | scope | source |
|---|---|---|
| `lean-tdd-20` | Port the target downside deviation at target 0 over 20 returns (QuantConnect Lean `TargetDownsideDeviation(20, 0)`) through Gates A–D, wire it at all five touch points, write `tests/test_lean_tdd_20.py` and `docs/LeanTdd20Measured.md`. Gate E and both repos' suites are the launcher's. | the `--auto` argument, which restates PandasTa issue #87 (`docs/issues/086-lean-tdd-20.md`, gitignored) |

Run folder: `docs/reviews/auto-2026-11-11-lean-tdd-20/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so every open
question was taken at its most conservative (smallest-scope) reading and
logged as an ASSUMPTION rather than asked.

| # | question | conservative answer taken |
|---|---|---|
| A1 | Which category? | `statistics`. It is a dispersion statistic of the return distribution, next to `stdev`, `skew`, `kurtosis` and to the two other return-distribution screen ports (`lean_hurst_100`, `lot_zeroret_60`). The counter-argument — its nearest neighbour `ui` is `volatility` — is recorded in the receipt's last section rather than hidden. |
| A2 | Module and column name? | The screen's candidate id, `lean_tdd_20`, and `LEAN_TDD_{length}` = `LEAN_TDD_20`. Precedent: `lean_hurst_100`, `lean_momersion_20`, `lot_zeroret_60`, `tf_centroid_20` keep the candidate name with its window and parameterise the column. |
| A3 | Expose the target as an argument? | **No.** The issue asks for *target 0*; a `target` argument absent from the column name would let two different columns ship as `LEAN_TDD_20`, which this fork's naming-is-API rule forbids, and putting it in the name would change the name the screen, the dictionary and the Gate E ledger know. Smaller scope wins. Written up in the receipt under "A reading that is not offered as an argument". |
| A4 | Simple or log returns? | Simple, `close / close.shift(1) - 1`, which is what the screen prototype's `ret(c)` is. |
| A5 | What does the warm-up emit? | NaN, this fork's convention. The partial-window alternative is priced in Gate A4 rather than assumed away. |
| A6 | Multiply by 100 to read as a percent? | No. The source formula has no factor, and a monotone factor would change the level without changing a rank. |
| A7 | The ledger row for Gate E? | NOT written. The system prompt forbids running Gate E here; `docs/gate_e_ledger.csv` is untouched, the receipt's Gate E section says "pending, run by issue-solver after this session", and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` is left failing on `['lean_tdd_20', 'mtd_ret']` as the rules require. |

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `lean-tdd-20` | main thread | One indicator, one category, overlapping edits across the five wiring points and four count-bearing documents. Nothing to parallelise, and the gate work needs main-context judgment. |

Reviewers: one fresh read-only `Explore` subagent per round, Fletcher persona,
told explicitly to re-run the harness and the suite rather than trust the
prose. Four rounds ran; see `01-lean-tdd-20.md`.
