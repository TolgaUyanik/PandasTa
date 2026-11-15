# A158GAPS batch run — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| A158GAPS | PASS | 3 (REVISE, REVISE, PASS) | `pandas_ta/statistics/rank.py` (new), `pandas_ta/volatility/wvma.py` (new), `pandas_ta/volume/vsumd.py` (new), `tests/test_rank.py` (new), `tests/test_wvma.py` (new), `tests/test_vsumd.py` (new), `docs/Alpha158Measured.md` (new), `pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/statistics/__init__.py`, `pandas_ta/volatility/__init__.py`, `pandas_ta/volume/__init__.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` | Gate E (3 runs: `rank`, `wvma`, `vsumd`) owed to the launcher/receipt session; `docs/gate_e_ledger.csv` gets its three rows then; parent repo's suite run by the launcher |

**What round 1 caught:** `docs/Alpha158Measured.md`'s Gate C row asserted one blanket
warm-up rule for all three indicators that was mathematically wrong for two of them
(`wvma`/`vsumd` burn one extra bar on an internal shift/diff before their rolling
windows start) — the row's own quoted fire counts already contradicted its stated
rule. Also: two of three module docstrings were missing the Scale-free paragraph the
third had, and the Gate F row under-reported the pre-existing failure count by one.

**What round 2 caught:** the round-1 fix for Gate F quoted a `pytest -q` result that
had gone stale by the time of the re-review — a fourth, self-inflicted failure
appeared, caused by this very run's own review-log prose tripping an unrelated
repo-wide guard (`test_no_other_document_retypes_the_split`) that flags any five-or-
more numbers joined by slashes anywhere in the fork, regardless of context. The same
literal shape was present in all three production modules' `DEFAULT_LENGTHS`
comments, not just the log — fixed in all four files by switching to comma-separated
window lists.

**Round 3:** PASS, with one NIT (a traceability gap in this log's own narrative,
fixed anyway).

Gate E is explicitly out of scope for this session (launcher-run, per the system
prompt's override rules); `tests/test_gate_e_ledger.py::test_every_indicator_that_
needs_a_row_has_one` fails locally for `['rank', 'vsumd', 'wvma']` by design — that is
the expected "Gate E owed" state, not a defect.

No task-file write-back performed: `docs/issues/` is a read-only, gitignored copy of
the owner's local tracker, outside this session's allowed-modify scope; the GitHub
issue is the source of truth and is updated by the launcher's PR, not this session.
