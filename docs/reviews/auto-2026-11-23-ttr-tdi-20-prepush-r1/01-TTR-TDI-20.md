# TTR-TDI-20 (issue #148) — pre-push gate round 1

## Findings addressed (quoted from the invocation)

MAJOR: `tests/test_tdi.py:52-53`, `docs/MLCompanionContract.md` (#148 census clause),
`tests/test_altport2_ports.py:196` (`CATEGORY_TOTAL` rationale) all still said Gate E
was pending/owed for `tdi` while the same tree (commit a2989a7) already records it SHIP
in `docs/gate_e_ledger.csv` and `docs/TdiMeasured.md`.

MINOR: `tests/test_altport2_ports.py:196`'s inline formula gloss dropped a parenthesis
(`... |mom|) / close` instead of `(... |mom|)) / close`).

MINOR: `docs/TdiMeasured.md`'s Gate D row cited `python docs/measure_tdi.py D` for
"bit-identical on all eight frames", but that script section loops over `FIRING` (seven
frames, excludes `flat`).

NIT: `docs/reviews/auto-2026-11-23-ttr-tdi-20/01-TTR-TDI-20.md` and `99-summary.md`
describe Gate E as pending, stale next to the SHIP row at HEAD.

## Fixes applied

- `tests/test_tdi.py` item 5: replaced "Gate E is OWED. No ledger row is recorded
  here..." with the measured SHIP verdict (0.4924 vs `mad_pct_Pctl`, per-frame max
  median 0.4915, run `is148-tdi-c25dda7f`, measured 2026-11-23).
- `docs/MLCompanionContract.md`: #148 clause's "Gate E pending, run by issue-solver
  after this session" -> the same SHIP verdict.
- `tests/test_altport2_ports.py` `CATEGORY_TOTAL` comment: same SHIP verdict, plus the
  formula gloss parenthesis fixed to `(|sum_n mom| - (sum_2n |mom| - sum_n |mom|)) /
  close`.
- `docs/TdiMeasured.md` Gate D row: added a citation to
  `tests/test_tdi.py::test_scale_an_exact_binary_factor_is_bit_identical`
  (parametrized over all eight `NAMES`, including `flat`) alongside the `measure_tdi.py
  D` citation, which only covers the seven `FIRING` frames.
- `docs/reviews/auto-2026-11-23-ttr-tdi-20/01-TTR-TDI-20.md` and `99-summary.md`: each
  got a short closing note pointing at the launcher's Gate E run and noting the ledger
  test now passes.

## Verification

```
python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py tests/test_altport2_ports.py \
  tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py \
  tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```
Result: 1542 passed, 7 skipped — no failures (the ledger row now exists, so
`test_every_indicator_that_needs_a_row_has_one` passes).

## Review round 1 (this gate)

VERDICT: PASS

FINDINGS: none.

SUMMARY: All three MAJOR findings fixed and verified digit-for-digit against
`docs/gate_e_ledger.csv`; both MINORs fixed; both NITs applied. Targeted suite clean,
1542 passed / 7 skipped, zero failures. Gate clears first round.
