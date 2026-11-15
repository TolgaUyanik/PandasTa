# TFSPECENT_64 — measured

`tf_spec_entropy_64` (statistics), PandasTa issue **#111**, TF-SPEC-ENTROPY-64.
Port of TSFEL's `spectral_entropy` (BSD-3-Clause), in the scale-free form the
owner's 2026-10-24 round-2 catalog screen prototyped
(`docs/issues/screen/ind_screen_r2.py:229-252`, candidate `tf_spec_entropy_64`,
local to the owner's machine — `docs/issues/` is gitignored).

    RET          = close / close[1] - 1
    W            = RET[T - length + 1 .. T] - mean(RET[T - length + 1 .. T])
    P            = abs(rfft(W))[1:] ** 2          # length // 2 bins, DC dropped
    p            = P / SUM(P)
    TFSPECENT[T] = -SUM(p * log2(p)) / log2(length // 2)

One column, `TFSPECENT_64`, dimensionless, in `[0, 1]`. Dictionary tag `SF`,
warm-up 64.

**Every number below is printed by `python docs/measure_tf_spec_entropy_64.py`**
(section letters match the headings), on `numpy 1.26.4`, on nine synthetic
1,500-bar frames unless a section says otherwise. `python
docs/measure_tf_spec_entropy_64_cpu.py` re-runs the test module — and any named
section — with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`.

The frames: `walk` (Gaussian random walk), `trend` (drifting walk),
`range-bound` (AR(1) in log price), `grid` (walk rounded to a 0.01 tick),
`heavy-tailed` (Student-t, df 2), `jump` (walk with a x1.5 step at the middle),
`cycle` (returns = one sinusoid on bin 8 plus light noise), `flat` (a constant
price) and `ramp` (200 bars of `100 * 2 ** k`, whose returns are all exactly
1.0). The last two have **no spectrum at all** and fire nowhere; the other
seven are called *firing* below.

---

## Gate A — correctness

### §A — what the source actually says, and what it does not

⚠ **TSFEL is not installed in this worktree, `docs/pine/` does not carry it,
and web access is unavailable.** The whole of the source text available here is
the line issue #111 quotes:

> `features.py spectral_entropy: normalised entropy of the power spectrum`

So Gate A does **not** read TSFEL's own code, and nothing in this document is
evidence about how TSFEL handles an edge the issue does not name — a zero-power
window, a NaN, or whether it keeps the DC bin. What Gate A checks is the
quantity that line names, against the module, through **three** oracles: the
retyped screen prototype (§A1), a scalar-loop DFT (§A2) and numpy's complex
`fft` (§A3). Three, not four — §A4's DC-keeping variant is the reading this
port did *not* take, and is priced rather than used as a check.
`tests/test_tf_spec_entropy_64.py::test_the_source_library_is_not_readable_here`
asserts `import tsfel` raises, so this limitation fails loudly if the
environment ever changes rather than sitting here as a stale sentence.

§A4 prices the one reading of that line this port did **not** take.

### §A1 — the screen prototype, bit for bit

The module's arithmetic *is* the prototype's, which is why the screen's Gate E
figure transfers to it.

| frame | bars both define | differing | prototype reads -0.0 |
|---|---|---|---|
| walk | 1,436 | 0 | 1 |
| trend | 1,436 | 0 | 1 |
| range-bound | 1,436 | 0 | 1 |
| grid | 1,436 | 0 | 1 |
| heavy-tailed | 1,436 | 0 | 1 |
| jump | 1,436 | 0 | 1 |
| cycle | 1,436 | 0 | 1 |
| flat | 0 | 0 | 1,437 |
| ramp | 0 | 0 | 137 |
| **TOTAL** | **10,052** | **0** | **1,581** |

At other lengths, over the seven firing frames (NaN masks included in
`differing`):

| length | bars both define | differing |
|---|---|---|
| 4 | 10,472 | 7 |
| 5 | 10,465 | 7 |
| 8 | 10,444 | 7 |
| 20 | 10,360 | 7 |
| 64 | 10,052 | 7 |
| 250 | 8,750 | 7 |

The 7 are one per firing frame and are §A1b's divergence, not a disagreement:
the warm-up bar, where the prototype reads -0.0 and this module reads NaN.

### §A2 — the formula by scalar loops

A DFT built from `cmath.exp` and an entropy built from `math.log2`, sharing no
numpy operation with the module. 200-bar frames, because the oracle is
`O(rows * length^2)` in Python. Masks identical on every frame and length.

| length | max relative difference, over the seven firing frames |
|---|---|
| 8 | 5.804e-16 .. 6.275e-15 |
| 16 | 5.540e-16 .. 3.639e-15 |
| 64 | 8.812e-16 .. 6.476e-15 |

Not bit-equality, and that is the finding rather than a weakness: an FFT sums
the taps in a different order from a naive DFT, so the two cannot agree to the
last bit. The largest figure in each row is the `cycle` frame, whose values sit
near 0.13 and so carry the largest *relative* error for the same absolute one
(max absolute difference anywhere above: 9.992e-16).

### §A3 — the same quantity through numpy's complex `fft`

`np.fft.fft`, keeping bins `1 .. 32`, instead of `np.fft.rfft` — a different
numpy code path for the same transform.

| frame | bars | differing | max relative |
|---|---|---|---|
| walk | 1,436 | 486 | 5.184e-16 |
| trend | 1,436 | 484 | 5.308e-16 |
| range-bound | 1,436 | 466 | 5.159e-16 |
| grid | 1,436 | 490 | 5.254e-16 |
| heavy-tailed | 1,436 | 480 | 5.107e-16 |
| jump | 1,436 | 488 | 5.175e-16 |
| cycle | 1,436 | 783 | 8.022e-16 |

A third of the bars differ in their last bits and none by more than 1e-15; the
largest relative difference anywhere in that table is **8.022e-16**.

⚠ The `differing` COLUMN is CPU-dispatch dependent and the max-relative column
is the claim. The same section under the launcher's reduced dispatch
(`python docs/measure_tf_spec_entropy_64_cpu.py A3`) prints 460 / 438 / 461 /
484 / 472 / 478 / 769 against the 486 / 484 / 466 / 490 / 480 / 488 / 783
above, and its max-relative column reads 5.445e-16 / 5.246e-16 / 5.358e-16 /
5.254e-16 / 5.112e-16 / 5.234e-16 / 8.022e-16 — the same 8.022e-16 ceiling.
Which bars land on the same double is a fact about the kernel; the bound is
the fact about the column.

### §A4 — the reading this port did NOT take

A literal reading of "normalised entropy of the power spectrum" keeps bin 0 and
normalises by `log2(#non-zero probabilities)`. This port drops bin 0 and
normalises by the fixed `log2(length // 2)` — the screen's scale-free form,
and the expression Gate E's prototype figure was measured on. Priced:

| frame | max abs difference | mean difference | Spearman | bins the literal reading used |
|---|---|---|---|---|
| walk | 0.0083 | 0.0037 | 0.9880 | 32 or 33 |
| trend | 0.0083 | 0.0028 | 0.9865 | 32 or 33 |
| range-bound | 0.0083 | 0.0060 | 0.9908 | 32 or 33 |
| grid | 0.0083 | 0.0039 | 0.9867 | 32 or 33 |
| heavy-tailed | 0.0086 | 0.0059 | 0.9916 | 32 or 33 |
| jump | 0.0088 | 0.0038 | 0.9895 | 32 or 33 |
| cycle | 0.0000 | -0.0000 | 1.0000 | 32 |

It is a different column and it is nearly rank-identical, so the choice barely
moves a tree — but the module docstring names which one this is. The "32 or 33"
is the whole mechanism: after the mean is subtracted, bin 0 is the rounding
residue of a cancelling sum, so it is sometimes exactly 0.0 (dropped by
`prob != 0`) and sometimes not, and the normaliser flickers between
`log2(32)` and `log2(33)` from bar to bar.

### §A1b — the two divergences from the prototype, which are the two windows with no spectrum

*(Printed by section **A1**, not by a section A5 — the script's A5 is the
bound, which Gate D leans on and which is tabulated under "§A5 — the bound"
there. This heading is lettered A1b so the preamble's "section letters match
the headings" stays true.)*

The prototype's `P / np.where(s == 0, np.nan, s)` looks like a guard and is
not: the NaN it injects is swallowed by the `p > 0` mask on the next line, and
the window comes out as **-0.0** — a legible entropy reading for a window that
has no spectrum. This port returns NaN, following `tf_centroid_20`,
`maxvol_adv` and `entropy`.

1. **A window holding a non-finite return.** `pct_change` makes bar 0 NaN, so
   every frame has exactly one: bar `length - 1` = 63, the bar before the first
   reading. Measured: 1 such bar on each of the seven firing frames, and the
   prototype's value there is `-0.0` (sign bit checked, not just `== 0.0`).
2. **A window of `length` EQUAL returns.** The centred window is identically
   zero, so `SUM(P)` is 0. On `flat` the prototype fires all 1,437 bars at
   exactly 0.0 and this module fires 0; on `ramp` (returns exactly 1.0) 137 and
   0.

⚠ The guard is EXACT equality to zero, not a dispersion floor, and §A1 prints
the table that shows it. A ramp whose step is not a power of two has returns
that differ in their last bits, so the window is not identically zero and the
column fires:

| ramp | bars | fires | of possible |
|---|---|---|---|
| `step = 1.001` | 1,500 | 1,436 | 1,436 |
| `step = 1.001` | 400 | 336 | 336 |
| `step = 1.0000000001` | 1,500 | **1,294** | 1,436 |
| `step = 2.0` | 200 | **0** | 136 |

("possible" is `bars - 64`: the module's warm-up is `length` bars, one more
than the prototype's, because window 0 holds `pct_change`'s leading NaN.)

The third row is the interesting one and it was not predicted: at a step small
enough that consecutive ratios round to the same double, 142 of the 1,436
windows DO become exactly constant and blank. So "not a power of two" is not
the rule — exact equality of the 64 returns is — which is why the `ramp` frame
uses `step = 2.0` over 200 bars, where the ratio is exact by construction, and
why `test_an_almost_constant_return_is_a_reading_and_not_a_gap` pins the
400-bar `step = 1.001` row (336 of 336).

### §A6 — the return spelling

`close.pct_change(fill_method=None)` is bit-equal to the prototype's
`c / c.shift(1) - 1` on all nine frames.

### §A7 — centring, which is redundant on paper and not in floating point

The mean is subtracted *and* bin 0 is dropped. Dropping the centring and
keeping only the bin drop:

| frame | bars | differing | max relative |
|---|---|---|---|
| walk | 1,436 | 179 | 4.996e-16 |
| trend | 1,436 | 145 | 5.126e-16 |
| range-bound | 1,436 | 212 | 4.783e-16 |
| grid | 1,436 | 167 | 5.254e-16 |
| heavy-tailed | 1,436 | 215 | 5.055e-16 |
| jump | 1,436 | 171 | 5.167e-16 |
| cycle | 1,436 | 0 | 0.000e+00 |

Both steps are kept because both are the prototype's, and the prototype is the
expression the screen measured. The cost of keeping them is 5.254e-16.

⚠ Same caveat as §A3: the `differing` column moves with numpy's CPU dispatch.
Under `python docs/measure_tf_spec_entropy_64_cpu.py A7` it prints 171 / 137 /
235 / 162 / 224 / 186 / 0 against the 179 / 145 / 212 / 167 / 215 / 171 / 0
above — and the same 5.254e-16 ceiling, which is the claim.

---

## Gate B — causality

12 offsets swept per frame (`69 .. 1495`), each by perturbing every bar from
`j` onward two ways and comparing the prefix below `j` bit for bit.

* **The real module: caught 0 of 12 on each of the seven firing frames.**
* Prefix truncation: the first `j` bars of the column equal the column computed
  on the first `j` bars alone, at every offset (asserted in the test module).

Five mutants, each read off `pandas_ta/statistics/tf_spec_entropy_64.py`,
edited and `exec`'d in memory, so none can drift from the code it claims to
edit:

| mutant | what it does | live | caught, each of 7 frames |
|---|---|---|---|
| `return-lead` | `close.shift(-1).pct_change(...)` | yes | 12 / 12 |
| `output-early` | write index `length - 2 + a` instead of `length - 1 + a` | yes | 12 / 12 |
| `window-ahead` | `sliding_window_view(np.roll(r, -1), length)` | yes | 12 / 12 |
| `window-centred` | `np.roll(r, -(length // 2))` — the `bos` failure mode | yes | 12 / 12 |
| `mask-shifted` | `np.roll(ok, -1)`, back-dating the GAP mask | yes | **0 / 12** |

### §B2 — the mutant the blind sweep cannot see

`mask-shifted` is live on every frame and the sweep misses it on every one,
because the bars it moves do not depend on the future. That is exactly what
CLAUDE.md's Gate B says prefix work cannot see, so it is pinned directly:
plant one NaN close and read where the gap lands.

| NaN planted at | real gap | mutant gap | mutant ⊇ real - 1 | extra |
|---|---|---|---|---|
| 200 | 200..264 | 199..263 | yes | 264, 1499 |
| 400 | 400..464 | 399..463 | yes | 464, 1499 |
| 700 | 700..764 | 699..763 | yes | 764, 1499 |
| 1000 | 1000..1064 | 999..1063 | yes | 1064, 1499 |

The mutant's gap is the real one shifted one bar EARLIER, plus the last bar of
the frame, where `np.roll` wraps the warm-up's `False` round to the end.

### How far each live mutant back-dates the column (walk, 1,500 bars)

| mutant | best match | bars bit-equal there |
|---|---|---|
| `return-lead` | 1-bar back-date | 1,435 |
| `output-early` | 1-bar back-date | 1,436 |
| `window-ahead` | 1-bar back-date | 1,436 |
| `window-centred` | none | 0 |
| `mask-shifted` | 0-bar | 1,435 |

---

## Gate C — reachability

⚠ **Synthetic only in this session. The real-data limb is owed with the Gate E
run** (`Gate E: pending, run by issue-solver after this session`), and the
receipt session records it.

| frame | bars | fired | distinct | mean | min | max |
|---|---|---|---|---|---|---|
| walk | 1,500 | 1,436 | 1,436 | 0.8837 | 0.8015 | 0.9436 |
| trend | 1,500 | 1,436 | 1,436 | 0.8825 | 0.7905 | 0.9441 |
| range-bound | 1,500 | 1,436 | 1,436 | 0.8827 | 0.7814 | 0.9415 |
| grid | 1,500 | 1,436 | 1,436 | 0.8820 | 0.7715 | 0.9393 |
| heavy-tailed | 1,500 | 1,436 | 1,436 | 0.8958 | 0.8194 | 0.9823 |
| jump | 1,500 | 1,436 | 1,436 | 0.8854 | 0.8000 | 0.9960 |
| cycle | 1,500 | 1,436 | 1,436 | 0.1364 | 0.0836 | 0.1886 |
| flat | 1,500 | 0 | — | — | — | — |
| ramp | 200 | 0 | — | — | — | — |

Warm-up: the first fired bar is 64 on each firing frame — `length` returns need
`length + 1` closes, so the first reading is at bar `length`, not `length - 1`.
65 closes produce exactly 1 bar; 64 closes return `None` (`verify_series`).

---

## Gate D — scale-free

### Exact binary factors: bit-identical

`(k*a) / (k*b)` is exactly `a / b` for a power of two `k`, so the returns — and
every later bit — are unchanged. Bit-identical on all seven firing frames at
**x8, x64, 2**-40, 2**40 and 2**100**, and under x8 at `length`
**4, 5, 8, 20, 64 and 250**.

### Inexact factors: a tolerance, and the number

Max relative move, NaN masks identical in every cell:

| frame | x10 | x3.7 | x0.1 | x1.0000001 |
|---|---|---|---|---|
| walk | 2.111e-15 | 2.528e-15 | 2.097e-15 | 2.520e-15 |
| trend | 3.217e-15 | 3.431e-15 | 2.904e-15 | 2.915e-15 |
| range-bound | 1.084e-15 | 1.486e-15 | 1.426e-15 | 1.319e-15 |
| grid | 2.152e-15 | 2.686e-15 | 2.139e-15 | 2.324e-15 |
| heavy-tailed | 1.955e-15 | 2.012e-15 | 2.421e-15 | 2.692e-15 |
| jump | 2.309e-15 | 2.457e-15 | 2.036e-15 | 2.496e-15 |
| cycle | 2.986e-14 | 3.090e-14 | 2.883e-14 | 2.877e-14 |

Largest anywhere: **3.090e-14**, on `cycle`, whose values are an order of
magnitude smaller than the others' and so carry the largest relative error for
the same absolute one.

### `0 < fires < n`, and the column is not constant

1,436 of 1,500 on each of the seven firing frames, with 1,436 distinct values
on each — so no bit-identity above can be passing because the column is flat.

### A level shift is not a rescale, and it moves the column

| shift | bars that differ | max abs difference |
|---|---|---|
| +1 | 1,436 of 1,436 | 1.989e-04 |
| +50 | 1,436 of 1,436 | 4.894e-03 |
| +1e6 | 1,436 of 1,436 | 9.441e-03 |

### §A5 — the bound, which Gate D also rests on

| frame | min | max | excess over 1.0 |
|---|---|---|---|
| walk | 0.801496 | 0.943625 | 0.000e+00 |
| trend | 0.790531 | 0.944116 | 0.000e+00 |
| range-bound | 0.781424 | 0.941486 | 0.000e+00 |
| grid | 0.771510 | 0.939273 | 0.000e+00 |
| heavy-tailed | 0.819437 | 0.982303 | 0.000e+00 |
| jump | 0.799994 | 0.996021 | 0.000e+00 |
| cycle | 0.083650 | 0.188560 | 0.000e+00 |

Both ends, by construction: a pure sinusoid exactly on bin 1, 2, 8 or 16 reads
**1.309e-27 .. 3.311e-25** (per bin: 2.131e-27 .. 5.902e-27, 2.582e-27 ..
1.106e-26, 1.309e-27 .. 9.271e-26, 1.653e-27 .. 3.311e-25) and reaches exactly
0.0 on **0** bars; white-noise
returns over five seeds reach a maximum of **0.960099** and never 1.0. ⚠ A
consumer must not test this column for equality with 0 or with 1.

⚠ The sinusoid figure is sensitive to how the frame is BUILT. A close path
`level * exp(cumsum(r))` has returns `exp(r) - 1`, not `r`, and the harmonics
of that distortion put 2.341e-05 of entropy into a single-sine frame against
the 1e-27 a `cumprod(1 + r)` path gives. Both are measured; the test module
uses the `cumprod` builder.

---

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

No row in `docs/gate_e_ledger.csv`, so
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally and skips in CI (`GATE_E_PENDING_OK=1`).
`tests/test_tf_spec_entropy_64.py::test_the_gate_e_row_is_owed_and_not_yet_recorded`
asserts the row's absence, which is the receipt session's cue to replace it
with one pinning the recorded row's identity.

What the 2026-10-24 screen measured, **on the prototype and not on this
module** (run `screen_r2_20261024`, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 comparators, canary bit-equal):

* max |ρ| **0.0284** vs `Supertrend_Flip_Age`, n = 393,242; top-5 per-frame max
  median 0.0578 → **SHIP** under `r3-perframe-0.90`.
* Next comparators: `VOL_SMA_20` 0.0257, `Volume` 0.0255.
* Stage-2 fork overlap (not Gate E; scale-free `Category` outputs at defaults,
  12 frames): max |ρ| 0.0497 vs `covariance:COV_30_1`, per-frame max median
  0.0550.

§A1 measures this module bit-equal to that prototype on every bar both define,
so the run on the port is expected to reproduce those digits — which is exactly
why the receipt session must pin the row's *identity* and not only its
arithmetic.

---

## Gate F — suites

* `tests/test_tf_spec_entropy_64.py`: **257 passed**.
* The same 257 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`,
  via `python docs/measure_tf_spec_entropy_64_cpu.py`, which refuses to run
  unless the dispatch actually took. ⚠ It prints the dispatchable features
  still enabled (`SSSE3 SSE41 POPCNT SSE42 AVX F16C AVX512CD AVX512_CLX
  AVX512_CNL AVX512_ICL` on this machine), so "reduced dispatch" cannot be read
  as "no vector kernels".
* Full suite: recorded in the commit message.

---

## §G — guards

A bad close planted at one bar of a 1,500-bar walk. `emptied` is how many bars
that fired on the clean frame stop firing; `earlier moved` counts every bar
below the planted one whose value or NaN status changed.

| planted | at bar 0 | 1 | 64 | 700 | 1499 | earlier moved, any |
|---|---|---|---|---|---|---|
| `nan` | 1 | 2 | 65 | 65 | 1 | 0 |
| `inf` | 0 | 1 | 64 | 64 | 1 | 0 |
| `-inf` | 0 | 1 | 64 | 64 | 1 | 0 |
| `0.0` | 1 | 2 | 64 | 64 | 0 | 0 |
| `-1.0` | 0 | 0 | 0 | 0 | 0 | 0 |
| `1e-310` | 1 | 2 | 64 | 64 | 0 | 0 |

Three things in that table are worth saying out loud.

1. **The guard is on the RETURN, not on the close.** A NaN close makes two
   returns NaN (its own and the next bar's) and so empties 65 windows; an
   infinite or zero close makes one of them non-finite and empties 64.
2. **A NEGATIVE close is read, not masked** — it produces a perfectly finite
   return. It empties nothing and moves 64 bars. Worth knowing before feeding
   this a spread or an already-differenced series.
3. **Nothing earlier than the planted bar ever moves**, over all 30 (value,
   position) pairs.

Degenerate whole frames: all-NaN fires 0 of 1,500, all-zero fires 0 of 1,500,
all-negative fires 1,436 of 1,500.

**No floating-point error is reachable.** Every one of the nine frames and all
30 planted-bad-value pairs run clean under `np.errstate(all="raise")`.
⚠ That required a change: without the `np.isfinite` fold on the returns, the
`inf` pairs raise `invalid value encountered in subtract` at
`win - win.mean(...)` — `inf - inf`. Measured before the fold was added, which
is why the fold is there.

The input series is not mutated. A `length` below `MIN_LENGTH` (4) — `None`,
0, 1, 2, 3 — falls back to 64, because at `length` 2 and 3 the normaliser
`log2(length // 2)` is `log2(1) = 0` and every window would be 0/0.

---

## §L — what the column reads

| frame | mean | sd | p05 | p95 |
|---|---|---|---|---|
| walk | 0.8837 | 0.0260 | 0.8394 | 0.9240 |
| trend | 0.8825 | 0.0240 | 0.8422 | 0.9190 |
| range-bound | 0.8827 | 0.0265 | 0.8337 | 0.9235 |
| grid | 0.8820 | 0.0257 | 0.8380 | 0.9197 |
| heavy-tailed | 0.8958 | 0.0290 | 0.8492 | 0.9391 |
| jump | 0.8854 | 0.0348 | 0.8339 | 0.9376 |
| cycle | 0.1364 | 0.0223 | 0.1000 | 0.1727 |

⚠ **A narrow band near the top of the range.** On everything except the
planted-cycle frame the column sits between 0.77 and 1.00, with an sd under
0.035. A model that reads raw distances will see almost nothing in it; it wants
ranking or scaling first. What separates `cycle` from the rest is not noise but
a dominant frequency, and that is the signal this column exists to carry.

### §L2 — the leakage artefact, which is the main thing to know

There is no window function, because TSFEL applies none and neither does this
port. A cycle whose period does not divide `length` leaks across the bins:

| returns | mean | min |
|---|---|---|
| one sinusoid on bin 8 | 0.0000 | 1.3092e-27 |
| the same at bin 8.25 | 0.2429 | 0.22795 |
| the same at bin 8.5 | 0.4303 | 0.41555 |

A model reading this column is reading *on-grid-ness* as well as entropy.

### §L3 — blind to the sign and the size of the returns

On the arithmetic, with the return window scaled directly:

| factor | bit-equal | max relative |
|---|---|---|
| x-1 | yes | 0.000e+00 |
| x0.5 | yes | 0.000e+00 |
| x2 | yes | 0.000e+00 |
| x-3.7 | no | 5.109e-16 |
| x1e6 | no | 5.184e-16 |

So the column carries no direction and no size — it is not a volatility
measure. ⚠ Through a close path rebuilt from scaled returns the equality is
only approximate (1,202 bars differ by up to 2.665e-15 under x-1), because
rebuilding and re-differencing rounds; that is a fact about the rebuild, not
about the column.

### §L5 — what the magnitude spectrum throws away

`abs(rfft(.))` has no phase. Over 2,000 random 64-return windows of one walk.

⚠ §L3 and §L5 read `_entropy_of_rows`, a copy of the module's arithmetic
applied to an explicit block of windows, because a claim about rotating or
scaling a WINDOW cannot go through a close path — rebuilding one from altered
returns and differencing it again rounds (the second table in §L3 is exactly
that effect). A copy that only *claims* to be the module's arithmetic is worth
nothing, so §L3 prints the pin first: `_entropy_of_rows` over the trailing
windows is bit-equal to `tf_spec_entropy_64` on each of the seven firing
frames, and `tests/test_tf_spec_entropy_64.py::test_the_row_helper_is_the_modules_arithmetic`
asserts the same thing.

| transformation | bit-equal | max abs difference |
|---|---|---|
| circular rotation | 1,307 / 2,000 | 4.441e-16 |
| time reversal | 1,332 / 2,000 | 4.441e-16 |
| general permutation | 0 / 2,000 | **1.354e-01** |

So the column cannot say WHERE in the window a pattern sat or which way round
it ran — but it is **phase-blind, not order-blind**: a permutation is not an
`abs(rfft(.))` symmetry and does move it.

### §L4 — against the fork's own entropy and spectrum columns

Absolute Spearman, synthetic frames only:

| comparator | walk | trend | range-bound | grid | heavy-tailed | jump | cycle |
|---|---|---|---|---|---|---|---|
| `entropy` (10) | 0.1508 | 0.0955 | 0.0452 | 0.1660 | 0.1520 | 0.0762 | 0.0364 |
| `entlz` | 0.0546 | 0.0049 | 0.0828 | 0.0307 | 0.0071 | 0.1324 | 0.0119 |
| `ts_binent_20` | 0.0143 | 0.0379 | 0.0471 | 0.1626 | 0.0403 | 0.0244 | 0.0114 |
| `ts_perment_20` | 0.0081 | 0.0350 | 0.1294 | 0.0528 | 0.0886 | 0.1530 | 0.0204 |
| `tf_centroid_20` | 0.1302 | 0.0021 | 0.0084 | 0.0420 | 0.0247 | 0.0598 | 0.0179 |

The fork already ships four entropies — Shannon on binned closes (`entropy`),
Lempel-Ziv (`entlz`, issue #11, the issue names it as related), binned
(`ts_binent_20`) and permutation (`ts_perment_20`) — and none of them is this
one on these frames. ⚠ All synthetic: the 687 Gate E comparators are the
engine's and hold no pandas_ta port, so the only real-data bound on the fork's
own columns is the screen's stage-2 fork sweep (0.0497 over 12 frames).

---

## §Z — cost, on 400,000 bars

**The peak columns and the monotone ordering are the claims. The seconds are
not: they are one significant figure and they still move.**

| length | ⚠ best of 3 (s), 1 s.f. | peak, chunked (MB) | peak, one block (MB) |
|---|---|---|---|
| 4 | 0.06 | 48.9 | 48.9 |
| 20 | 0.2 | 58.7 | 205.7 |
| 64 | 0.2 | 58.1 | 636.8 |
| 250 | 1 | 57.9 | 2,458.1 |

The peaks reproduce to the tenth on every invocation so far, on this worktree
and in two reviewers'. The seconds do not reproduce to two significant
figures: six runs printed `length` 64 at 0.244, 0.237, 0.249, 0.268, 0.247
and 0.241, which is why the column is cut to one.

The transform has to materialise a `(rows, length)` copy — the spectrum reads
the whole window, so a window inherits nothing from its neighbour — and without
`CHUNK_VALUES` the peak grows with `len(close) * length`: 2.4 GB at `length`
250. With it the peak is flat at about 58 MB. The budget cannot change a value:
bit-identical at 1, 64, 999 and 10\*\*9.

⚠ The time ratio is the same kind of number. `length` 250 costs **about 17x**
`length` 4; six invocations of this section printed 16.49x, 17.15x, 17.22x,
17.40x, 17.13x and 17.10x — three here and three in reviewers' runs. The
ordering,
monotone in `length`, and the peak are the claims; no wall-clock figure is
quoted outside this section.

---

## §M / §W — the wiring the generated docs carry

* `docs/IndicatorDictionary.md`, regenerated: exactly one new row,
  `` `tf_spec_entropy_64` | C | `length=None` | `TFSPECENT_64` SF | 64 ``, and
  the three counts move 350 → 351 probed, 348 → 349 in `Category`,
  356 → 357 accessors.
* `docs/MLCompanionContract.md`: the running tally gains one clause,
  693 → 694 tagged columns and 332 → 333 `SF`. ⚠ Those absolute totals come
  from a parse `docs/measure_tf_spec_entropy_64.py` does not reproduce; what
  section M checks is the DELTA, which is the one dictionary row above.
* The user-facing docstring's first paragraph is 138 characters and survives
  `gen_indicator_dictionary.desc()` whole, with **12 characters of slack**.
  That cut is not 150 characters: it is `d[:150].rsplit(" ", 1)[0]`, which
  drops the trailing word entirely. Re-run section W before lengthening it.
