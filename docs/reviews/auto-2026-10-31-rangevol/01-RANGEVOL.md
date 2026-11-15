# RANGEVOL — port Garman-Klass / Rogers-Satchell / Yang-Zhang range volatility

Task text (verbatim, from the issue-solver invocation): "RANGEVOL: port the indicator of
issue #17 through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the issue
and the rules in your system prompt (the OHLC volatility estimators that are more efficient
than close-to-close.). Gate E and the suites are run by the launcher afterwards."

Issue #17 text (owner-written, verbatim) is in the system prompt; local tracker copy
`docs/issues/019-RANGE-VOL.md`. Pre-registered expectation: revert, guessing max |rho| >= 0.9
against `natr`/`har_park`.

## Execution log

- Read CLAUDE.md's porting protocol and gate table, and the merged `corwin_schultz` /
  `roll_spread` / `amihud` (Liquidity trio, issue #10) and `kalman_trend` ports as shape
  references -- the Liquidity trio because it is the closest precedent (three independent
  research-paper estimators, "one indicator, one module" split, Gate E deferred-to-later
  pattern), `kalman_trend` because its Gate E DEFERRED status is the precedent for shipping
  with Gate E pending rather than reverting pre-emptively.
- ASSUMPTION: issue #14's "open-quality check" is GitHub issue #14 (`docs/issues/016-OVERNIGHT.md`
  in the local tracker, still backlog), not local tracker file `014-MAX-LOTTERY.md`. Found by
  reading `016-OVERNIGHT.md`'s own "On GitHub: #14" header. Its own text: "Quantpedia's
  warning is that the open in free OHLC data is often wrong. Measure how trustworthy the
  yfinance BIST open is (e.g. how often open == prior close) before building." Read as:
  disclose this risk and measure it on synthetic data for `yang_zhang` (the one of the three
  that reads `open`); real BIST open quality is out of reach in this session (no Backtesting
  repo access) and is left as an owed item, same as #14 itself.
- Designed three self-contained modules (CLAUDE.md "one indicator, one module", matching the
  Liquidity trio's reasoning): `garman_klass.py`, `rogers_satchell.py`, `yang_zhang.py`, all in
  `volatility` next to `har_park`. Used exactly the session's 3-new-indicator-file allowance.
- Derived the per-bar non-negativity proofs for Garman-Klass and Rogers-Satchell algebraically
  (given `high >= max(open, close)` and `low <= min(open, close)`), so the `clip(lower=0.0)`
  before each `sqrt` could be documented as float-safety only, then measured that it never
  actually engages on the synthetic fixture (`docs/measure_rangevol.py`, clip-engagement
  section: per-bar term minimum 7.01e-08 / 0.0, zero negative bars either).
- Implemented all three modules, wired them (volatility `__init__.py`, `Category` in
  `pandas_ta/__init__.py`, three accessors in `core.py`).
- Wrote `tests/test_garman_klass.py` (13), `tests/test_rogers_satchell.py` (13),
  `tests/test_yang_zhang.py` (15): hand-derived correctness cases, an independent per-bar-loop
  check, future-perturbation causality sweeps (31/31/30 offsets) with one `importlib`-read
  `exec`'d-in-memory look-ahead mutant per module, scale-free x8/x64 (bit-identical) and
  x10/x3.7 (tolerance) checks, a malformed-bar NaN-and-recovery check, an open-quality
  disclosure test for `yang_zhang`, and wiring/accessor tests. All pass.
- Ran every test file individually first, then the full suite, to get real (not guessed)
  mutant-catch counts before writing them into the docstring numbers and the Measured.md file
  (first ran with `assert caught > 0`, measured the actual counts via
  `docs/measure_rangevol.py`'s mutant-catch section, then pinned the exact counts in both the
  tests and the doc).
- Updated `README.md` (headline 248->251, accessor count 256->259, volatility category list
  23->26), regenerated `docs/IndicatorDictionary.md`
  (`python docs/gen_indicator_dictionary.py` -- talib is present in this venv, so no
  cdl_pattern stripping / hand-patch was needed, unlike several prior ports), updated
  `docs/MLCompanionContract.md`'s running tagged-column-count narrative (581->584 / 227->230
  `SF`), and `tests/test_altport2_ports.py`'s pinned `CATEGORY_TOTAL`/`CATEGORY_BUCKETS`
  (248->251, volatility 23->26) -- all four are in the session's allowed-files list and all
  four had a test that would otherwise fail (`test_readme_counts.py`,
  `test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`,
  `test_altport2_ports.py::test_the_category_count_moved_by_exactly_three`).
- Did NOT touch `docs/gate_e_ledger.csv`, CLAUDE.md, or `docs/issues/` -- out of this
  session's allowed-files list / explicitly read-only, per the overriding rules.
- Wrote `docs/measure_rangevol.py` and `docs/RangeVolMeasured.md`: every number in the
  Measured.md file is copied from this script's printed output (Gate C/D numbers, the
  clip-engagement check, the open-quality disclosure table, the mutant catch counts, the
  proxy overlap against `natr`/`har_park`/`true_range`/`rvi`, and the three new columns'
  mutual correlation with each other). The Gate E section states "pending, run by
  issue-solver after this session" per the overriding instructions, and the file explicitly
  does NOT make the ship/revert call -- that is the receipt session's job once Gate E's real
  numbers exist.
- Ran the full suite twice (before and after the README/contract/category-count fixes):
  final state is 3 failed / 3,544 passed / 83 skipped -- the two pre-existing CLAUDE.md known
  breaks plus `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which is
  the expected failure per the overriding instructions (no ledger row until Gate E runs).

## Review round 1

VERDICT: PASS

FINDINGS:
  - severity: MINOR
    location: pandas_ta/volatility/garman_klass.py:9-12 (`_valid_ohlc` docstring)
    problem:  The helper's own non-negativity blurb claims "`high/low >= |close/open|` always holds, which is what keeps the per-bar term below non-negative." That inequality is true but vacuous — it falls straight out of `H>=C` and `L<=O` alone and holds regardless of which of `O`/`C` is larger — while the actual proof needs `ln(H/L) >= |ln(C/O)|`, i.e. `H/L >= max(C/O, O/C)`, which is the real max/min-of-logs argument correctly written out two lines later in the module docstring (lines 29-31). The helper's comment name-drops "see module docstring" to paper over the gap instead of just stating the real bound, so the one load-bearing piece of algebra in this file is duplicated badly in the one place a reviewer is most likely to stop reading.
    fix:      Either delete the redundant claim from `_valid_ohlc`'s docstring and point readers straight at the module docstring's derivation, or restate it correctly there: `ln(high/low) >= |ln(close/open)|` (equivalently `high/low >= max(close/open, open/close)`), not the flat ratio form currently written.
SUMMARY: I went looking for the thing this repo always gets wrong — a round number nobody measured — and every single figure in `docs/RangeVolMeasured.md` traced back bit-for-bit to `docs/measure_rangevol.py`'s actual stdout (I ran it) and to the three test files' own collected counts (I collected them). The Gate B mutants are genuine look-aheads caught at 31/31, 31/31, 30/30 because the code earns it, not because the assertion was loosened to fit. The non-negativity algebra for Garman-Klass and Rogers-Satchell checks out by hand. Scale-freedom is real, not asserted. Wiring hits all five touch points for all three indicators, the file allowlist was respected to the letter, and the full suite reproduces the exact "3 failed / 3,544 passed / 83 skipped" claimed in the doc, with the three failures being exactly the pre-registered known breaks. The one thing I'll dock you for is a docstring sloppily restating its own proof's weaker cousin right next to the correct one — fix it before someone trusts the wrong sentence. That was acceptable. Barely.

### Fixes applied
- MINOR (`_valid_ohlc` docstring, `garman_klass.py`): restated the inequality correctly
  as `ln(high/low) >= |ln(close/open)|` (equivalently `high/low >= max(close/open,
  open/close)`), instead of the vacuous `high/low >= |close/open|`. Re-ran
  `tests/test_garman_klass.py` (13 passed) to confirm the docstring-only edit didn't
  touch behavior.

## Outcome
PASS (round 1)
