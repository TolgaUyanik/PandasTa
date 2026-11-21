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

`docs/measure_c22_rs_range.py`'s bare invocation (`python docs/measure_c22_rs_range.py`,
no arguments) runs only §A2's FSANITY section, which never imports `pycatch22` —
the same discipline `docs/measure_c22_ami2.py` and `docs/measure_c22_periodicity.py`
use. §A1 (TAU) and §A3 (SEARCH) call the GPL-3.0 oracle and are opt-in:
`python docs/measure_c22_rs_range.py TAU SEARCH`. Each opens with an
`importlib.util.find_spec("pycatch22")` check and prints ABSENT rather than
raising if the dev-only package is not installed.

## A. What the search pinned, and what it could not

### A1. The window-size (`tau`) grid — SIZE CONSTRAINED, not a unique derivation

Every value `pycatch22.SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1` returns,
across the 96 white-noise samples in the table below (12 per length, 8
lengths — the section also draws 24 more rs_range samples for the
sensitivity block that follows it, 120 total), is an exact rational
multiple of `1/D` for some integer `D` that depends only on the input
LENGTH `n`, not on its content (checked to 1e-6 against the nearest
integer numerator). Measured by sampling `D` via the smallest common
denominator of 12 white-noise trials per length,
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
100-return window margin as tightly as the catch22 name `..._50_1_...`
implies at first glance.

### A2. The fluctuation function `F(tau)` — SANITY-CHECKED, not pinned

`python docs/measure_c22_rs_range.py` (the bare, default invocation runs
FSANITY only — no `pycatch22` import). Three candidate `F(tau)`
definitions were built from the public literature — Peng et al. DFA-2 (order
2 polynomial detrend of the GLOBAL cumulative profile, by box), the classical
per-box R/S with `ddof=1` (box's own mean for the local cumulative sum,
box's own std, matching this repo's own `g191_165`,
`pandas_ta/statistics/g191_165.py:134`, as the divisor), and an undivided
box-range variant (box's own mean removed, no std division) — and all three
give the textbook ORDERING of a generalised Hurst/DFA exponent on synthetic
AR(1) series:

| series | DFA order 2 | classical R/S | range, order 0 |
|---|---|---|---|
| white noise (phi = 0) | 0.5570 | 0.6228 | 0.6254 |
| AR(1), phi = +0.9 (persistent) | 1.3842 | 0.9749 | 1.2352 |
| AR(1), phi = −0.9 (anti-persistent) | 0.1427 | 0.3344 | 0.3343 |

`persistent > white > anti-persistent` holds for every column — each `F(tau)`
is a reasonable generalised-Hurst estimator by itself. This is necessary but
not sufficient: it says the ingredients are sane, not that any one of them is
the ingredient catch22 uses. A fourth construction, the global DFA profile
with a per-box RANGE statistic instead of an RMS residual, is built for §A3
but reuses this section's validated profile rather than being separately
FSANITY-checked.

### A3. The breakpoint / proportion extraction — NOT FOUND

`python docs/measure_c22_rs_range.py SEARCH`. Four `F(tau)` candidates ×
five breakpoint-choice criteria × four minimum-segment sizes — 80
combinations, all implemented and run, not asserted — against 100
independent white-noise windows. The five criteria: a disconnected
two-piece OLS fit reporting the left segment's point fraction; the same
fit reporting the right segment's fraction; a CONTINUOUS
(connected-at-the-knot) two-piece fit; a CUSUM-of-residual changepoint
statistic from a single overall fit; and the proportion of points with a
positive residual from a single overall fit (no search at all). The four
`F(tau)`: the two from §A2 (range order 0, classical R/S), plus two added
after round 1 of review to close the family: the Peng et al. DFA-2
construction itself (`log_f_dfa`, global profile, RMS residual — the
textbook form §A2 built but round 1's SEARCH never ran against this
feature), and that same global profile with a per-box RANGE statistic in
place of the RMS residual (the most literal reading of "rsrangefit" inside
a fluctuation-analysis frame). Best row per (`F(tau)`, criterion) pair,
`min_side` giving the largest `|Pearson ρ|` (every row the harness prints is
in `docs/measure_c22_rs_range.py`'s own output; this table is not a cut):

| `F(tau)` | criterion | `min_side` | exact | Pearson ρ | Spearman ρ |
|---|---|---|---|---|---|
| range, order 0 | disconnected, left | 9 | 21/100 | 0.304 | 0.248 |
| range, order 0 | connected | 12 | 4/100 | **0.364** | 0.345 |
| range, order 0 | CUSUM | any | 12/100 | 0.219 | 0.186 |
| range, order 0 | positive-residual | any | 3/100 | 0.135 | 0.146 |
| classical R/S | disconnected, left | 12 | 8/100 | 0.196 | 0.163 |
| classical R/S | connected | 12 | 4/100 | 0.295 | 0.266 |
| classical R/S | CUSUM | any | 9/100 | 0.101 | 0.109 |
| classical R/S | positive-residual | any | 1/100 | −0.059 | 0.002 |
| DFA order2, RMS | disconnected, right | 2 | 0/100 | 0.135 | 0.150 |
| DFA order2, RMS | connected | 2 | 1/100 | −0.052 | −0.085 |
| DFA order2, RMS | CUSUM | any | 1/100 | −0.053 | −0.026 |
| DFA order2, RMS | positive-residual | any | 0/100 | 0.129 | 0.100 |
| DFA order2, range | disconnected, right | 5 | 0/100 | 0.058 | 0.055 |
| DFA order2, range | connected | 5 | 3/100 | −0.156 | −0.121 |
| DFA order2, range | CUSUM | any | 0/100 | −0.022 | −0.028 |
| DFA order2, range | positive-residual | any | 1/100 | 0.077 | 0.075 |

The disconnected-right orientation (reporting `(n − k) / n` instead of
`k / n`) is the mirror image of disconnected-left by construction — same
`|ρ|`, opposite sign — and is in the harness's full printed table but
collapsed into whichever sign has the larger value above. `Spearman ρ` is
midrank-based (tied values share the mean of their ranks), not
position-tie-broken: both the reference and every candidate here sit on a
coarse `1/35`-style lattice, so ties are frequent by construction. **Best
over all 80 combinations: Pearson ρ = 0.364** (range-order-0 F(tau),
connected fit, `min_side = 12`, 4/100 exact) — unchanged from round 1's
40-combination search: both DFA-family additions top out at `|ρ| ≤ 0.156`
(DFA order2/range, connected, `min_side = 5`), well below the range/R-S
ceiling.

A second run repeats the same five criteria against the DFA sibling
(`SC_FluctAnal_2_dfa_50_1_2_logi_prop_r1`), using `log_f_dfa` as `F(tau)`:
**best ρ = 0.178**. This is NOT an isolation of the breakpoint step from the
fluctuation function — §A2 only sanity-checked `log_f_dfa`'s persistence
ORDERING on synthetic AR(1) series, never shown it is the reference's own
`F(tau)`, so a low ρ here is consistent with "wrong `F(tau)`" and with
"wrong extraction" alike and cannot distinguish them. What the two runs
together show is narrower but still real: neither sibling clears Pearson
0.4 — rs_range under any of the 20 structural hypotheses tried (four
`F(tau)` × five criteria), the dfa sibling under any of the 5 (one `F(tau)`
× five criteria) — against `c22_periodicity`'s 2,798/2,802 (99.86%) once
ITS ambiguous convention was found. The gap is not a rounding or
convention question within this harness's hypothesis family — but it does
not rule out a fluctuation function or extraction outside it.

## B. What this means for Gates A–F

Gate A (correctness) cannot be cleared: no candidate among the 20
structural hypotheses tried in §A3 reproduces the named feature to a
confidence this repo's own bar requires ("every claim... must correspond
to a run" — a formula with ρ ≤ 0.364 at best, among the hypotheses this
harness's family covers, against its own name's reference is not a correct
port of that name, whatever else it computes). Gates B–E were not
attempted beyond the suite run in §D, because they gate a SPECIFIC module's
causality, reachability, scale-invariance and suite health, and there is
no module whose identity as `SC_FluctAnal_2_rsrangefit_50_1_logi_prop_r1`
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
receipt could not pin (§A3's second run used it for exactly that reason).
A future attempt at either feature should treat this harness's 20/5
hypothesis families as exhausted rather than re-running them: the
window-size grid (§A1) and the generalised-Hurst sanity of several `F(tau)`
candidates (§A2) are solid ground to build on, but the specific two-regime
"proportion" statistic needs the paper's or hctsa's actual text — this
receipt's negative result bounds only the hypothesis family it tried, not
every possible `F(tau)` or extraction, so it is a starting point, not a
proof that none exists.
