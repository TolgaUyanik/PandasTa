# Mode C run manifest — osap_retskew_21 (issue #36)

**Task (as given, free-form, single item):**
> OSAP-RETSKEW-21: port the indicator of issue #36 through Gates A-D, the wiring, the tests
> and docs/<Name>Measured.md, per the issue and the rules in your system prompt (skewness of
> daily returns (21). Source: Open Source Asset Pricing SignalDoc (Chen & Zimmermann; US
> monthly cross-section); GTJA191 #166 is the same statistic over 20 —
> `ReturnSkew (Bali-Engle-Murray 2). Gate E and the suites are run by the launcher afterwards.

**Clarification (Phase 2):** AskUserQuestion is unavailable in this session (headless
issue-solver run). Ambiguities resolved by the most conservative reading and logged as
ASSUMPTIONs instead of asked:

1. **Window length.** Issue title and prototype both fix it at 21 trading days. ASSUMPTION:
   ship `length=21` as the default, overridable like every other fixed-named port in this
   repo (`tf_centroid_20`, `median_ad_hl2`), not hard-coded to 21 only.
2. **Primary source access.** The paper (Bali-Engle-Murray 2016) and OSAP's own SignalDoc PDF
   are not in this worktree (`docs/pine/` and web access unavailable). ASSUMPTION: port from
   the statistic's universal textbook definition (Fisher-Pearson bias-corrected sample
   skewness — the same formula this repo's own `statistics.skew` already ships for price),
   which is explicitly NOT OSAP's GPL-2.0 code and satisfies the issue's "port from the
   paper's definition, never from that code" instruction without needing the PDF, since the
   statistic itself is common-knowledge mathematics. Disclosed in the module docstring and
   `docs/OsapRetskew21Measured.md`, not silently assumed.
3. **Gate E / Gate F scope.** Per this session's overriding rules: Gate E is not run here
   (launcher's job, after this session); Gate F is this repo's own `pytest -q` only (parent
   repo + ledger record are the launcher's and a later receipt session's jobs).

**Execution map:** one task, main thread (no parallel lane needed — single indicator,
sequential wiring).

**File scope (all within the issue-solver's allowed-to-change list):**
- `pandas_ta/statistics/osap_retskew_21.py` (new — the 1 new `pandas_ta/<category>` module)
- `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py` (wiring)
- `tests/test_osap_retskew_21.py` (new)
- `tests/test_altport2_ports.py` (CATEGORY_TOTAL 268 -> 269)
- `docs/OsapRetskew21Measured.md`, `docs/measure_osap_retskew_21.py` (new)
- `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`, `README.md`
  (counts: 268->269 Category, 276->277 accessors, statistics 21->22, SF tag count 259->260)
