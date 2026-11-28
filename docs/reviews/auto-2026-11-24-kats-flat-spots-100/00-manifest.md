# Manifest — KATS-FLAT-SPOTS-100 (issue #161)

Mode: C (batch task execution), single task, invoked via `/brutally-honest-review --auto`.

## Task

Port the indicator of issue #161 ("flat spots: longest run of unchanged closes within
10-bar chunks (100)", Kats tsfeatures `get_flat_spots`) through Gates A-D, the wiring, the
tests and `docs/FlatSpotsMeasured.md`, per the issue and the issue-solver system prompt's
rules. Gate E and the whole suites are explicitly out of scope (run by the launcher
afterwards).

## Clarifications

None needed — the issue text and `CLAUDE.md`'s porting protocol fully specify scope. One
ASSUMPTION was made and logged in `docs/FlatSpotsMeasured.md` Decision 2: the issue's own
ref string for this candidate ("max groupby run length per n/10 chunk") and the
prototype's code (`docs/issues/screen/ind_screen_r5.py` L107-116) both describe a
TIME-chunked reading of Kats' `get_flat_spots`, not Hyndman's R `tsfeatures::flat_spots`
VALUE-binned reading (`cut(x, breaks=10)` over the whole series' range). Took the more
conservative, narrower-scope reading: port exactly what the prototype implements and the
issue's own ref string names, not the R original.

## Execution map

Single task, main thread (no parallel lanes — one indicator, no independent sub-scopes).

## Clarifications log

None asked; none needed.
