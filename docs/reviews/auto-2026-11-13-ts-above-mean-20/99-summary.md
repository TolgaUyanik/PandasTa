# 99 — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| TS-ABOVE-MEAN-20 (issue #97) | **PASS** | 4 (REVISE, REVISE, REVISE, PASS) | 5 new + 7 modified, listed in `00-manifest.md` | Gate E and Gate C's real-data counts, both run by the launcher; `ts_medskew_20` (issue #98) if it ships |

## What shipped

`TS_ABOVE_MEAN_20` — the share of a 20-return window's simple returns sitting
strictly above that window's own mean, tsfresh's `count_above_mean / n`.
Statistics category, `length` parameter defaulting to 20, dimensionless, on
the 19 values 1/20 … 19/20.

## What each round cost

Rounds 1–3 each found one defect of the SAME kind, each one layer deeper:

1. a claim in the shipped module that the run it cited contradicted;
2. a FIX for (1) that invented a new claim, backed by a mutant that was never
   built;
3. a FIX for (2) whose measurement was narrowed by a silent slice until it
   agreed with the sentence.

That is the repo's dominant defect — *a claim written before it was measured*
— reproducing itself inside its own corrections. The thing that broke the
chain was building the sixth mutant and printing the moved-bar INDEX LIST
instead of a count: a list cannot be quietly trimmed the way a zero can.
Round 4 found no wrong number.

## Open, and named

* **Gate E: pending, run by issue-solver after this session.** No ledger row;
  `tests/test_ts_above_mean_20.py::test_the_gate_e_row_is_still_owed` asserts
  there is none, which is the receipt session's cue.
* **Gate C on real data is OWED** — the pooled non-NaN / non-zero counts come
  out of the same launcher run. What exists now is the screen's real-frame
  pre-flight (`sanity.csv` line 72), quoted in receipt §3.
* **The redundancy to watch.** This column is a backwards skewness reading.
  Against the shipped `OSAP_RETSKEW_21` it measures −0.61 / −0.86 / −0.96 on
  three synthetic frames, and those are the ONLY measurement of that pair
  that exists — the screen's real-frame fork overlap predates
  `osap_retskew_21` by nine days, and Gate E's 687 comparators hold no
  pandas_ta port. The adverse real-frame number that does exist is pooled
  **0.8428** against the screen's unshipped `ts_medskew_20` candidate
  (issue #98). Receipt §5.
* **Pre-existing, not fixed here**: `pandas_ta/core.py:453` hands out the live
  `Category[name]` list and `core.py:692` removes names from it, so running
  `tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py` in
  one process fails the pinned `CATEGORY_TOTAL`. Alphabetical collection hides
  it; receipt §8 records it.
