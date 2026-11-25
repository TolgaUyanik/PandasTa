# `c22_transition_variance` — measured, and reverted

PandasTa issue **#130** (C22-TRANSITION-VARIANCE). Branch
`issue-130-c22-transition-variance`. **No module was shipped.** This is the
receipt for a MEASURED REVERT, kept per the issue's own closing rule:
"measured and reverted with that file kept as the receipt... closes this
exactly as well as a ship."

| | |
|---|---|
| candidate | `c22_transition_variance`, catch22 feature `SB_TransitionMatrix_quantile_3_ac_sumdiagcov` |
| source | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821); reference code pycatch22 1.0.2, **GPL-3.0** — to be ported from the definitions, never from that code |
| outcome | **REVERTED** — no `pandas_ta/statistics/c22_transition_variance.py`, no wiring, no test module |
| harness | `docs/measure_c22_transition_variance.py` (sections FSANITY, SEARCH) |

## 0. Why this is a revert and not a port

Gate A asks for correctness "against the source" — here, the paper's and
hctsa's definitions, since the reference implementation is GPL-3.0 and may
only be used to MEASURE. Neither the Lubba et al. 2019 paper's full text nor
hctsa's own MATLAB source is available in this worktree or on the web (both
`docs/pine/` and web access are unavailable per the issue-solver rules), so
the only thing nameable from first principles is the paper's own one-line
gloss for this feature, quoted in the issue itself: "trace of covariance of
transition matrix between symbols in equiprobable 3-letter alphabet". That
names three steps — (1) discretise the window into 3 EQUIPROBABLE
quantile-based symbols, (2) form the one-step transition matrix of the
resulting symbol sequence, (3) take the covariance of that matrix and report
its trace — but it does not say the tie-breaking convention for the
quantile edges, whether the transition matrix is row-normalised (a
conditional distribution) or divided by the total pair count (a joint
distribution), which axis of the matrix the covariance treats as the set of
observations, or the covariance's `ddof`. Those are the load-bearing
readings `pycatch22`'s OUTPUT was used, as a BLACK-BOX NUMERIC ORACLE, to
pick — the same discipline `docs/measure_c22_rs_range.py` and
`docs/measure_c22_periodicity.py` §P use.

`docs/measure_c22_transition_variance.py`'s bare invocation (no arguments)
runs only §FSANITY, which never imports `pycatch22` — the same discipline
`docs/measure_c22_ami2.py` and `docs/measure_c22_rs_range.py` use. §SEARCH
calls the GPL-3.0 oracle and is opt-in: `python
docs/measure_c22_transition_variance.py SEARCH`. It opens with an
`importlib.util.find_spec("pycatch22")` check and prints ABSENT rather than
raising if the dev-only package is not installed (it is, in this worktree).

## A. What the search pinned, and what it could not

### A1. The symbolisation itself — SOUND, but that is necessary, not sufficient

`python docs/measure_c22_transition_variance.py` (bare, FSANITY only — no
`pycatch22` import). Four candidate quantile-symbolisation readings (value
thresholds with two half-open-interval conventions; equal-count binning by
rank, with two tie-breaking rules) were checked on 14 sampled windows of a
1,500-bar synthetic walk: every one gives each of the 3 symbols a 33.0% to
34.0% share (equiprobable, as the name requires), and every one's
row-normalised transition matrix is row-stochastic (rows sum to 1.0) where
it is defined at all. A second check (§FSANITY2, 61 windows) confirms all
four are invariant under both an affine rescale and a nonlinear monotone map
(cubing, sign-preserved) — 0 of 61 windows move either way for any of the
four, which is the property a RANK-based symbolisation must have and is
necessary for "equiprobable quantile bins" to mean what it says. This is
sanity, not identification: it says the ingredients are plausible readings
of the sentence, not that any one of them is the reference's own reading.

### A2. The reference's own value — a narrow, small-magnitude range

`python docs/measure_c22_transition_variance.py SEARCH` §SEARCH1: over 366
sampled windows (6 synthetic frames — walk, tick-rounded, penny, AR(1),
cosine, Student-t — 1,500 bars each, stride 23), `pycatch22.catch22_all`'s
`transition_variance` short name ranges over `[0.000204, 0.033181]`, median
0.004353. That narrow, near-zero-weighted range already rules OUT most of
the candidate space on SCALE alone, before Spearman or exact-match is even
considered. §SEARCH5 reports, for each of the three matrix normalisations,
the best (smallest max `|gap|`) row found anywhere in the 432-combination
grid: `normalize="row"` (each row of the transition matrix summing to 1)
bottoms out at a max `|gap|` of 1.446e-02, but the FAMILY spans up to
5.849e-01 and most of its rows (§SEARCH2's printed sample) sit at 0.32 to
0.54 — an order of magnitude too large to be this reference's own
magnitude, which tops out at 0.033. `normalize="total"` (the transition
matrix divided by the pair count — a joint rather than a conditional
distribution, entries near `1/9 ≈ 0.111`) is UNIFORMLY close in scale
across its whole family: 1.244e-02 to 5.776e-02. `normalize="none"` (raw
counts, no probability normalisation at all) is three to four orders of
magnitude off: 3.066e+01 to 5.986e+02. That is a real, measured finding —
not every reading of "transition matrix" even has the right SCALE, and
"total" is the only one that reliably does — but it is still well short of
identifying the exact formula.

### A3. The breakpoint across the whole grid — NOT FOUND

§SEARCH2: **4 symbolisations × 3 normalisations (row / total / raw-count) ×
3 covariance axes (rows-as-observations, columns-as-observations, the whole
matrix flattened into one variance) × 2 `ddof`s × 6 lags (1 .. 5, and the
classical `CO_FirstZero` autocorrelation-crossing lag — tried because the
operation's own name carries an `ac` token) = 432 combinations, all
implemented and run, not asserted**, against the reference's cached value on
all 366 windows. §SEARCH2's own printed table, ranked by exact agreement
within `1e-9` then by the smallest worst-case gap (top 8 of the 432, quoted
verbatim from a fresh run, not retyped by hand):

| symbolisation | normalize | axis | ddof | lag | exact (of 366) | max \|gap\| | Spearman ρ |
|---|---|---|---|---|---|---|---|
| quantile-rank-average | total | cols | 1 | `ac0` | 7 | 0.0203 | 0.578 |
| quantile-hctsa | total | cols | 1 | `ac0` | 7 | 0.0538 | 0.539 |
| quantile-rank-average | total | rows | 1 | `ac0` | 6 | 0.0200 | 0.578 |
| quantile-rank-average | total | rows | 1 | 1 | 6 | 0.0318 | 0.787 |
| quantile-rank-average | total | cols | 1 | 1 | 6 | 0.0319 | 0.787 |
| quantile-hctsa | total | cols | 1 | 1 | 6 | 0.0538 | 0.759 |
| quantile-hctsa | total | rows | 1 | 1 | 6 | 0.0550 | 0.759 |
| quantile-hctsa | total | rows | 1 | `ac0` | 6 | 0.0550 | 0.539 |

**No combination reaches exact agreement beyond 7 of 366 windows** (1.9%,
consistent with incidental matches rather than a correct formula). §SEARCH4
ranks the full 432-combination grid by Spearman ρ alone (a SEPARATE ranking
from §SEARCH2's exact-match-first one, printed separately rather than
quoted as if it were the same): the single highest is ρ = 0.7891
(`quantile-rank-first`, `normalize="none"`, lag 1), but that row's own
`normalize` is the wrong-scale family §A2 already ruled out (max `|gap|`
3.853e+02 — Spearman, a RANK statistic, does not care about absolute
scale, so a wrong-magnitude candidate can still rank well without being a
candidate worth shipping). Restricted to the right-scale `normalize="total"`
family, the best is ρ = 0.7890 (`quantile-rank-first`, `axis="rows"`,
`ddof=1`, lag 1, exact 2 of 366, max `|gap|` 2.994e-02 — this exact row is
printed by §SEARCH4, not §SEARCH2, whose top-15-by-exact-count cutoff drops
it below two other `exact=2` rows with a smaller gap). Every `ac`-style
dynamic lag tested, including the classical `CO_FirstZero` crossing, does
WORSE than a fixed lag of 1: 0.54 to 0.58 against 1's 0.76 to 0.79, so the
operation's own `ac` token is not a lag choice this harness's reading of it
can confirm. A Spearman ρ of 0.79 is a real, reproducible, monotone
relationship — stronger than mere chance, and stronger than this fork's
previous catch22 revert's own Spearman figure
(`docs/C22RsRangeMeasured.md`'s best row: Pearson ρ 0.364, Spearman ρ
0.345) — but it is a qualitative gap from this repo's own bar for a
correct port: every SHIPPED catch22 column in this fork (`c22_dfa`,
`c22_periodicity`, `c22_ami2`) is bit-equal or agrees with the reference on
effectively every sampled window, because
their defining sentence pinned the algorithm up to a handful of genuinely
close calls. Here, the best right-scale candidate by Spearman ρ
(`quantile-rank-first`, `total`, `rows`, `ddof=1`, lag 1) disagrees with the
reference's own value by as much as 0.0299 against a value range of only
0.033 — the error is comparable to the whole scale of the quantity, not a
last-bit question.

## B. What this means for Gates A–F

Gate A (correctness) cannot be cleared: no candidate among the 432
structural hypotheses tried in §A3 reproduces the named feature to a
confidence this repo's own bar requires ("every claim... must correspond to
a run" — a formula with ρ ≤ 0.789 at best, among the hypotheses this
harness's family covers, is not a correct port of
`SB_TransitionMatrix_quantile_3_ac_sumdiagcov`, whatever else it computes).
Gates B–E were not attempted beyond the suite run in §D, because they gate a
SPECIFIC module's causality, reachability, scale-invariance and suite
health, and there is no module whose identity as that named feature is
established.

**Gate E does not apply to this issue.** It measures a shipped `Category`
column's overlap against the engine's comparators; there is no column here
for the launcher to run it against. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is unaffected: `c22_transition_variance` was never added to `Category`, so
it never needed a row.

## C. What is NOT in this tree

- `pandas_ta/statistics/c22_transition_variance.py` — not written.
- No `Category` entry, no `core.py` accessor, no package export.
- `tests/test_c22_transition_variance.py` — not written.
- `docs/gate_e_ledger.csv` — unchanged.
- The three counts `tests/test_readme_counts.py` checks, `CATEGORY_TOTAL` in
  `tests/test_altport2_ports.py`, and `docs/MLCompanionContract.md`'s tagged
  counts — all unchanged, because nothing was added to count.

## D. Gate F — suites

| run | result |
|---|---|
| `python -m pytest -q tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` | **1290 passed, 7 skipped** |

No port test module exists to run, by construction (§C). Both repos' whole
suites: run by issue-solver in clean worktrees (see the PR body).

## E. Related open work

The symbolisation building blocks (§A1 — equiprobable quantile binning,
confirmed rank-invariant under affine and nonlinear monotone maps) and the
scale finding (§A2 — a row-stochastic transition matrix is the wrong order
of magnitude, a total-pair-count joint matrix is the right one) are solid
ground a future attempt could build on, rather than hypotheses to re-run. A
future attempt at this feature needs the paper's or hctsa's actual text
describing the transition-matrix normalisation and the covariance's
axis/divisor convention: this receipt's negative result bounds only the
432-combination hypothesis family tried, not every possible reading, so it
is a starting point, not a proof that none exists. The issue's own screen
prototype (`docs/issues/screen/ind_screen_r3.py`, local to the owner's
machine) used `pycatch22`'s own implementation directly and is not affected
by this revert.
