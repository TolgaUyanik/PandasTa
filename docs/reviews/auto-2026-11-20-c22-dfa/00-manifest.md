# Auto run 2026-11-20 — c22-dfa (`/brutally-honest-review --auto`)

**Mode C** (batch task execution): the argument is a TASK reference, not a plan file,
so there is no step-0 pre-gate — Mode C resolves tasks, which do not carry
load-bearing reasoning the way a plan does. `--fletcher` is on automatically.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `c22-dfa` | Port the indicator of issue #128 (catch22 `SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1` on the last 100 daily returns) through Gates A-D, the five wiring touch points, the tests and `docs/C22DfaMeasured.md`. Gate E and both repos' suites are run by the launcher afterwards. | the invocation, and the issue text in this session's system prompt (`docs/issues/127-c22-dfa.md` is the owner's local copy) |

One task, so there is nothing to parallelise and no ordering to resolve.

## Phase 2 — clarifications

**None asked.** `AskUserQuestion` is unavailable in this headless session, and the
session's own rules say to take the most conservative reading and log it. Every
ambiguity resolved this way is below.

### ASSUMPTIONS

1. **`length` floor.** The definition has no floor. `MIN_LENGTH = 83` is the
   SMALLER-scope reading: the shortest `length` whose scale ladder gives the break
   search more than one candidate, so the column cannot be constant by construction.
   The reference implementation accepts shorter windows and returns 1.0 for them (a
   number outside the quantity's range); this port refuses them and falls back to the
   default. Receipt §Q5, §H3.
2. **The GPL-3.0 reference is a BLACK BOX, nothing more.** The issue says to port
   from the definitions and never from the reference code. No line of pycatch22 was
   read; it is run in `docs/measure_c22_dfa.py` sections P and Q to MEASURE, which is
   the same use the owner's own screen prototype makes of it, and a test asserts no
   shipped module imports it. The three structural readings the definition leaves
   open are identified by fitting candidate pipelines to its OUTPUT.
3. **Gate E is not run here.** The session's rules forbid touching
   `../Backtesting`, so the receipt says "Gate E: pending, run by issue-solver after
   this session" and `tests/test_c22_dfa.py::test_the_gate_e_row_is_owed` asserts
   there is no ledger row. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
   fails locally until the launcher's run is recorded; that is expected and the
   indicator is NOT held out of `Category` to silence it.
4. **Gate C's real-data limb is owed** from the same run. Every number in the receipt
   is synthetic.
5. **Overlap against the fork's own columns is reported as NOT Gate E** (receipt §E).
   It is on synthetic frames with this fork's comparators, and it exists because
   issue #128 names #112 `tf_dfa_100` as a relative and that port shipped AFTER the
   2026-10-24 screen, so the screen's fork-overlap stage never saw it.
6. **No file outside the allowed list is touched**, and nothing under `docs/issues/`
   (gitignored, read-only here) is staged.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `c22-dfa` | main thread | one task; it needs main-context judgement (a black-box fit against a GPL-3.0 reference, and three readings that the first attempt got wrong) and it edits shared wiring files |

## Phase 4 — gate

A fresh Fletcher reviewer (`Explore`, read-only) per round, up to 4 rounds (round 1 +
3 re-runs, the user's standing rule, which overrides Mode B's 3-round cap). Verdicts
verbatim in `01-c22-dfa.md`.

## Phase 5 — write-back

`TODO.md` was removed from this repository in 2026-10-20 and the local issue tracker
under `docs/issues/` is gitignored, so there is no task file to write back to. The
GitHub issue is the launcher's to close.
