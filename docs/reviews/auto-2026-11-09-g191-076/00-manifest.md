# Auto run g191-076 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | g191-076 | issue #54 (GitHub), local tracker `docs/issues/053-g191-076.md` | Port GTJA191 alpha `#76` (variability of return-per-volume) as `g191_076`, Gates A-D, wiring, tests, `docs/G191076Measured.md`; Gate E/F run by the launcher afterward |

## Clarifications (asked ONCE, before execution)
- AskUserQuestion is unavailable in this headless session (issue-solver system
  prompt). Per that prompt's instruction, ambiguities are resolved with the
  most conservative reading and logged as ASSUMPTION rather than asked.
- ASSUMPTION: category = `volume`. The formula's only two series are `C`
  (via the return term) and `V`, and the ratio's denominator is defined
  by `V` throughout (`X = |ret|/V`, then `STD(X)/MEAN(X)`) -- matching this
  fork's existing `volume` entries built the same way (`volcv`, a
  coefficient of variation of volume itself; `g191_191`, issue #53, whose
  dominant operator's input also matched `volume`). Smallest-scope reading:
  one category, matching the issue's own candidate name ("variability of
  return-per-volume") and the `g191_146`/`g191_191` precedent of each going
  to the category its dominant operator's input matched.
- ASSUMPTION: Gate A source. `docs/pine/` and web access are unavailable in
  this worktree (stated by the system prompt), so the issue's named copy
  (HKUDS/Vibe-Trading, MIT) was never read. Gate A is derived from the
  issue's own stated formula text and the issue's own prototype
  (`docs/issues/screen/ind_screen.py:419-423`'s `cand("g191_076", ...)`),
  which itself spells out GTJA's `ret`/`STD`/`MEAN`/`sdiv` convention
  unambiguously as plain code (not prose) -- so, like `g191_146` and
  `g191_191`, no operator needed a disclosed guess.
- ASSUMPTION: Gate E/F. The system prompt overrides the issue text here:
  this session does not run `gate_e_overlap.py` or touch any path outside
  this worktree, and does not run the full suite as a gating action beyond
  `python -m pytest -q` for the record. `docs/G191076Measured.md`'s Gate E
  row says "pending, run by issue-solver after this session," per the
  system prompt's explicit instruction.
- No other gaps identified; the issue specifies the exact formula, the
  prototype function, and the gate protocol (CLAUDE.md) in full.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| g191-076 | main thread | single task, needs main-context judgment (Gate A/B/D derivations, file-scope restrictions, wiring across 5 touch points) -- no parallel lane benefit |
