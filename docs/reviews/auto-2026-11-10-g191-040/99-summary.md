# Run summary — auto-2026-11-10-g191-040

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| g191-040 | **PASS** | 5 (REVISE ×4, PASS at round 5) | **added:** `pandas_ta/volume/g191_040.py`, `tests/test_g191_040.py`, `docs/measure_g191_040.py`, `docs/G191040Measured.md`, this run folder. **modified:** `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py` (`Category["volume"]`), `pandas_ta/core.py` (accessor), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 311→312, `CATEGORY_BUCKETS["volume"]` 40→41), `README.md` (312 / 320 / `volume (41)`), `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md` (656→657 / 299→300 `SF`) | Gate E owed: the launcher runs `gate_e_overlap.py run --module pandas_ta.volume.g191_040` after this session, and a receipt session records the `docs/gate_e_ledger.csv` row. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails until then — expected. Band to expect from the PROTOTYPE's own screen: DISCLOSE_GAP (max \|ρ\| 0.8268 vs `OBV_Slope_norm`), not a port number. |

## Final state, measured

- `python -m pytest tests/test_g191_040.py -q` → **25 passed**
- `python -m pytest -q` → **3 failed, 5155 passed, 83 skipped**; the three are
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the absent
  `../AlternativeRepos`), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  (owed for `g191_040` and the pre-existing `mtd_ret`) and
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (CLAUDE.md "Known breaks").
- `python docs/measure_g191_040.py` → every figure quoted in `docs/G191040Measured.md`.
- `python docs/gen_indicator_dictionary.py` → reproduces the committed dictionary.

## What the five rounds cost and bought

One real code defect found and fixed: `undefined` guarded only the PRIOR close, so a `NaN` at
`close[t]` (where `C > C1` and `C <= C1` are both `False`) had its volume silently dropped from
both buckets while the 26 windows containing it kept firing over 25 defined bars. Now
`close_prior.isna() | close.isna()`.

Everything else the rounds removed was a claim standing in front of its measurement or a test
standing in front of a mirror: a bar-0 "pin" that never called the indicator; a zero-denominator
trigger stated as one cause when it has two; "a real, reachable condition" with no run behind it;
"no column value changes" from two compared scalars; "and no other bar moves", which measurement
showed to be false (`max|diff| = 5.68e-14`, not bit-identical); and the same retracted sentence
surviving in whichever file had not been looked at that round — three times.

**Standing rule this run earned**, recorded in `docs/G191040Measured.md`'s Review history: a
retraction is not done when the sentence is gone from the file you were looking at. Grep all four
files (`pandas_ta/volume/g191_040.py`, `tests/test_g191_040.py`, `docs/measure_g191_040.py`,
`docs/G191040Measured.md`) for the struck phrase before calling it fixed. Applying that grep
after round 4 found one further live instance that no finding had named.

## Destructive / irreversible actions

None. No push, no deletion of tracked files, no deploy, nothing published externally. `git
restore --source=4bfa0df --worktree` was used to recover session 1's own uncommitted work from
its WIP commit, after checking that commit's base is this branch's `HEAD`.
