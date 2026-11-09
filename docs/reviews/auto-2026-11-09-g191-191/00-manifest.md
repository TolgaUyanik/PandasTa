# Auto run g191-191 — 2026-11-09

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | g191-191 | issue #53 (GitHub), local tracker `docs/issues/052-g191-191.md` | Port GTJA191 alpha `#191` (volume-low correlation plus mid-to-close gap) as `g191_191`, Gates A-D, wiring, tests, `docs/G191191Measured.md`; Gate E/F run by the launcher afterward |

## Clarifications (asked ONCE, before execution)
- AskUserQuestion is unavailable in this headless session (issue-solver system
  prompt). Per that prompt's instruction, ambiguities are resolved with the
  most conservative reading and logged as ASSUMPTION rather than asked.
- ASSUMPTION: category = `volume`. The formula's core operator is
  `CORR(MEAN(V,20), L, 5)` (volume is the only series it averages), matching
  this fork's existing `volume` entries built the same way (`pvcorr`,
  correlation of a volume transform against a price series). The price-gap
  term is a secondary addend, not the dominant operator. Smallest-scope
  reading: one category, matching the issue's own candidate name
  ("volume-low correlation...") and the precedent of `g191_146` (issue #52)
  going to the category its dominant operator's input matched.
- ASSUMPTION: Gate A source. `docs/pine/` and web access are unavailable in
  this worktree (stated by the system prompt), so the issue's named copy
  (HKUDS/Vibe-Trading, MIT) was never read. Gate A is derived from the
  issue's own stated formula text and the issue's own prototype
  (`docs/issues/screen/ind_screen.py:582-584`'s `cand("g191_191", ...)`),
  which itself spells out GTJA's `MEAN`/`CORR` convention unambiguously in
  its own module docstring and states the scale-free conversion
  (`conv = "price terms /close"`) applied before Gate E screened it -- so,
  like `g191_146`, no operator needed a disclosed guess.
- ASSUMPTION: Gate E/F. The system prompt overrides the issue text here:
  this session does not run `gate_e_overlap.py` or touch any path outside
  this worktree, and does not run the full suite as a gating action beyond
  `python -m pytest -q` for the record. `docs/G191191Measured.md`'s Gate E
  row says "pending, run by issue-solver after this session," per the
  system prompt's explicit instruction.
- No other gaps identified; the issue specifies the exact formula, the
  prototype function, and the gate protocol (CLAUDE.md) in full.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| g191-191 | main thread | single task, needs main-context judgment (Gate A/B/D derivations, file-scope restrictions, wiring across 5 touch points) -- no parallel lane benefit |
