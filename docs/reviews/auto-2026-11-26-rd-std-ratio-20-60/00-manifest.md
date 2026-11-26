# Run manifest — rd-std-ratio-20-60 (issue #179), 2026-11-26

Mode C, single task, batched via `/brutally-honest-review --auto`.

## Task

> RD-STD-RATIO-20-60: port the indicator of issue #179 through Gates A-D, the wiring, the tests
> and docs/<Name>Measured.md, per the issue and the system-prompt rules (price sd over its own
> 60-bar average (20); Reddit tier 4 rd:algotrading:1lezs3n; `normalized_vol = std(close, p) /
> mean(std(close, p), 3p)`, p=20). Gate E and the whole suites run by the launcher afterwards.

## Clarifications

None needed. Issue text, prototype (`docs/issues/screen/ind_screen_r6.py`), and this fork's own
`rd_obv_dev5`/`rd_range_contraction` ports supplied a complete template for category choice
(volatility), parameter naming, and docstring/test/receipt shape.

## Execution map

Single task, main thread (no parallel lanes — one indicator, sequential Gate A→D→wiring→docs).

## Gate (Fletcher review)

One round. **PASS** with one MINOR finding (Gate D docstring didn't explicitly distinguish its
sound deviation-first variance computation from `avwap_z`'s documented catastrophic-cancellation
risk). Fix applied inline (one sentence added to the module docstring and to
`docs/RdStdRatio2060Measured.md`'s Gate D section) — see `01-rd_std_ratio_20_60.md`.
