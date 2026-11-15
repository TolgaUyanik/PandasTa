# Auto run — TS-BINENT-20 (PandasTa issue #89)

`/brutally-honest-review --auto "TS-BINENT-20: port the indicator of issue #89
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md ..."`

Mode C (batch task execution), one task, run 2026-11-12 on branch
`issue-89-ts-binent-20`.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `ts-binent-20` | Port *binned entropy of returns (20, 5 bins)* — tsfresh `binned_entropy(max_bins=5)` on 20 returns — through Gates A–D, the five wiring touch points, a test module and `docs/TsBinent20Measured.md`. Gate E and both repos' suites are the launcher's. | PandasTa issue #89, quoted verbatim in the session prompt |

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so every gap is
resolved by the most conservative reading (the smaller scope) and logged as an
ASSUMPTION here.

* **ASSUMPTION 1 — the degenerate window is NaN, not 0.** A window whose
  `length` returns are all equal has no range to bin. The screen prototype
  (`docs/issues/screen/ind_screen.py`, candidate `ts_binent_20`) returns NaN
  there; a literal `np.histogram` reading returns exactly 0, because numpy
  widens a zero-width range to `[v - 0.5, v + 0.5]` and puts every sample in
  one bin. NaN is the smaller-scope choice: it is the prototype's, it is this
  fork's habit for a window with nothing to report (`ts_c3_20`,
  `lean_hurst_100`), and it is what issue #89's Gate E numbers were screened
  with. The rejected reading is **priced** in `docs/TsBinent20Measured.md`
  §Gate A rather than dismissed.
* **ASSUMPTION 2 — the column name is `TS_BINENT_{length}_{bins}`.** The issue
  names the candidate `ts_binent_20` and does not name the column. The fork's
  convention is that the name carries the effective parameters
  (`TS_C3_20_1`, `LEAN_HURST_100_20`), so the default is `TS_BINENT_20_5`.
* **ASSUMPTION 3 — entropy in nats, unnormalised.** The source line says
  `binned_entropy`, whose standard form uses the natural logarithm and does not
  divide by `log(bins)`. Dividing by `log(bins)` would be a strict rescaling;
  it is priced in §Gate A.
* **ASSUMPTION 4 — `bins` is clamped to `length`.** `bins` is user-reachable
  and the module loops once per bin, so an unclamped value is unbounded work.
  One bin per sample is already the saturation point; the cost of the clamp is
  measured in §Gate A rather than asserted.
* **ASSUMPTION 5 — Gate E is the launcher's.** The session prompt forbids
  running `gate_e_overlap.py` or reading `../Backtesting`, so
  `docs/TsBinent20Measured.md` carries *Gate E: pending, run by issue-solver
  after this session* and `tests/test_gate_e_ledger.py` fails here until a
  later receipt session records the row.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-binent-20` | main thread | One indicator, five wiring touch points plus four docs files, all overlapping; every number in the receipt has to come from a run made in this context. No independent scope to parallelise. |

Gate per task: a fresh `/brutally-honest-review` Fletcher reviewer subagent,
read-only, every verdict quoted in `01-ts-binent-20.md`. Cap 3 REVISE rounds
per the skill, raised to 4 rounds total by the user's global review-loop rule.
