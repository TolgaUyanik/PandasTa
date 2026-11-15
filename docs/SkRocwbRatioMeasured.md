# SK-ROCWB-RATIO — `sk_rocwb_ratio` measured (PandasTa issue #109)

ROC over its own 5-bar RMS band, `(20, 5)`. Module
`pandas_ta/momentum/sk_rocwb_ratio.py`, tests `tests/test_sk_rocwb_ratio.py`.

    ROC[T]              = 100 * (close[T] / close[T - 20] - 1)
    band[T]             = sqrt(mean(ROC[T - 4 .. T]^2))     -- an RMS, not a stdev
    SK_ROCWB_RATIO_20_5 = ROC[T] / band[T]                  -- +-inf folded to NaN

Source: Skender Stock.Indicators (Apache-2.0), `RocWb`, as issue #109 names it
("RocWb.Series.cs: ROC20 vs band sqrt(mean5(ROC20^2))"). The RATIO is the fork's,
from the 2026-10-24 catalog screen's scale-free candidate `sk_rocwb_ratio`
(`docs/issues/screen/ind_screen_r2.py`): Skender returns the ROC and the band as
two series in the same units, which is two features where this is one.

**Every number below except §E's and Gate F's is printed by
`python docs/measure_sk_rocwb_ratio.py`** (one section per gate limb;
`python docs/measure_sk_rocwb_ratio.py A1 D` for named sections). §E's figures are
the ISSUE's, quoted from the screen's run on the prototype; Gate F's are the
pytest runs named there. The same figures appear in the module docstring and in
`tests/test_sk_rocwb_ratio.py`, and this file is the only place they may come
from. `python docs/measure_sk_rocwb_ratio_cpu.py` re-runs the test module with
numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled.

Measured 2026-11-15 on this machine: pandas 2.3.3, numpy 1.26.4, Python 3.11.

⚠ **No real-data figure measured on THIS module.** Every count and range about
this column comes from eight synthetic frames of 1,500 bars — plus §C3's 300-bar
flat OHLCV frame, §Z's 100,000- and 400,000-bar walks, and §W2's parse of the
generated dictionary. The only real-data numbers in the file are §E's, and they
are the SCREEN's, measured on the prototype in October, not this port's.

**Gate C's real-data limb is OWED** and is listed as ASSUMPTION 5 at the foot of
this file: the session that records the launcher's Gate E run fills in the
fired-bar count over the 89 ALTPORT-1 BIST frames and — the figure that matters
for this column specifically — how often `close[T] == close[T - 20]` there,
because an exactly-zero ROC is what makes this column read 0.0, and five of them
in a row is the only thing that makes it blank. 21.17% of real BIST daily bars
close exactly at an extreme (`CLAUDE.md`, FVGDEAD); the 2.0-tick `coarse` frame
below is a stand-in for that regime and not a prediction of it.

## The frames

Eight synthetic close paths, 1,500 bars each, level 100, the builders and seeds of
`docs/measure_sk_fcb_pos.py` (issue #108) minus the high/low spread, because this
column reads only `close`:

| frame | what it is |
|---|---|
| `walk` | lognormal random walk, sigma 0.01 |
| `trend` | drifting walk, mu 0.003 |
| `range-bound` | AR(1) in log price, phi 0.9 |
| `grid` | `walk` rounded to a 0.01 tick |
| `heavy-tailed` | Student-t(2) innovations |
| `jump` | `walk` with a x1.5 level jump at bar 700 |
| `flat` | a constant price |
| `coarse` | `walk` rounded to a **2.0** tick — coarser than its own bar-to-bar move |

`coarse` is the frame that matters most here and not for the reason the sibling
ports keep it: a coarse grid makes `close[T] == close[T - 20]` an everyday event,
so the ROC is **exactly 0** on 449 of its bars and a window of five exact zeros is
the only input that makes this column blank. FVGDEAD (`CLAUDE.md`) is this repo's
record of a column whose behaviour on synthetic continuous floats said nothing
about its behaviour on rounded prices.

---

## §C2 THE BOUND — the section to read first

The band is a **root mean square**, so nothing is subtracted before squaring and
`roc[T]` is one of the `band_length` terms of its own denominator:

    band[T]^2 = (roc[T]^2 + roc[T-1]^2 + ... ) / band_length >= roc[T]^2 / band_length
    => |SK_ROCWB_RATIO[T]| <= sqrt(band_length) = 2.2360680 at the default

| frame | fired | min | max | max \|x\| | \|x\| / sqrt(5) | over strict | over 1e-12 |
|---|---|---|---|---|---|---|---|
| `walk` | 1476 | -2.2161 | 2.1415 | 2.2161 | 0.9911 | 0 | 0 |
| `trend` | 1476 | -1.8866 | 2.1108 | 2.1108 | 0.9440 | 0 | 0 |
| `range-bound` | 1476 | -2.1639 | 2.1850 | 2.1850 | 0.9772 | 0 | 0 |
| `grid` | 1476 | -2.0793 | 2.1420 | 2.1420 | 0.9580 | 0 | 0 |
| `heavy-tailed` | 1476 | -2.1655 | 2.1787 | 2.1787 | 0.9743 | 0 | 0 |
| `jump` | 1476 | -2.1658 | 2.2288 | 2.2288 | 0.9968 | 0 | 0 |
| `coarse` | 1370 | -2.2361 | 2.2361 | 2.2361 | 1.0000 | 0 | 0 |

Two "over" columns because `math.sqrt(5)` is itself a rounded double and the test
asserts the bound with 1e-12 of relative slack: `over strict` counts bars above
`math.sqrt(5)` at all, `over 1e-12` bars above it by more than that slack. Both
are 0 on every frame, so the module's `Returns:` line is entitled to the closed
interval it states.

`closest` is rounded to four decimals, so 1.0000 is not by itself a claim of
exactness. The harness therefore prints the ulp distance for any frame that
rounds to 1.0000, and there is one: `coarse`'s `max |x|` is
`2.23606797749979`, **0 ulps** from `math.sqrt(5)`. It genuinely attains the
bound.

The bound is **tight and attained**: 24 constant closes followed by one move reads
`2.23606797749979`, which is `sqrt(5)` to **0 ulps**, and `-2.23606797749979` with
the move down. A random walk gets to 0.9911 of it without touching it; the frame
that touches it, at 0 ulps as above, is the 2.0-tick one, where a flat band window
is a rounding artefact rather than a quiet market.

⚠ The bound is on the VALUE, not on the information. A bar at +2.236 says "the
other four ROC readings were ~0", which on a tick grid is a statement about
rounding. But no consumer has to clip or winsorise this column, which is the whole
reason the ratio ships instead of Skender's two price-unit series.

⚠ **The reading not taken.** The band as a STANDARD DEVIATION of the ROC (ddof=0)
— which is what a reader who knows Bollinger-style bands will assume — is a
DIFFERENT COLUMN and an unbounded one, because the mean subtraction stops the
numerator being one of the denominator's terms:

| frame | differ | Spearman vs this column | RMS max \|x\| | stdev max \|x\| |
|---|---|---|---|---|
| `walk` | 1476 | 0.8524 | 2.2161 | 31.9722 |
| `trend` | 1476 | 0.3251 | 2.1108 | 71.3112 |
| `range-bound` | 1476 | 0.9163 | 2.1850 | 17.8897 |
| `grid` | 1475 | 0.8605 | 2.1420 | 61.6648 |
| `heavy-tailed` | 1476 | 0.8609 | 2.1787 | 138.9931 |
| `jump` | 1476 | 0.8731 | 2.2288 | 132.7800 |
| `coarse` | 1027 | 0.8925 | 2.2361 | 110.0000 |

---

## Gate A — correctness

The issue's instruction is that Gate A starts from the SOURCE formula, not the
prototype. ⚠ `RocWb.Series.cs` itself is **not readable from this worktree**:
Stock.Indicators is not installed, `docs/pine/` is absent, and a repo-wide search
for a `Roc*.cs` finds nothing — pinned by
`tests/test_sk_rocwb_ratio.py::test_the_source_library_is_not_readable_here` so the
claim cannot rot into "checked against Skender" if a dependency or a vendored
corpus ever appears. ⚠ Web access was also unavailable in the session that wrote
this, and that one no test can see. So Gate A checks the formula the ISSUE names,
spelled three ways, and the attribution is to the issue's naming of the source.

### §A1 — the source formula by explicit scalar loops

Two Python loops over numpy scalars: Skender's own algebra for the ROC,
`100 * (c - c20) / c20`, and a FRESH five-term sum of squares (not a pandas
rolling mean). Shares no pandas operation with the module.

| frame | bars | fired | bit-equal | differ | max rel | max abs | Spearman |
|---|---|---|---|---|---|---|---|
| `walk` | 1500 | 1476 | False | 1375 | 4.007e-12 | 2.909e-14 | 1.0000 |
| `trend` | 1500 | 1476 | False | 1372 | 4.524e-13 | 1.099e-14 | 1.0000 |
| `range-bound` | 1500 | 1476 | False | 1398 | 8.911e-13 | 1.465e-14 | 1.0000 |
| `grid` | 1500 | 1476 | False | 1401 | 4.835e-13 | 3.553e-14 | 1.0000 |
| `heavy-tailed` | 1500 | 1476 | False | 1375 | 1.373e-12 | 1.721e-14 | 1.0000 |
| `jump` | 1500 | 1476 | False | 1367 | 1.335e-12 | 2.337e-14 | 1.0000 |
| `flat` | 1500 | 0 | True | 0 | — | — | — |
| `coarse` | 1500 | 1370 | False | 575 | 4.229e-15 | 4.219e-15 | 0.9999 |

Not bit-equal, and that is the finding rather than a weakness: `100 * (c - c20) / c20`
and `100 * (c / c20 - 1)` are the same identity and not the same double. The NaN
masks match on every frame.

### §A2 — the same loops, the module's spelling, and the prototype

With the ROC respelled `100 * (c / c20 - 1)` and nothing else changed:

| frame | bit-equal | differ | max rel |
|---|---|---|---|
| `walk` | False | 794 | 2.335e-14 |
| `trend` | False | 244 | 3.306e-16 |
| `range-bound` | False | 1082 | 9.457e-15 |
| `grid` | False | 408 | 1.025e-14 |
| `heavy-tailed` | False | 336 | 2.638e-15 |
| `jump` | False | 442 | 1.449e-14 |
| `flat` | True | 0 | — |
| `coarse` | False | 102 | 4.314e-16 |

⚠ Still not bit-equal, and the reason is worth carrying out of this port: **pandas'
rolling mean is an online add/remove accumulator**, so it does not agree to the
last bit with a fresh five-term sum of the same five numbers. Any "bit-equal to a
hand-written oracle" claim about a rolling window should be checked, not assumed.

The screen prototype, retyped — the expression Gate E's 0.8537 was measured on —
**is** bit-equal, on all eight frames, 0 bars differing. That equality is
structural (the prototype is this module's expression without the `isfinite`
mask), and what it buys is the tie to the screen's figures.

### §A3 — why this module does not import `pandas_ta.roc`

`roc` computes `100 * mom(close, length) / close.shift(length)`, i.e. Skender's
spelling. Building the same ratio on it:

| frame | differ | max rel | max abs | Spearman | bit-equal |
|---|---|---|---|---|---|
| `walk` | 1372 | 4.007e-12 | 6.173e-14 | 1.0000 | False |
| `trend` | 1377 | 4.524e-13 | 1.099e-14 | 1.0000 | False |
| `range-bound` | 1411 | 8.903e-13 | 3.508e-14 | 1.0000 | False |
| `grid` | 1405 | 4.837e-13 | 6.306e-14 | 1.0000 | False |
| `heavy-tailed` | 1377 | 1.373e-12 | 8.793e-14 | 1.0000 | False |
| `jump` | 1408 | 1.562e-12 | 3.857e-13 | 1.0000 | False |
| `flat` | 0 | — | — | — | True |
| `coarse` | 703 | 4.229e-15 | 5.329e-15 | 0.9999 | False |

The repo's rule is to import a helper rather than retype it. **This port
deliberately does not, and the reason is provenance, not numerical risk.**

What the table shows is that the two spellings differ by up to 4.007e-12 relative
on 703 .. 1,411 bars per frame at Spearman 1.0000 — which is far too small to move
a Gate E rho reported to four decimals, and no claim here says otherwise. Nor is
there a bit-exact "tie" to protect: the ledger fingerprints THIS module
(`module_sha1`, `output_fp`, `pandas_ta_src_sha1`), and the port's own rho comes
from the launcher's run, not from the screen's.

The reason to retype the two lines is that the issue's 0.8537 was measured on the
prototype's expression, and shipping that expression bit for bit (§A2) makes the
port and the screened candidate the same object rather than two columns that agree
to 4e-12. The override costs two lines of arithmetic that `roc` already contains,
and it is recorded as ASSUMPTION 2 rather than left implicit. Importing `roc` and
re-running §A1 .. §A3 would be a defensible alternative; it was not taken.

---

## Gate B — causality

### §B the blind sweep

For each boundary `j`: two closes that agree bit for bit on bars `< j` and differ
wholly on bars `>= j` (every later bar scaled by a random factor in [1, 4], and by
its reciprocal). A causal column is bit-identical on the shared prefix. **Every**
boundary of every frame, not a sample:

| frame | offsets | caught |
|---|---|---|
| all eight | 1,499 each | **0** |

### §B1 five look-ahead mutants, read off the shipped source

Each is an edit to `pandas_ta/momentum/sk_rocwb_ratio.py` read off disk, `exec`'d
in memory, and swept by the same detector. `live` = frames on which the mutant's
output differs from the module's at all (an edit that failed to apply would sweep
clean and prove nothing); the remaining columns are catches out of 36 offsets
(bars 1464 .. 1499).

| mutant | live | walk | trend | range-b | grid | heavy-t | jump | flat | coarse |
|---|---|---|---|---|---|---|---|---|---|
| `roc-lead` (`shift(-length)`) | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 |
| `close-lead` (`c.shift(-1)` numerator) | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 |
| `band-centred` (`center=True`) | 7 | 36 | 36 | 36 | 36 | 36 | 36 | **0** | **15** |
| `band-lead` (`band.shift(-1)`) | 7 | 36 | 36 | 36 | 36 | 36 | 36 | **0** | **10** |
| `output-early` (`ratio.shift(-1)`) | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 36 | 36 |

`live` is 7 of 8 for every mutant: the eighth is `flat`, where the module and every
mutant are all-NaN.

### §B2 the two band mutants, swept densely

A 36-of-36 headline is not available for the two that shift the BAND, and the
reason is arithmetic: a shifted band multiplies a numerator that is **exactly 0**
on **449** bars of `coarse` (343 of which read 0.0 and 106 of which are blank,
§C4) and on every bar of `flat`, and `0 / anything` is 0 either way. Each is given a NECESSARY condition, computed from the clean frame's own ROC
rather than argued — `band-lead` can only move bar `j - 1`, `band-centred` bars
`j - 1` and `j - 2`, and only if that bar's numerator is a non-zero number and its
window fits inside the frame — and swept over every offset of every frame:

| mutant | offsets | exposed | caught | caught inside | **caught outside** | **exposed but missed** |
|---|---|---|---|---|---|---|
| `band-lead` | 11,992 | 9,883 | 9,883 | 9,883 | **0** | **0** |
| `band-centred` | 11,992 | 10,034 | 10,034 | 10,034 | **0** | **0** |

The sweep runs every boundary from 1 to 1,499 of all eight frames — deliberately
including the boundaries where the bars the condition talks about do not exist,
because starting it after the warm-up would make a loose condition look exact.

Per frame: `band-lead` is exposed on 1,476 of 1,499 offsets on `walk`, `trend`,
`range-bound`, `heavy-tailed` and `jump`, **1,475 on `grid`** (which carries one
exactly-zero ROC bar), 1,028 on `coarse` and **0** on `flat` — 9,883 in total.
`band-centred` is exposed on 1,477 on those same six frames, `grid` included,
because its condition is a disjunction over bars `j - 1` and `j - 2` and one
zero-ROC bar costs it nothing; 1,172 on `coarse`, 0 on `flat` — 10,034 in total.
The condition is exact in both directions on every one of those offsets: nothing
is caught outside it and nothing exposed is missed.

⚠ The practical lesson is about Gate B method, not about this column: a flat frame
can hide a whole class of look-ahead. A Gate B argument that rested on one frame
could have rested on that one.

---

## Gate C — reachability

⚠ **Synthetic only; the real-data limb is owed** (see the head of this file and
ASSUMPTION 5). `CLAUDE.md` defines Gate C as "every shipped column fires on real
data, with counts stated", and the counts below are not that.

| frame | bars | fired | first | distinct | min | max | bars reading exactly 0.0 |
|---|---|---|---|---|---|---|---|
| `walk` | 1500 | 1476 | 24 | 1476 | -2.2161 | 2.1415 | 0 |
| `trend` | 1500 | 1476 | 24 | 1476 | -1.8866 | 2.1108 | 0 |
| `range-bound` | 1500 | 1476 | 24 | 1476 | -2.1639 | 2.1850 | 0 |
| `grid` | 1500 | 1476 | 24 | 1476 | -2.0793 | 2.1420 | 1 |
| `heavy-tailed` | 1500 | 1476 | 24 | 1476 | -2.1655 | 2.1787 | 0 |
| `jump` | 1500 | 1476 | 24 | 1476 | -2.1658 | 2.2288 | 0 |
| `flat` | 1500 | **0** | — | 0 | — | — | 0 |
| `coarse` | 1500 | 1370 | 24 | 501 | -2.2361 | 2.2361 | 343 |

The warm-up is a **constant 24 bars** (`length + band_length - 1`), not
data-dependent: unlike the fractal ports there is no event to wait for. The
shortest input that produces a value is 25 bars, which is also `verify_series`'
floor — 24 bars returns `None`.

### §C4 the only way the column goes blank

`band == 0` needs five consecutive EXACTLY zero ROC readings. A squared ROC is 0
only if the ROC is: `c / c20` is either exactly 1 or at least one ulp away from it,
so a non-zero `|ROC|` is at least ~1.1e-14 and its square is nowhere near
underflow. Measured smallest non-zero `|ROC|` per frame: 5.888e-04 (`walk`),
9.228e-03, 1.241e-02, 7.891e-03, 5.491e-03, 3.793e-03, and 2.273e+00 on `coarse`.

A patch of L constant closes carries L - 20 zero ROC readings, so 25 is the
shortest patch that empties anything:

| flat patch | bars emptied | bars with band 0 |
|---|---|---|
| 20 | 0 | 0 |
| 23 | 0 | 0 |
| 24 | 0 | 0 |
| **25** | **1** | 1 |
| 29 | 5 | 5 |
| 40 | 16 | 16 |

On `coarse` rounding does it without any flat patch: 449 bars read a ROC of exactly
0, 106 bars are emptied, and **343 bars read exactly 0.0** — a value, not a gap:
the price is where it was 20 bars ago while the other four readings were not.

### §C3 a flat price fires nothing, and that is ordinary for the bucket

Claimed about 86 other indicators, so it was RUN: every name in
`Category["momentum"]` on one flat OHLCV frame, through the accessor.

| | n |
|---|---|
| names | 87 |
| columns | 144 |
| **all-NaN** | **42** (this column among them) |
| all-zero | 77 |
| something else | 25 |
| raised | 0 |

The all-NaN company includes `CMO_14`, `CCI_14_0.015`, `ER_10`, `IMI_14`,
`CTI_12`, `CRSI_STREAK_2` and `INERTIA_20_14`.

---

## Gate D — scale-free

The price enters only as `close[T] / close[T - 20]`, so a positive rescale cancels
before the first arithmetic.

| factor | result |
|---|---|
| x8, x64 | **bit-identical** on every fired bar of all eight frames |
| 2^-20, 2^20, 2^300 | **bit-identical on all eight frames**, each factor swept over each frame |
| x10, x3.7, x0.1, x1.0000001 | NaN masks match everywhere; max 1.885e-11 relative (`walk` x1.0000001), Spearman 1.0000 (0.9999 on `coarse` x0.1) |
| price level 1e-6 / 1e+6 / 1e+100 (inexact factors) | not bit-equal; 1.885e-11 / 6.709e-13 / 1.885e-11 relative, 1476 fired, Spearman 1.0000 |

Tests assert the inexact factors at **1e-7**, four orders of margin over the
measurement, because a quotient of two small numbers amplifies a last-bit move.

⚠ **A level shift is NOT invariant**, and the sibling `sk_fcb_pos` is — assuming
it here would be wrong. A ratio of prices is not a ratio of prices-plus-a-constant:

| shift (walk at level 100) | max abs | max rel | Spearman |
|---|---|---|---|
| +1 | 9.437e-04 | 1.168e-03 | 1.0000 |
| +50 | 2.325e-02 | 2.923e-02 | 1.0000 |
| +1e6 | 4.491e-02 | 6.905e-02 | 0.9999 |

Small, and not zero. Gate D's other limb, `0 < fires < n`, is Gate C's table: the
seven firing frames fire 1,370 .. 1,476 of 1,500, and `flat` fires 0 — a reading
about a constant price, priced in §C3.

---

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

The port is wired into `Category`, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails
locally until the run is recorded (it is a skip in CI, which sets
`GATE_E_PENDING_OK=1`). `tests/test_sk_rocwb_ratio.py::test_the_gate_e_row_is_owed_and_not_yet_recorded`
pins that state deliberately; the receipt session replaces it with one pinning the
recorded row's identity, the shape issues #107 and #108 used.

What the 2026-10-24 screen measured **on the prototype** — a prototype is not a
port, and these figures are the issue's, not this session's:

| | |
|---|---|
| pooled max \|rho\| | **0.8537** vs `zscore` (compute_all), n = 396,264 |
| top-5 per-frame max median | 0.8535 |
| verdict | **DISCLOSE_GAP** (0.80 <= rho < 0.90), which SHIPS |
| next comparators | `bias_ta` 0.8192, `Ret_21d_vol_adj` 0.8183 |
| run | `screen_r2_20261024`, 89 ALTPORT-1 frames, 398,849 bars, 687 comparators, canary bit-equal |

§A2 asserts this module bit-equal to that prototype on all eight synthetic frames,
so the port and the screened expression are the same column — but the figure above
is still the prototype's, and the port's own number comes from the launcher's run.

### §F — non-redundancy against the fork's own close-only columns, synthetic

⚠ A DISCLOSURE, not a gate: Gate E measures 687 engine comparators over 89 real
BIST frames. Spearman on the synthetic frames:

| frame | ROC_20 | ROC_5 | MOM_20 | RSI_14 | CMO_14 | ZS_30 | ZS_20 of ROC_20 |
|---|---|---|---|---|---|---|---|
| `walk` | 0.8681 | 0.5848 | 0.8663 | 0.8027 | 0.8027 | 0.8717 | 0.6425 |
| `trend` | 0.3883 | 0.5357 | 0.2516 | 0.4062 | 0.4062 | 0.6795 | 0.6959 |
| `range-bound` | 0.9317 | 0.4371 | 0.9311 | 0.7499 | 0.7499 | 0.8093 | 0.8045 |
| `grid` | 0.8698 | 0.5536 | 0.8648 | 0.7982 | 0.7982 | 0.8596 | 0.6193 |
| `heavy-tailed` | 0.8830 | 0.5194 | 0.8835 | 0.8031 | 0.8031 | 0.8644 | 0.6647 |
| `jump` | 0.8913 | 0.5132 | 0.8896 | 0.8036 | 0.8036 | 0.8644 | 0.6910 |
| `coarse` | 0.8947 | 0.5462 | 0.9040 | 0.8037 | 0.8038 | 0.8726 | 0.6791 |

The sign is shared with `ROC_20` by construction — the band is positive — so a high
rank correlation there is expected and is not news; what the column adds is the
SIZE, normalised by the recent RMS. The screen's own comparator, a z-score, sits at
0.6795 .. 0.8726 here against 0.8537 on real data.

---

## §G Guards, each priced

One bar of a 1,500-bar walk is replaced at index 700. `emptied` = bars that went
NaN, `moved` = bars whose value changed, `earlier` = either, before the plant.

| plant | emptied | moved | earlier | new bars reading 0.0 | first | last |
|---|---|---|---|---|---|---|
| NaN | 10 | 230 | **0** | 0 | 700 | 1024 |
| +inf | 10 | 230 | **0** | 0 | 700 | 1024 |
| -inf | 10 | 230 | **0** | 0 | 700 | 1024 |
| 0.0 | 5 | 235 | **0** | 0 | 700 | 1024 |
| -1.0 | 0 | 240 | **0** | 0 | 700 | 1024 |
| 1e-310 | 5 | 235 | **0** | 0 | 700 | 1024 |
| 1e+300 | 5 | 235 | **0** | 0 | 700 | 1024 |

* A **NaN** close empties exactly the 10 bars the formula implies — 700 .. 704 and
  720 .. 724 — its own band windows and the same five 20 bars later.
* A **zero, subnormal or 1e+300** close is a FINITE price, so the `isfinite` mask
  does not touch it: 1e+300 empties 700 .. 704 (its squared ROC overflows), 0.0 and
  1e-310 empty 720 .. 724 (they make the LATER ROC infinite), and a **negative**
  close empties nothing at all.
* ⚠ **No plant leaves a quiet 0.0.** The obvious failure mode — a finite numerator
  over an infinite band reading 0.0 — does not happen, because pandas' rolling mean
  turns a window NaN rather than carrying `inf` through it. Measured 0 new bars
  reading exactly 0.0 on all seven plants.
* ⚠ **The forward reach is not 10 bars.** Every plant moves 230 .. 240 bars, out to
  bar 1024, in their LAST BITS (max 3.375e-14 absolute, the same figure for every
  plant). That is the online accumulator of §A2 again: a bar that passes through the
  window changes the running sum's rounding for every window after it. A last-bit
  effect, not a second signal — and the reason it is disclosed is that a single bad
  tick is not exactly undone 25 bars later.

### §G2 the `isfinite` mask — a DIVERGENCE from the prototype, and what it buys

| plant | masked == the NaN column | unmasked == masked | unmasked emptied |
|---|---|---|---|
| NaN | True | True | 10 |
| +inf | **True** | False | **5** |
| -inf | **True** | False | **5** |

Masked, an infinite close empties 700 .. 704 **and** 720 .. 724. Unmasked it empties
only 700 .. 704, and the five bars at 720 .. 724 carry plausible NUMBERS computed off
an infinite base price:

| bar | unmasked | clean | masked |
|---|---|---|---|
| 720 | **-2.2216** | 0.4980 | NaN |
| 721 | 0.0587 | 0.5836 | NaN |
| 722 | -0.0204 | -0.2787 | NaN |
| 723 | -0.0043 | -0.0893 | NaN |
| 724 | -0.0136 | -0.3520 | NaN |

A number near the bound is harder to notice than a gap. On FINITE input the masked
and unmasked columns are bit-identical on all eight frames, which is what keeps the
tie to the prototype's Gate E measurement despite the divergence.

### §G3 the `+-inf -> NaN` fold is dead code, kept on purpose

`band == 0` forces `roc[T] == 0` with it, so the quotient is `0 / 0` = NaN and never
`+-inf`. Measured with the fold removed (a mutant of the shipped source): **0**
infinite raw bars on all eight frames and on the 0.0, 1e+300, +inf and -1.0 plants,
and the folded and unfolded columns identical everywhere. It stays because it is
the prototype's expression and the prototype is what Gate E measured; deleting it
would change the shipped column on no evidence.

---

## §W Wiring — the five touch points

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/momentum/sk_rocwb_ratio.py` | added |
| 2 | `pandas_ta/momentum/__init__.py` | `from .sk_rocwb_ratio import sk_rocwb_ratio` |
| 3 | `pandas_ta/__init__.py` → `Category["momentum"]` | added (momentum 86 -> **87**, Category total 347 -> **348**) |
| 4 | `pandas_ta/core.py` → `df.ta.sk_rocwb_ratio()` | added, both lengths forwarded |
| 5 | `tests/test_sk_rocwb_ratio.py` | **186 tests** |

Also touched: `README.md` (348 / 356 / momentum list), `docs/IndicatorDictionary.md`
(regenerated), `docs/MLCompanionContract.md` (692 -> 693 tagged columns,
331 -> **332** `SF`, counted from the regenerated dictionary in §W2, where every
other tag — 137 `PX`, 104 `BIN`, 54 `ORD`, 43 `CONST`, 2 `PX2`, 21 `??` —
reproduces the contract's current figure), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL` 347 -> 348).

Column `SK_ROCWB_RATIO_20_5`, category tag `momentum`, accessor output bit-equal to
the direct call. `offset=2` shifts by two bars; `fillna=-9.0` fills the 24 warm-up
bars. Non-default `length=10, band_length=3` names itself `SK_ROCWB_RATIO_10_3`,
fires first at bar 12 and stays inside `sqrt(3)` = 1.7321 (measured max 1.7305).

The dictionary cut: the generator shows `d[:150].rsplit(' ', 1)[0]` of the first
docstring paragraph, which is **138 characters** here — 12 to spare before a whole
word would be lost.

## §Z Cost

Vectorised throughout, no Python loop: `isfinite` and `where`, one shift, a divide,
a subtract, a multiply, a square, one rolling mean, a `sqrt`, a second divide and
the `replace` — plus a shift only when `offset != 0`. Time and memory are linear in
bars.

| bars | peak MB | peak MB (2nd run) | ms | ms (2nd run) |
|---|---|---|---|---|
| 100,000 | 5.1 | 5.1 | 4.5 | 4.3 |
| 400,000 | 20.4 | 20.4 | 16.7 | 16.8 |

⚠ The wall clock is disclosed, not claimed: both runs are printed because two
invocations of the same section already disagree.

---

## Gate F — suites

* `python -m pytest tests/test_sk_rocwb_ratio.py -q` → **186 passed**
* `python docs/measure_sk_rocwb_ratio_cpu.py` → the same **186 passed** with numpy's
  `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled (numpy 1.26.4; the run prints the
  features still enabled, so the claim cannot drift from what was turned off)
* `python -m pytest -q` (whole fork) → **3 failed, 9711 passed, 85 skipped** in 256 s.
  The three:
  1. `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` — the
     known break of `CLAUDE.md`, a clean checkout fails it;
  2. `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
     — needs the sibling `../AlternativeRepos` checkout, deselected in CI;
  3. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` —
     **Gate E owed**, this port among eight indicators already on that list
     (`arch_lm`, `diff2_acf1`, `edge`, `firstzero_ac`, `halflife`, `lumpiness`,
     `mtd_ret`, `sk_rocwb_ratio`). A skip in CI, which sets `GATE_E_PENDING_OK=1`.
* The Backtesting suite is the launcher's to run, in a clean worktree.

## Decision

**SHIP, pending the launcher's Gate E run.** The prototype measured DISCLOSE_GAP
(0.8537 vs `zscore`), which ships, and §A2 asserts this module bit-equal to that
prototype. If the port's own run comes back STRUCK, the revert is the usual one —
remove the module, its wiring and its tests, keep this file as the receipt.

## ASSUMPTIONS recorded in this session

1. **The band is an RMS of the ROC over 5 bars**, as the issue states
   (`sqrt(mean5(ROC20^2))`), not a standard deviation and not an EMA-centred band.
   `RocWb.Series.cs` could not be read to confirm the C# spelling; §C2 measures what
   the stdev reading would have been instead, so the choice is priced rather than
   assumed silently.
2. **The ROC is spelled the prototype's way**, `100 * (c / c20 - 1)`, not the
   shipped `roc`'s `100 * (c - c20) / c20`, overriding the repo's import-the-helper
   rule. §A3 measures the gap at 4.007e-12 relative, Spearman 1.0000 — too small
   to move a Gate E figure — so the override is for PROVENANCE (the port is then
   the screened expression bit for bit, §A2) and not because importing `roc`
   would be numerically risky. Importing it and re-running §A1 .. §A3 was the
   alternative and was not taken.
3. **The `isfinite` mask is added**, diverging from the prototype, on the evidence
   in §G2. On finite input — every real price frame — the two are bit-identical, so
   the Gate E tie is unaffected.
4. **The `+-inf -> NaN` fold is kept** although §G3 measures it dead, because
   removing it would change the shipped expression with no measurement behind the
   change.
5. **Gate C's real-data limb is OWED to the receipt session**, with each number's
   source named so the limb cannot quietly go unpaid. This session cannot touch
   `../Backtesting`, so nothing here is measured on the 89 ALTPORT-1 BIST frames.
   From the launcher's Gate E ledger row the receipt session can read:
   * fired bars out of 398,849 pooled — the row's `non_nan`;
   * bars reading exactly 0.0 — `non_nan - non_zero`.
   ⚠ **What the row does NOT carry** is the figure peculiar to this column: how
   often `close[T] == close[T - 20]` on those frames. The row counts NaNs and
   zeros, not price ties, so that needs a separate pass over the BIST cache;
   absent one, `non_nan - non_zero` is a LOWER BOUND on it, because the zero-ROC
   bars that fall inside a blanked band window are not counted anywhere.
   §C4's 449 / 106 / 343 are a 2.0-tick synthetic stand-in for that regime, chosen
   because 21.17% of real BIST daily bars close exactly at an extreme
   (`CLAUDE.md`, FVGDEAD), and they are not a prediction of the real counts.
