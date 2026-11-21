# `c22_rs_range` — measured, and reverted

PandasTa issue **#129** (C22-RS-RANGE). Branch `issue-129-c22-rs-range`.
**No module was shipped.** This is the receipt for a MEASURED REVERT, kept
per the issue's own closing rule: "measured and reverted with that file kept
as the receipt... closes this exactly as well as a ship."

| | |
|---|---|
| candidate | `c22_rs_range`, catch22 feature `SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1` |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821); reference code pycatch22 1.0.2, **GPL-3.0** — to be ported from the definitions, never from that code |
| outcome | **REVERTED** — no `pandas_ta/statistics/c22_rs_range.py`, no wiring, no test module |
| harness | `docs/measure_c22_rs_range.py` (sections TAU, FSANITY, SEARCH) |

## 0. Why this is a revert and not a port

Gate A asks for correctness "against the source" — here, the paper's and
hctsa's definitions, since the reference implementation is GPL-3.0 and may
only be used to MEASURE (the issue's own words, repeated from the owner's
screen prototype docstring). Neither the Lubba et al. 2019 paper text nor
hctsa's own source is available in this worktree or on the web (both
`docs/pine/` and web access are unavailable per the issue-solver rules), so
the only thing nameable from first principles is the GENERAL FAMILY the
feature belongs to: a generalised Hurst / rescaled-range fluctuation
analysis, computing a fluctuation function `F(tau)` over a ladder of window
sizes and relating `log F(tau)` to `log tau`. That family is well-established
public statistics (Hurst 1951; Mandelbrot & Wallis 1969; Peng et al. 1994's
`q`-order generalisation) and this repo already ships one instance of it —
`g191_165`, the plain single-scale R/S statistic (`docs/issues/` issue #55)
— and a different one, `tf_dfa_100` (TSFEL's DFA-1, PandasTa #112).

What is NOT derivable from first principles is the specific scalar catch22
extracts from that family under the name `prop_r1` — a "proportion", given
the issue's own human-readable gloss ("rescaled-range fluctuation **scaling
break**"), of SOMETHING related to a two-regime fit. §A below is the
measured search for that specific quantity, using `pycatch22` (installed in
this worktree, GPL-3.0) strictly as a BLACK-BOX NUMERIC ORACLE — called on
constructed inputs and never read, same discipline `docs/C22PeriodicityMeasured.md`
§P used to disambiguate load-bearing choices the sources left open. The
difference from that precedent is the outcome: there, the paper's own
operation name (`PD_PeriodicityWang`) and a hand-held description ("spap2(2,
4, ...)" and `acf(i) = mean(...)`) pinned the algorithm up to a handful of
genuinely ambiguous conventions, each resolved to 2,798/2,802 agreement.
Here, nothing pins the breakpoint/proportion step at all, and the measured
search below tops out at a Pearson ρ of 0.364 against the reference — a
qualitative gap, not a last-bit or convention question.

## A. What the search pinned, and what it could not

### A1. The window-size (`tau`) grid — SIZE CONSTRAINED, not a unique derivation

Every value `pycatch22.SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1` returns,
across the 96 white-noise samples probed (12 per length, 8 lengths), is an
exact rational multiple of `1/D` for some integer `D` that depends only on
the input LENGTH `n`, not on its content (checked to 1e-6 against the
nearest integer numerator). Measured by sampling `D` via the smallest
common denominator of 12 white-noise trials per length,
`python docs/measure_c22_rs_range.py TAU`:

| `n` | observed `D` | `\|{unique(round(logspace(5, n//2, 50)))}\|` | match |
|---|---|---|---|
| 100 | 35 | 35 | yes |
| 90 | 34 | 34 | yes |
| 80 | 32 | 32 | yes |
| 70 | 29 | 29 | yes |
| 60 | 26 | 26 | yes |
| 50 | 21 | 21 | yes |
| 45 | 18 | 18 | yes |
| 40 | 2 (degenerate) | 16 | no — below the method's effective minimum length |

**Seven consecutive lengths match the CARDINALITY** of 50 candidate window
sizes, log-spaced between `tau_min = 5` and `tau_max = n // 2`, rounded to
the nearest integer and de-duplicated. That constrains the grid's SIZE, and
is as far as the evidence goes — it does not prove this exact formula is the
unique one producing that size at every length, only that it is consistent
with one. A sensitivity check (same section) varies `tau_min` by ±1 at
`n = 100` and `n = 70`: at `n = 100`, `tau_min = 4` gives the same count (35)
as `tau_min = 5` — both consistent with the observed denominator — while
`tau_min = 6` gives 36 and is ruled out; at `n = 70` all three of `tau_min`
4, 5 and 6 give 29 and are equally consistent. So `tau_min = 5` is A
reading that fits every length tried, not THE reading the evidence singles
out — an alternative `tau_min` in `{4, 5}` (or, at some lengths, `{4, 5, 6}`)
cannot be excluded by a cardinality match alone. The sibling feature
`SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1` matches the analogous rule with
`tau_max = n // 4` at `n = 100` (`D = 21`) and `n = 90` (`D = 18`), consistent
with a detrending order of 2 needing more points per box and so a smaller
maximum box fraction than the un-detrended range statistic. Both degrade to
a degenerate constant denominator below their respective minimum lengths
(rs_range's needs ≈ 45, dfa's ≈ 90) — the method is not defined on a
100-return window margin as tightly as the catch22 name `..._50_1_..."`
implies at first glance.

### A2. The fluctuation function `F(tau)` — SANITY-CHECKED, not pinned

`python docs/measure_c22_rs_range.py FSANITY`. Three candidate `F(tau)`
definitions were built from the public literature — Peng et al. DFA-2 (order
2 polynomial detrend of the GLOBAL cumulative profile, by box), the classical
per-box R/S this repo's own `g191_165` computes (box's own mean for the
local cumulative sum, box's own std as the divisor), and an undivided
box-range variant (box's own mean removed, no std division) — and all three
give the textbook ORDERING of a generalised Hurst/DFA exponent on synthetic
AR(1) series:

| series | DFA order 2 | classical R/S | range, order 0 |
|---|---|---|---|
| white noise (phi = 0) | 0.5570 | 0.5865 | 0.6254 |
| AR(1), phi = +0.9 (persistent) | 1.3842 | 0.9386 | 1.2352 |
| AR(1), phi = −0.9 (anti-persistent) | 0.1427 | 0.2981 | 0.3343 |

`persistent > white > anti-persistent` holds for every column — each `F(tau)`
is a reasonable generalised-Hurst estimator by itself. This is necessary but
not sufficient: it says the ingredients are sane, not that any one of them is
the ingredient catch22 uses.

### A3. The breakpoint / proportion extraction — NOT FOUND

`python docs/measure_c22_rs_range.py SEARCH`. Two `F(tau)` candidates ×
five breakpoint-choice criteria × four minimum-segment sizes — 40
combinations, all implemented and run, not asserted — against 100
independent white-noise windows. The five criteria: a disconnected
two-piece OLS fit reporting the left segment's point fraction; the same
fit reporting the right segment's fraction; a CONTINUOUS
(connected-at-the-knot) two-piece fit; a CUSUM-of-residual changepoint
statistic from a single overall fit; and the proportion of points with a
positive residual from a single overall fit (no search at all). Best four
rows per criterion family (every row the harness prints is in
`docs/measure_c22_rs_range.py`'s own output; this table is not a cut):

| `F(tau)` | criterion | `min_side` | exact | Pearson ρ | Spearman ρ |
|---|---|---|---|---|---|
| range, order 0 | disconnected, left | 9 | 21/100 | 0.304 | 0.254 |
| range, order 0 | connected | 12 | 4/100 | **0.364** | 0.325 |
| range, order 0 | CUSUM | any | 12/100 | 0.219 | 0.179 |
| range, order 0 | positive-residual | any | 3/100 | 0.135 | 0.125 |
| classical R/S | disconnected, left | 9 | 22/100 | 0.221 | 0.229 |
| classical R/S | connected | 9 | 13/100 | 0.278 | 0.217 |
| classical R/S | CUSUM | any | 9/100 | 0.166 | 0.155 |
| classical R/S | positive-residual | any | 1/100 | −0.102 | −0.006 |

The disconnected-right orientation (reporting `(n − k) / n` instead of
`k / n`) is the mirror image by construction — same `|ρ|`, opposite sign —
and is in the harness's full printed table but not repeated here. **Best
over all 40 combinations: Pearson ρ = 0.364** (range-order-0 F(tau),
connected fit, `min_side = 12`, 4/100 exact).

An isolation run repeats the same five criteria against the DFA sibling
(`SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1`), using `log_f_dfa` — the Peng et
al. DFA-2 fluctuation function §A2 already validated as a sane generalised
Hurst estimator — to separate whether the ceiling comes from the
fluctuation function or the breakpoint logic: **best ρ = 0.178**, lower
than rs_range's 0.364 even with a TRUSTED `F(tau)`. Neither sibling clears
0.4, against `c22_periodicity`'s 2,798/2,802 (99.86%) once ITS ambiguous
convention was found. **The gap here is not a rounding or convention
question — it is evidence that none of the ten structural hypotheses tried
(two `F(tau)` × five criteria) is the mechanism `prop_r1` actually
measures, for either feature.**

## B. What this means for Gates A–F

Gate A (correctness) cannot be cleared: there is no candidate formula that
reproduces the named feature to a confidence this repo's own bar requires
("every claim... must correspond to a run" — a formula with ρ ≤ 0.364 at
best against its own name's reference is not a correct port of that name,
whatever else it computes). Gates B–F were not attempted, because they gate
a SPECIFIC
module's causality, reachability, scale-invariance and suite health, and
there is no module whose identity as `SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1`
is established.

**Gate E does not apply to this issue.** It measures a shipped `Category`
column's overlap against the engine's comparators; there is no column here
for the launcher to run it against. (This differs from a shipped port's
receipt, where this section would instead say "Gate E: pending, run by
issue-solver after this session" — that sentence does not belong here
because there is nothing pending to run.)
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is unaffected: `c22_rs_range` was never added to `Category`, so it never
needed a row.

## C. What is NOT in this tree

- `pandas_ta/statistics/c22_rs_range.py` — not written.
- No `Category` entry, no `core.py` accessor, no package export.
- `tests/test_c22_rs_range.py` — not written.
- `docs/gate_e_ledger.csv` — unchanged.
- The three counts `tests/test_readme_counts.py` checks, `CATEGORY_TOTAL` in
  `tests/test_altport2_ports.py`, and `docs/MLCompanionContract.md`'s tagged
  counts — all unchanged, because nothing was added to count.

## D. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **1282 passed, 7 skipped** |

No port test module exists to run, by construction (§C). Both repos' whole
suites: run by issue-solver in clean worktrees (see the PR body).

## E. Related open work

`docs/issues/screen/candidates_r3.csv` lists `c22_dfa` (`SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1`)
as a separate candidate, sharing the same `prop_r1` extraction mechanism this
receipt could not pin (§A3's isolation test used it for exactly that reason).
A future attempt at either feature should start from §A3's negative result
rather than re-running the same search: the window-size grid (§A1) and the
generalised-Hurst sanity of several `F(tau)` candidates (§A2) are solid
ground to build on, but the specific two-regime "proportion" statistic
needs the paper's or hctsa's actual text, not further black-box search
against this harness's hypothesis family.
