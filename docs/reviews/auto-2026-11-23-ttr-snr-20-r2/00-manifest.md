# Auto run ttr-snr-20-r2 — 2026-11-23

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | TTR-SNR-20-R2 | pre-push review gate, round 1 of 3, HEAD `7f3a2cfe6481` (`/brutally-honest-review --auto` free-form task) | Fix every CRITICAL/MAJOR finding of that gate's REVISE verdict: three live files still asserting "Gate E pending" in a tree whose ledger row and `docs/TtrSnr20Measured.md` already record SHIP. |

## Clarifications (asked ONCE, before execution)
- none needed — the gate's findings named exact file:line locations and exact replacement
  text (the sibling #146/#145/#144 clauses' shape). No ambiguity to resolve.
- NIT finding (docs/measure_ttr_snr_20.py's `walk()` wick floor and the frozen-after-volatile
  probe's dead `n = 60` / hard-coded freeze level) fixed too: cheap, safe, single-file, matches
  the explicit instruction to take MINOR/NIT fixes when cheap and safe.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| TTR-SNR-20-R2 | main thread | single task, sequential (fix -> gate), no parallel benefit |
