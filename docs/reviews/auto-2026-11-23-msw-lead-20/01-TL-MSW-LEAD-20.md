# TL-MSW-LEAD-20

## Implementation summary

Ported issue #145 (MESA lead sine, fixed-period DFT form, length 20) as `pandas_ta/cycles/msw_lead.py`
/ `msw_lead` / column `MSW_LEAD_<length>` (default `MSW_LEAD_20`). Gate A written from John
Ehlers' published MESA Sine Wave / Lead Sine pseudocode (Stocks & Commodities, Apr 1996; Rocket
Science for Traders, Wiley 2001, ch. 11), not from Tulip's `msw.c` and not copied from the
issue's prototype (`docs/issues/screen/ind_screen_r4.py`'s `_msw_phase`) — independently
re-derived, differing from the prototype's degenerate-branch form (`pi*sign(ip)`) in favor of the
published pseudocode's `90*Sign(ImagPart)` (`(pi/2)*sign(imag)` in radians). Scale-free guard
(`0.001 * close` instead of Ehlers' raw-price-unit `0.001`) per the issue's explicit instruction.

Wired at all five touch points: module, `pandas_ta/cycles/__init__.py` export, `Category["cycles"]`,
`core.py` accessor, `tests/test_msw_lead.py`. Added `docs/measure_msw_lead_proxy.py` (every number
quoted in the receipt and test docstring) and `docs/measure_msw_lead_cpu.py` (CPU-kernel check per
the session rules). Updated README.md (cycles 9->10, Category 377->378, callable 385->386),
regenerated `docs/IndicatorDictionary.md`, bumped `docs/MLCompanionContract.md`'s SF tag count
(722->723 total, 356->357 SF) with a changelog entry, and bumped `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` (377->378) with a changelog entry.

Gates A-D cleared (see `docs/MswLeadMeasured.md` for the full table and measured numbers). Gate E
left as `pending, run by issue-solver after this session` per the overriding session rules; no row
added to `docs/gate_e_ledger.csv`.

## Verification

`python -m pytest -q tests/test_msw_lead.py tests/test_readme_counts.py tests/test_altport2_ports.py
tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py
tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
-> 1,414 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
expected per the session rules).

`python docs/measure_msw_lead_cpu.py disable pytest` (NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX
AVX2 FMA3", this machine's own CPU features) -> 12 of 12 `test_msw_lead.py` tests pass.

## Assumptions logged

- Column/module name `msw_lead` / `MSW_LEAD_<length>`, not the catalog candidate id's `tl_` prefix
  (`tl_msw_lead_20`) — no shipped Tulip-attributed indicator in this repo uses that prefix
  (checked `decay.py`); conservative reading of an unspecified naming choice.

## Review round 1

```
VERDICT: PASS
FINDINGS:
SUMMARY: Every number this session wrote down, I checked against the machine, and for once the
machine agreed with the paper -- the independent-loop max|diff| (3.28e-14), the x8/x64
bit-identical and x10/x3.7 tolerances (1.52e-14/2.30e-14), the 576/605 sign split, the proxy
rhos, and the "12 of 12" CPU-kernel claim all reproduce exactly from
docs/measure_msw_lead_proxy.py and docs/measure_msw_lead_cpu.py. The formula is a faithful,
correctly-ordered port of Ehlers' published MESA Sine Wave (quadrant +pi/2, +pi if real<0,
mod-wrapped), and it is visibly NOT a copy of the ind_screen_r4.py prototype -- the prototype's
degenerate-branch angle is pi*sign(ip), the module's is (pi/2)*sign(imag), matching the cited
published pseudocode's 90*Sign(ImagPart) instead of Tulip's C quirk, which is exactly what Gate
A's independent-derivation rule demanded. The k-indexing comment is self-consistent with the
rolling-window orientation, the rejected imag_lookahead mutant's "sin(0)=0 at the window's newest
position" reasoning checks out against the k[::-1] construction, and both live mutants
(real_lookahead, write_shift) are genuinely caught 31/31 after being proven live. All five wiring
touch points are present and consistent, naming (msw_lead, no tl_ prefix) follows the decay.py
Tulip-attribution precedent, every touched file is inside the allowed scope, and
docs/gate_e_ledger.csv was correctly left untouched. The pytest run shows exactly the one
expected ledger failure and nothing else. That was acceptable. Barely.
```

**Status: PASS, round 1. Done.**
