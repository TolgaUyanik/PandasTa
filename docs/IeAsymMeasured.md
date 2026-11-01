# Return Asymmetry (IE) — measured (`ie_asym`)

The empirical form of Jiang, Wu, Zhu and Chen's distribution-based return asymmetry
measure, as described in Quantpedia strategy #0664 ("Return Asymmetry Effect in Commodity
Futures") and the companion Quantpedia blog post citing Wu, Zhu and Chen (2020) on Chinese
stocks. Found by the ResearchIntel RAG scan of 2026-10-24, round 3 (issue #28). Over the
trailing `length` bar-to-bar log-returns: count how many sit more than `mult` sample
standard deviations above the window mean, subtract how many sit below it by the same
margin, divide by `length`. High = more extreme up days than down days ("lottery
preference"), which the sources associate with overpricing and lower subsequent returns.

**Status: Gates A, B, D cleared on this machine; Gate C on synthetic data only (real-data
counts owed to the launcher's run, same as Gate E). Do not merge to `main` before Gate E**:
`ie_asym` is in `Category`, so any `df.ta.strategy()` sweep in the parent repo picks it up.

Shipped: `pandas_ta/statistics/ie_asym.py`, one column `IEASYM_<length>_<mult>` (default
`IEASYM_260_2.0`). Tests: `tests/test_ie_asym.py` (14). Numbers:
`python docs/measure_ie_asym.py`. Environment: pandas 2.3.3, numpy (repo-pinned), Python
3.11. Measured 2026-11-01.

## Gate A decision: formula, not an alternative

The issue catalogues three alternative forms (Rachev ratio, upside/downside volatility
ratio, `ratio_beyond_r_sigma`) and says "pick one at Gate A." Read conservatively (no
clarification channel in this session; smaller-scope reading wins per the issue-solver
rules): the issue's own "What" section states `IE_n` as the ask, and the alternatives are
catalogued as fallbacks in case `IE_n` turns out unworkable (the issue's own risk note
about BIST's ±10% limit and tick rounding clipping the tails). `IE_n` is not unworkable on
this machine's synthetic data (Gate C below: 846-850 of 940 non-NaN bars nonzero, both with
and without tick rounding), so it ships as specified. No Pine or TA-Lib source exists for
this one — it is a published formula, not a chart script — so Gate A is checked against an
independent loop written from the formula and two hand-computed windows (same pattern as
`pfe`, `docs/PfeMeasured.md`), not a line citation.

Two choices the formula itself leaves open, decided here:

- **Returns are `log(close / close.shift(1))`**, not simple percent change, so the ratio
  inside the log is bit-identical under a power-of-two price rescaling (Gate D).
- **Standard deviation is the sample form (`ddof=1`)**, pandas's default. The source
  formula does not specify biased vs. unbiased and there is no oracle to check it against.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (self-consistency; no Pine/TA-Lib source exists for this formula) | hand-computed window (9 zero-returns + one +10 log-return, length=10, mult=2.0) reads exactly 0.1 (the lone bar beyond mean + 2·std); mirror case reads -0.1; matches an independent loop to 1e-9 on a 500-bar walk, length=20 |
| B Causality | pass, with a measured, understood exception | 20-offset future-perturbation sweep (spike bar `j` alone, x5 — see below): real module 0 leaks at all 20 offsets. Two look-ahead mutants (`net`/`returns`: read `close.shift(-1)`; `window`: shift the rolling input by one bar) are each proved live, then caught at **18 of 20**, not 20 of 20 — the other 2 are coincidences, not misses (next section) |
| C Reachability | synthetic only, real-data counts owed | 1,200-bar walk (seed 11, σ=0.02), length=260: 940 of 1,200 bars non-NaN; 850 nonzero (495 positive / 355 negative / 90 zero), 15 distinct values, range [-0.0231, +0.0308]. Same walk tick-rounded (0.05): 940 non-NaN, 846 nonzero (508 positive / 338 negative / 94 zero). **Real BIST counts owed** — the issue's own risk flag (±10% limit, tick rounding) is exactly what Gate C on real data must report |
| D Scale-free | pass | x8/x64 bit-identical (the log-ratio is exact under a power of two); x10/x3.7 max abs diff measured **0.0** (not just "small" — the floating-point rounding from rescaling a ~100-level price by 10 or 3.7 is around 1e-15, far below the gap between any realistic return and its window's own ±2σ threshold, so no window's tail membership flips); `0 < 846 fires < 940` on the tick-rounded walk; 15 distinct values rules out a constant column |
| E Attribution | **OWED** | `gate_e_overlap.py run --module pandas_ta.statistics.ie_asym`, run by the launcher after this session |
| F Suites | this repo only; parent repo not run (not on this machine) | `python -m pytest -q`: 3 failed / 3,843 passed / 83 skipped. All 3 failures pre-exist this port and are named in `CLAUDE.md`/the issue-solver rules: `test_pine_coverage_csv` (known break, `docs/pine/` untracked), `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout, not on this machine), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (no ledger row yet for `ie_asym` — expected until the launcher's Gate E run is recorded) |

## The coincidental mutant misses, explained

`IEASYM` is a tail **count**, not a continuous function of its input. A 1-bar lookahead
mutant can only ever disturb exactly one output row per offset `j` — row `j-1`, the only
window whose causally-correct content would stop at bar `j-1` but whose mutant content
reaches one bar further, into bar `j`. Spiking bar `j` alone (×5, about 80σ on this walk)
makes it that window's dominant element regardless of where it lands — mean shifts by
`value/length`, the window's own std is dominated by one huge squared term, and the
spike's own deviation from the new mean still exceeds the new threshold — so the mutant's
output at row `j-1` is deterministically exactly `+1/length` every time (measured: the
literal same float at all 20 offsets). The real module's own unperturbed value at that
same row occasionally **also** reads `+1/length`, on its own merits, from an unrelated
real extreme already present in that window (nothing to do with the spike). Two counts
landing on the same side of a 15-value, ±0.03-wide range by chance (`docs/`-measured
probability about 1/15 per trial here, matching 2 misses out of 20) reads as "no change"
even though the mutant genuinely read the future. Diagnosed directly: at `j-1 = 299` and
`j-1 = 749` on this walk, the real (unperturbed) module's own output already equals
`+1/260` before any mutant is involved. This is a property of the statistic's coarse,
discrete output space — the issue's own risk note ("the column moves in coarse steps of
1/n") — not a defect in the mutant or the test.

## To close

1. The launcher runs Gate E (`gate_e_overlap.py run --module pandas_ta.statistics.ie_asym`)
   and records the row (`python docs/gate_e_ledger.py record ...`).
2. A receipt session fills in the measured max |ρ|, its comparator, and the real-data Gate
   C tail-fire counts (the ±10%-limit / tick-rounding risk) above.
3. Apply CLAUDE.md's Gate E bands. STRUCK -> revert (delete the module, export, `Category`
   entry, accessor, tests, README/dictionary counts) and keep this file as the receipt —
   a measured revert closes issue #28 exactly as well as a ship.
4. Run both repos' suites.
