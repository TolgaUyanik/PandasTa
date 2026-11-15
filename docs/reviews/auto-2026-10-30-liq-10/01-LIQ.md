# LIQ — liquidity trio from OHLCV

GitHub issue #10 (`docs/issues/012-LIQUIDITY.md`, migrated from the owner's local
tracker). Verbatim text and the session's own overriding rules are in the launcher's
system prompt; not re-quoted here. Clarifications/assumptions are in `00-manifest.md`.

## Execution log

- Read `pandas_ta/volatility/har_park.py`, `pandas_ta/volume/maxvol_adv.py`,
  `tests/test_pfe.py`/`test_har_park.py`, `CLAUDE.md`'s porting protocol, and the
  Gate E ledger guard (`tests/test_gate_e_ledger.py`) to confirm the shape a port
  takes in this repo and what CI actually checks instead of Gate E.
- Wrote `pandas_ta/volatility/corwin_schultz.py` (AFML 19.1 / Corwin & Schultz
  2012), `pandas_ta/volatility/roll_spread.py` (Roll 1984), `pandas_ta/volume/amihud.py`
  (Amihud 2002) — three modules, per the ASSUMPTION in `00-manifest.md`.
- Wired all five touch points: category `__init__.py` exports, `pandas_ta/__init__.py`
  `Category` entries, `pandas_ta/core.py` accessors, and one test module each.
- Wrote `docs/measure_liq_proxy.py` and ran it (`python docs/measure_liq_proxy.py`) to
  produce every Gate C/D number and the proxy-overlap figures, rather than typing
  any of them.
- Wrote `tests/test_corwin_schultz.py` (13), `tests/test_roll_spread.py` (11),
  `tests/test_amihud.py` (13): hand-derived closed-form correctness checks (not
  re-running the module's own formula), an independent per-bar loop, a
  future-perturbation causality sweep (31 offsets) plus one `importlib`-read,
  `exec`'d-in-memory look-ahead mutant per module, ×8/×64 bit-identical and
  ×10/×3.7 tolerance scale checks, Gate C fire/NaN/clip counts pinned to the
  measured numbers, and wiring checks.
- Found, mid-run, that the CS and ROLL mutants structurally cannot reach 31/31 on
  the future-perturbation sweep (each has a one-bar reach, and the affected bar is
  sometimes masked by CS's clip-to-zero or ROLL's NaN-vs-NaN) — measured the actual
  catch rate (CS 9/31, ROLL 18/31) and pinned that number with the reason, rather
  than engineering a bigger, less-realistic mutant to force 31/31 or silently
  weakening the assertion. Same pattern `tests/test_altport2_ports.py` already
  documents for `smc_sweep`.
- Updated `tests/test_altport2_ports.py`'s pinned `CATEGORY_TOTAL`/`CATEGORY_BUCKETS`
  (237→240, volatility 20→22, volume 24→25), `README.md`'s category headline and
  the `volatility`/`volume` rows, and regenerated `docs/IndicatorDictionary.md`
  (`python docs/gen_indicator_dictionary.py`), then updated
  `docs/MLCompanionContract.md`'s measured tag counts (570→573 tagged, 216→219
  `SF`) to match — all three guarded by tests that parse the live package/README/
  dictionary rather than trusting typed numbers.
- Wrote `docs/LiquidityMeasured.md` with the Gates A-D numbers, the four decisions
  the issue asked to be made explicit (with reasons), the proxy overlap (labelled
  NOT Gate E), and Gate E marked PENDING per the session's override rule.
- Ran `python -m pytest -q` (full suite): **3 failed / 3,297 passed / 83 skipped**.
  The three failures: `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  naming exactly the three new indicators (expected — Gate E is owed, matches the
  `pfe`/`kalman_trend`/`range_compress_run`/`maxvol_adv` precedent before their
  ledger rows existed); `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, both
  pre-existing and unrelated (documented in `CLAUDE.md`'s "Known breaks" /
  deselected by name in CI).

## Review round 1

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: tests/test_corwin_schultz.py:103-111 (test_malformed_bar_is_nan_not_an_exception)
    problem:  The test pins that the malformed bar (index 1) and its direct neighbour (index 2, whose gamma needs both bars valid) read NaN, but never asserts that index 3 recovers to a finite value. I hand-derived it myself (beta[3]=hl2[2]+hl2[3], both valid; valid2[3]=True) — the module is correct — but the test doesn't prove that, it only proves the mask doesn't stay silent.
    fix:      Add `assert pd.notna(out.iloc[3])` (or go further and assert the exact derived value) so a future change that widens the NaN mask past where the math actually requires it gets caught here instead of being someone's surprise six months from now.
SUMMARY: I ran the proxy script, ran the full suite, regenerated the dictionary, hand-derived all three closed-form test values independently, and traced every one of the four explicit decisions from module docstring through to docs/LiquidityMeasured.md. Every number in that document — fire counts, clip rates, scale-tolerance max|diff|, proxy rho's, the pytest 3/3297/83 split, the exact ['amihud', 'corwin_schultz', 'roll_spread'] Gate-E-owed failure — matched the live script and live suite output to the decimal. The Gate B mutants are real look-ahead bugs with a genuinely bounded reach, not strawmen, and the sub-100% catch rates are measured and explained, not asserted around — same discipline this repo already demanded of itself for smc_sweep. Amihud's scale-free claim is checked on both the price axis and the volume axis independently, which is exactly what the issue flagged as the risk. All five wiring touch points land correctly and alphabetically; scope is exactly the allowed files plus exactly three new modules; Gate E and Gate F are stated honestly as pending/deferred, not faked. I found one thing worth a sentence, and it is a missing assertion, not a bug. That was acceptable. Barely.
```

### Fixes applied
- NIT (test_malformed_bar_is_nan_not_an_exception): added
  `assert pd.notna(out.iloc[3])` so the NaN mask's exact boundary is pinned, not
  just its onset. Re-ran `tests/test_corwin_schultz.py`: 13 passed. PASS verdict
  carried no CRITICAL/MAJOR, so no re-review round was required (Mode C step 10);
  the NIT was fixed anyway because it was free.

## Outcome
PASS (round 1)

