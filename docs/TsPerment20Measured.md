# `ts_perment_20` — measured

Issue #91 (TS-PERMENT-20), ported 2026-11-12 on branch `issue-91-ts-perment-20`.
Column: **`TS_PERMENT_20_3`**, `pandas_ta/statistics/ts_perment_20.py`.
**Status: SHIPPED through Gates A–F.** Gates A–D were cleared in the porting
session; the launcher ran Gate E on the committed code afterwards (run
`is91-ts_perment_20-cff57e6c`, measured 2026-11-12) and this receipt session
wrote its numbers into the *Gate E* and *Gate C* sections below and recorded
the ledger row in `docs/gate_e_ledger.csv`. The single column
`TS_PERMENT_20_3` is **SHIP**: pooled max \|ρ\| **0.2848** vs `inertia`, well
under the 0.76 ship line.

Every number here is printed by `python docs/measure_ts_perment_20.py` (its
sections can be run one at a time, e.g. `… gate_b`) on pandas 2.3.3 / numpy
1.26.4, or by `python -m pytest tests/test_ts_perment_20.py -q`. Nothing in
this file was typed from expectation; where a number is *not* measured, the
line says so.

⚠ **Spearman figures and last-bit counts here are this machine's.** CI's
runner has measured the third decimal differently for the same seeds on the
same pandas/numpy/scipy (commit 22fe27b moved `ts_binent_20`'s 0.651029 to
0.648490), because the generated frames themselves differ in their last bits.
That is why `tests/test_ts_perment_20.py` pins correlations with a tolerance
(`abs=0.02`–`0.05`) and pins the *relations* where a count is CPU-dependent.

The two bit-equality claims in this file are **not** the same kind of claim:

* **Gate D's 1481/1481 is structural.** A monotone transform leaves every
  `<=` unchanged, so both runs execute identical arithmetic on identical
  integers; there is no rounding for a libm to disagree about.
* **Gate A3's 581/581 is an equality between two float pipelines** — the
  module's six `h -= p*log(p)` subtractions over an `(n,)` array against the
  oracle's `-np.sum(...)` over a `(<=6,)` one. It holds because the module
  accumulates in `np.unique`'s order (§A3), and §A4 measures what a mere
  reordering of the same terms costs: 4.44e-16. So it is a measurement on
  this machine, not an arithmetic guarantee: a numpy whose `log` takes a
  different SIMD path for the two array shapes could lose a last bit. What
  the test pins exactly is the portable half — 0 bars differing by more than
  1e-12, which is about three orders of margin over that 4.44e-16, plus
  max \|diff\| under 1e-14, which is about 20× it. The 581/581 count is
  pinned at `>= 579`, and that slack is **only** worth a one- or two-bar
  drift: §A3 measures that reordering the same six terms and changing
  nothing else moves **249–274 of 581 bars** on four frames, so a libm that
  really disagreed about `log` across call shapes would move hundreds and
  SHOULD fail this test rather than be absorbed by it.

## What it is

    code[T] = 4*(c[T-2] <= c[T-1]) + 2*(c[T-1] <= c[T]) + (c[T-2] <= c[T])
    p[k]    = (count of code == k over the window's `length - 2` triples)
              / (length - 2)
    column  = -sum(p * log p) over the six realisable codes

At the default (`length=20`; dimension 3 and tau 1 are fixed by the issue):
Bandt-Pompe permutation entropy of the 18 three-close triples inside a
20-close window, in nats, unnormalised. The window reads 20 closes and the
first value lands at bar 19.

The column reads **how ordered the recent path is** — 0.0 when every triple
reads the same way, the ceiling when the six orderings are equally common. It
is an ordinal statistic: it reads only the ORDER of the closes, never a
difference, a ratio or a sum.

Three consequences, measured below, that a consumer is likely to get wrong:

* **0.0 is both the flat window and the monotone one** (§Gate A, A6). A tie is
  broken by index, so it reads as a rise; 20 identical closes and 20 strictly
  rising closes are the same value.
* **Magnitude is invisible** (§What it reads). A +10, +50 and +1000 sigma
  spike at the same bar give a bit-identical column.
* **Price granularity is an input** (§The tie rule). The same path on a coarse
  grid is Spearman 0.3796 against the unrounded one.

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue's line is `permutation_entropy(tau=1, dimension=3) on 20 closes`,
sourced to tsfresh `feature_calculators` (MIT). **tsfresh is not installed in
this worktree** — `import tsfresh.feature_extraction.feature_calculators`
raises `ModuleNotFoundError` (measured, §source) — and web access is not
available to this session, so the attribution is an attribution and not an
oracle. Anything tsfresh does that the issue's line does not state (how it
treats a series shorter than `dimension`, whether it drops NaNs rather than
returning NaN, whether it normalises) is **unverified here**.

What IS independently checkable is the DEFINITION of the ordinal pattern, and
it is checked four ways in §Gate A: the 3-bit code is a bijection with
`argsort(argsort(x))` over every weak order on three points; tsfresh's own
spelling (`np.unique` over those rank vectors, then `-sum(p log p)`) is
**bit-equal** to the module; seven hand-derived windows have an exact closed
form; and a plain-Python scalar loop agrees to 4.44e-16.

## ⚠ The port is not the column the screen measured

The screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_perment_20`, local to the owner's machine) is:

    def perm_entropy3(x, n):
        a, b, c = x.shift(2), x.shift(1), x
        pid = (4*(a < b) + 2*(b < c) + 1*(a < c)).where(a.notna() & c.notna())
        h = pd.Series(0.0, index=x.index)
        for k in (0, 1, 3, 4, 6, 7):                 # "the 6 realisable patterns"
            p = (pid == k).astype(float).rolling(n - 2).mean()
            h -= np.where(p > 0, p * np.log(p.where(p > 0, 1)), 0)
        return (h / np.log(6)).where(pid.rolling(n - 2).count() == n - 2)

**That loop is wrong about which codes are realisable.** Exhaustively over all
27 triples of values drawn from `{1, 2, 3}` — which realises every weak order
on three elements, ties included — the codes that occur are
**{0, 2, 3, 4, 5, 7}** and the codes that never occur are **{1, 6}**: 6 would
need `a < b < c` together with `a >= c`, and 1 would need `a >= b >= c`
together with `a < c`. The prototype visits those two impossible codes and
**skips the realisable 2 and 5**, which hold **25.90%** of a 1,500-bar walk's
triples (per-code shares, measured: 0 → 0.2383, 2 → 0.1328, 3 → 0.1202,
4 → 0.1275, 5 → 0.1262, 7 → 0.2550). So the prototype is a FOUR-pattern sum,
and it is not a rescaling of the six-pattern one.

`CLAUDE.md` is explicit that *"Gate A starts from the source formula, not the
prototype"*, so this port ships the six-pattern Bandt-Pompe form. Measured,
port against the retyped prototype, 1,481 shared bars (NaN masks equal on all
three frames):

| frame | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|
| gaussian walk | 1.148161 | 0/1481 | **0.548665** |
| tick-rounded walk | 1.254004 | 0/1481 | **0.481738** |
| coarse grid (46% tied triples) | 1.411393 | 0/1481 | **−0.029641** |

Dividing the port by `log 6` (the prototype's normalisation) does not
reconcile them either: 2 of 1,481 bars bit-equal on the walk, 0 on the other
two, same Spearman.

The retyped prototype is **bit-equal to the screen's own registry entry** —
`REG["ts_perment_20"]["fn"]` imported out of the owner's gitignored tree —
on 1,481 of 1,481 bars of each of the three frames, so the comparison above
is against the code the screen ran and not a paraphrase of it.

**Consequence for Gate E.** Issue #91's screen numbers (max \|ρ\| 0.2046 vs
`psl`, top-5 per-frame max median 0.1715, SHIP) were measured on the
four-pattern prototype and do **not** transfer to this port, which correlates
0.55 with it. The launcher re-ran Gate E on the shipped module, and the §Gate E
numbers below are that run: the port's own figure is **0.2848 vs `inertia`**,
not 0.2046 vs `psl`. Both land SHIP, but they are different measurements of
different columns and the issue's must not be quoted for this port.

## Gate A — correctness

### A1. Hand-derived windows

Seven windows whose pattern counts are known by hand. "accumulated" is the
closed form summed the way the module sums it, one ordering at a time; the
module must land exactly on it.

| window (length) | counts | accumulated | module | closed form, ulps away |
|---|---|---|---|---|
| 20 strictly rising closes | one ordering × 18 | 0.0 | **0.0 away** | 0, 0 ulps |
| 20 identical closes | one ordering × 18 | 0.0 | **0.0 away** | 0, 0 ulps |
| 20 strictly falling closes | one ordering × 18 | 0.0 | **0.0 away** | 0, 0 ulps |
| zigzag 100/101 (20) | 9 + 9 | 0.6931471805599453 | **0.0 away** | `log 2`, 0 ulps |
| the even-split witness (20) | 3 × 6 | 1.7917594692280547 | **0.0 away** | `log 6`, **1 ulp above** |
| `[1,3,2,4]` (4) | 1 + 1 | 0.6931471805599453 | **0.0 away** | `log 2`, 0 ulps |
| `[1,3,2,4,5]` (5) | 1 + 1 + 1 | 1.0986122886681096 | **0.0 away** | `log 3`, **1 ulp above** |

The ceiling is therefore **1.7917594692280547**, one ulp BELOW
`math.log(6)` = 1.791759469228055: the six terms are accumulated separately,
so `value <= log 6` holds but `value == log 6` never does. It is **attained**,
not approached — the witness is a real 20-close window, found after 12
shuffles at seed 2026 and pinned as a constant in the test module:

    [20, 4, 8, 17, 13, 5, 2, 14, 6, 10, 11, 9, 1, 15, 7, 12, 3, 18, 19, 16]

### A2. The screen prototype

See *The port is not the column the screen measured* above: deliberately
different, measured on three frames, and bit-equal between the retyped and
the imported prototype.

### A3. tsfresh's own spelling, bit for bit

`argsort(argsort(X))` over the 18 subchunks, `np.unique(..., axis=0,
return_counts=True)`, `-sum(probs * log probs)` — window by window, sharing no
code with the module. 600-bar frames, 581 fired bars:

| frame | max \|diff\| | bit-equal | NaN masks |
|---|---|---|---|
| gaussian walk | 0.000000e+00 | **581/581** | equal |
| tick-rounded walk | 0.000000e+00 | **581/581** | equal |
| coarse grid (ties everywhere) | 0.000000e+00 | **581/581** | equal |
| two-point returns | 0.000000e+00 | **581/581** | equal |

Bit-equality is **earned, not luck**: the module accumulates the six terms in
the order `np.unique` returns the rank vectors — sorted, which is codes
`7, 5, 3, 4, 2, 0` — and `PATTERNS` in the module is fixed in that order for
exactly this reason. Accumulating in code order instead (`0, 2, 3, 4, 5, 7`)
keeps every count, changes nothing else, and still moves the last bit on a
quarter of the bars:

| frame | max \|diff\| | bit-equal | bars moved | bars \|diff\| > 1e-12 |
|---|---|---|---|---|
| gaussian walk | 4.440892e-16 | 325/581 | **256** | 0 |
| tick-rounded walk | 4.440892e-16 | 319/581 | **262** | 0 |
| coarse grid | 4.440892e-16 | 307/581 | **274** | 0 |
| two-point returns | 4.440892e-16 | 332/581 | **249** | 0 |

`test_the_accumulation_order_is_the_sources_own` pins the order itself (same
value to 1e-12, a non-zero number of differing bars).

⚠ This is an equality of two different float pipelines, so it is a
**measurement on this machine and not an arithmetic guarantee** — see the ⚠ at
the top of this file. The portable half of the claim (0 bars differing by more
than 1e-12) is what the test pins exactly; the 581/581 is pinned at `>= 579`,
which is slack for a one- or two-bar drift and nothing more.

### A4. An independent plain-Python scalar loop

A third implementation, sorting `(value, position)` pairs and accumulating in
FIRST-OCCURRENCE order. 600-bar frames, 581 fired bars:

| frame | max \|diff\| | bars \|diff\| > 1e-12 | bit-equal | Spearman |
|---|---|---|---|---|
| gaussian walk | 4.440892e-16 | **0** | 346/581 | 0.999187 |
| tick-rounded walk | 4.440892e-16 | **0** | 335/581 | 0.999392 |
| coarse grid | 4.440892e-16 | **0** | 358/581 | 0.999700 |

Spearman is 0.999 rather than 1.000 *because* the column is a coarse count
statistic: a last-bit difference re-orders values that are equal to 1e-12. It
is not a disagreement about any distinct value — 0 bars differ by more than
1e-12 on all three frames.

### A5. The five open readings, decided and priced

1,500-bar frames, 1,481 shared bars (the window reading loses 2 bars, the
returns reading 1):

| reading, and what this port does | frame | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|---|
| **SIX realisable orderings.** Rejected: the prototype's four | walk | 0.722019 | 2/1481 | 0.548667 |
| | tick-rounded | 0.690054 | 0/1481 | 0.481095 |
| | coarse grid | 0.668479 | 5/1481 | 0.606731 |
| **nats, unnormalised** (tsfresh's). Rejected: ÷ `log 6` (the prototype's) | walk | 0.783418 | 0/1481 | **1.000000** |
| | tick-rounded | 0.791759 | 0/1481 | **1.000000** |
| | coarse grid | 0.791759 | 0/1481 | **1.000000** |
| **ties broken by INDEX** (`<=`, what `argsort` does). Rejected: strict `<` | walk | 0.000000 | **1481/1481** | 1.000000 |
| | tick-rounded | 0.172910 | 1377/1481 | 0.979533 |
| | coarse grid | 0.865435 | 19/1481 | **0.038409** |
| **the window is 20 CLOSES** (18 triples). Rejected: 20 triples (22 closes) | walk | 0.306010 | 0/1479 | 0.889513 |
| | tick-rounded | 0.272040 | 0/1479 | 0.906333 |
| | coarse grid | 0.316619 | 0/1479 | 0.928736 |
| **the input is CLOSES** (the issue's wording). Rejected: the 19 returns | walk | 1.116495 | 39/1480 | 0.131103 |
| | tick-rounded | 0.935110 | 44/1480 | −0.053797 |
| | coarse grid | 0.989403 | 20/1480 | 0.060025 |

Reading them in order of what they cost:

* The **pattern set** is the decision that matters most, and it is not a
  judgement call: two of the prototype's codes are provably unrealisable and
  two realisable ones are missing.
* The **normalisation** is the only one a rank miner cannot see (Spearman
  exactly 1.000000). The port follows tsfresh and leaves the value in nats,
  with the ceiling `log 6` rather than 1.
* The **tie rule** is free on continuous prices and decisive on coarse ones —
  see *The tie rule* below.
* The **window** reading is a smoothing choice worth 0.89–0.93 Spearman; the
  issue says "on 20 closes", so 18 triples it is.
* The **input** reading is not interchangeable at all (\|Spearman\| ≤ 0.14).
  This fork's return-based tsfresh ports are `ts_binent_20` and `ts_c3_20`;
  this one reads closes.

### A6. The degenerate window: 0.0, not NaN

| frame | fires | of those, exactly 0.0 | the NaN-on-degenerate variant fires |
|---|---|---|---|
| flat 300 closes | 281/300 | **281** | 0/300 |
| monotone 300 closes (rising 0.5 a bar) | 281/300 | **281** | 0/300 |
| 1,500-bar walk | 1481/1500 | **0** | 1481/1500 |

The source's reading is 0.0: one ordering holds all the mass, and the entropy
of a one-bin histogram is 0. The port keeps it, and the cost is that **a flat
window and a monotone one are the same number** — the first value of each is
exactly 0.0. A NaN-on-degenerate variant would be a different column and is
not what the issue asked for; it is recorded here so the choice is visible.

## The tie rule

Ties are broken by INDEX — the earlier close counts as the smaller — because
that is what the installed numpy's `argsort(argsort(x))` does on a 3-element
array, measured exhaustively over all 27 triples rather than assumed, and
therefore what tsfresh's `argsort` spelling does *if* that is its spelling:
tsfresh is not installed here (see §Source), and `argsort`'s default `kind` is
not documented as stable. The prototype folds them the other way, with a
strict `<`.

| frame | triples holding a tie | bit-equal to the strict-`<` reading | Spearman |
|---|---|---|---|
| gaussian walk | **0.00%** (0 of 1498) | **1481/1481** | 1.000000 |
| tick-rounded walk (2 decimals, σ 1.5%) | 0.67% (10 of 1498) | 1377/1481 | 0.979533 |
| **coarse grid** (1 decimal, σ 0.2%) | **46.33%** (694 of 1498) | 19/1481 | **0.038409** |
| heavy-tailed / mean-reverting / trending / two-point | 0.00% each | — | — |

So the rule looks cosmetic and is not: on a thin or low-priced instrument
whose closes repeat, the column is largely *about* the tie convention. The
same path rounded onto that coarse grid is Spearman **0.379642** against the
unrounded path (98 of 1,481 bars bit-equal), while rounding a 1.5%-σ walk to
two decimals costs almost nothing (Spearman 0.991236, 1,443 of 1,481
bit-equal). **Price granularity is an input to this column**, and that belongs
in a reader's hands before they compare it across instruments.

## Gate B — causality, by mutant

37 offsets, J = 40 … 1480 step 40. At each J every bar from J onward is
replaced by a different path; a "hit" means a bar STRICTLY BEFORE J moved.
Prefix truncation alone cannot see back-dating, which is why this is a
perturbation sweep.

Five mutants, each `importlib`-read from the module's own source and `exec`'d
in memory. They cover **two mechanisms**, not five: rolling the code array
forward by k is the same as writing the column k bars early (except for the k
wrapped windows at the tail, which `np.roll` fills from the head of the
series), so four of them are the write index back-dated by four distances, and
only `forward_leg` changes how a triple is built.

| mutant | what it does | mechanism |
|---|---|---|
| `forward_triple` | the window rolled ONE triple into the future | write index 1 bar early |
| `back_date_two` | the column written 2 bars early | write index 2 bars early |
| `rolled_window` | the window rolled `length // 2` triples into the future | write index `length // 2` bars early |
| `back_date_full` | the column written `length - 1` bars early | write index `length − 1` bars early |
| `forward_leg` | the newest leg of every triple taken one bar early (`np.roll(c, -1)`) | the triple itself reads ahead |

⚠ At `length=4` the second and third coincide (`length // 2 == 2`), which is
why their rows below are identical — 22/37 with the same missed offsets — and
that cell is **one** measurement, not two.

| | walk | tick-rounded | heavy-tailed |
|---|---|---|---|
| **real module** | **0/37** | **0/37** | **0/37** |
| `back_date_two` | 31/37 | 32/37 | 23/37 |
| `back_date_full` | **37/37** | **37/37** | **37/37** |
| `forward_leg` | 18/37 | 17/37 | 19/37 |
| `rolled_window` | **37/37** | **37/37** | **37/37** |
| `forward_triple` | 20/37 | 21/37 | 15/37 |

The same five on the walk at three non-default lengths. The real module leaks
**0/37** at each, and its first value lands at bar `length - 1` (9, 59, 3):

| setting | real | back-date 2 | back-date `length−1` | forward leg | rolled window | forward triple |
|---|---|---|---|---|---|---|
| `length=10` | **0/37** | 29/37 | **37/37** | 15/37 | **37/37** | 20/37 |
| `length=60` | **0/37** | 30/37 | **37/37** | 21/37 | 36/37 | 20/37 |
| `length=4` | **0/37** | 22/37 | 25/37 | 7/37 | 22/37 | 11/37 |

⚠ **The catch rate is 15–32 of 37 for the three one- and two-bar leaks at the
default length, and 7–37 across all six configurations in the two tables
above** — the floor is `forward_leg` at `length=4` (7/37), where a window
holds two triples. The two whole-window leaks (`back_date_full`,
`rolled_window`) are caught at 36–37 of 37 at every length but 4, where they
fall to 22–25/37 as well.
That is a property of an ORDINAL column rather than a hole in the module:
a perturbation is invisible unless it flips an order relation. A whole-window
leak moves so much that almost every offset sees it; a one- or two-bar leak
does not. The catch rate falls with the window — at `length=4` a window holds
two triples, so there is very little for a perturbation to disturb.

**The mechanism is measured, not excused.** `forward_triple` writes bar T from
a window that ends one triple late, so at offset J the only prefix bar that
can move is J−1, and it moves only if the perturbation changes the CODE of the
triple ending at bar J. Every missed offset is one of exactly two things:

| frame | missed | code unchanged (window identical) | code changed, counts a PERMUTATION |
|---|---|---|---|
| walk | 17 | 15 | 2 (J = 240, 1440) |
| tick-rounded | 16 | 13 | 3 (J = 240, 560, 1440) |
| heavy-tailed | 22 | 18 | 4 (J = 520, 680, 760, 1040) |

Every offset at which the code is unchanged is missed (set inclusion,
asserted), and every remaining missed offset has the window's count vector
moving to a permutation of itself — e.g. on the walk at J = 240,
`[3,3,1,2,4,5] → [2,3,1,3,4,5]`. The entropy is a symmetric function of the
counts, so a permutation is invisible to it by construction. Measured
alongside: 262–275 of 1,480 consecutive window pairs already share their whole
count vector on these frames, which is the same insensitivity seen from the
other side.

The real module's `0/37` is therefore asserted on **six configurations**
(three frames at the default plus three lengths on the walk), not on one.

`offset` is this fork's standard parameter: `offset=2` equals `base.shift(2)`
and `offset=-2` equals `base.shift(-2)` exactly — a negative offset is the
caller's explicit look-ahead request, not a property of the formula, whose
default `offset=0` the sweep covers.

## Gate C — reachability

**Real data: measured** by the launcher's Gate E run
`is91-ts_perment_20-cff57e6c` (2026-11-12), over the 89 frozen ALTPORT-1
frames, **398,849 pooled bars**:

| | bars | share of 398,849 |
|---|---|---|
| non-NaN | **397,158** | 99.576% |
| of those, non-zero | **397,152** | 99.575% |
| exactly 0.0 | **6** | 0.0015% |
| degenerate (constant) frames | **0** of 89 | — |

`TS_PERMENT_20_3` therefore fires on real data, and `0 < 397,158 < 398,849`,
so Gate C and Gate D's non-constant requirement hold on the frozen universe
and not only on synthetic frames.

The porting session predicted this cell before it was run and the prediction
was exact: `89 × 19 = 1,691` is the arithmetic floor on the NaN count (19
warm-up bars a frame), so at most `398,849 − 1,691 = 397,158` bars can be
non-NaN, and **397,158 is what the run reports** — no frame carried a
non-finite close.

The porting session also expected a non-zero number of exactly-0.0 bars,
because a monotone or flat 20-bar run reads 0.0 (see the `trending` row
below). That is confirmed but it is **rare on real data: 6 bars in 397,158**,
against 1,236 of 1,481 on the synthetic drift-2.5σ path. BIST daily closes are
not monotone over 20 bars at any useful rate.

The rest of this section is **synthetic**: 1,500-bar generated paths, 1,481
fired bars each. "distinct" counts RAW float64 values; "at 1e-12" is after
rounding.

| path | distinct | at 1e-12 | min | p05 | median | p95 | max | exactly 0.0 | at the ceiling |
|---|---|---|---|---|---|---|---|---|---|
| gaussian walk | 160 | 97 | 0.5566 | 1.3485 | **1.6188** | 1.7540 | 1.7729 | 0 | 0 |
| tick-rounded walk | 162 | 102 | 0.7608 | 1.3006 | **1.6188** | 1.7540 | 1.7918 | 0 | 2 |
| coarse grid | 182 | 119 | 0.6837 | 1.1649 | **1.5654** | 1.7400 | 1.7918 | 0 | 4 |
| student-t(2) returns | 170 | 103 | 0.7608 | 1.3297 | **1.6425** | 1.7540 | 1.7918 | 0 | 3 |
| mean-reverting (AR φ = −0.6) | 151 | 88 | 0.9580 | 1.3801 | **1.6731** | 1.7729 | 1.7918 | 0 | 9 |
| two-point returns (±σ) | 65 | 48 | 0.8676 | 1.0879 | **1.3220** | 1.3801 | 1.3801 | 0 | 0 |
| **trending** (drift 2.5σ a bar) | **6** | 6 | **0.0** | 0.0 | **0.0** | 0.4258 | 0.6837 | **1236** | 0 |

`0 < 1481 < 1500` on every frame, with more than one distinct value on every
frame, so Gate D's non-constant requirement is met — but the `trending` row is
the one to read twice: a nearly monotone path sits at exactly 0.0 on 1,236 of
its 1,481 bars and takes only 6 distinct values. The column is informative
about *order*, and a whole regime can read 0.

The two-point row is a bound rather than an accident: when the returns take
exactly two values the reachable orderings are restricted, and the frame's
maximum (1.3801) is well below the ceiling.

## Gate D — scale-free

1,500-bar frames, 1,481 fired bars each; NaN masks equal in every cell.

| frame | ×8 | ×64 | ×1024 | ×10 | ×3.7 | ×0.1 |
|---|---|---|---|---|---|---|
| gaussian walk | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |
| tick-rounded walk | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |
| coarse grid | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |
| student-t(2) | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |
| mean-reverting | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |
| trending | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |
| two-point | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** | **1481/1481** |

All cells are max \|diff\| exactly 0.0. At four non-default lengths on the
walk, under ×8: `length=4` 1497/1497, `length=10` 1491/1491, `length=60`
1441/1441, `length=250` 1251/1251 — all bit-identical.

**Why this is stronger than Gate D asks.** The column reads only comparisons,
so it is invariant to ANY strictly increasing transform of the price axis, not
just to a multiplication — measured on the walk, all bit-identical on
1,481 of 1,481 bars:

| transform | bit-equal |
|---|---|
| `log(close)` | **1481/1481** |
| `sqrt(close)` | **1481/1481** |
| `close ** 3` | **1481/1481** |
| `close + 1000` | **1481/1481** |

×10 and ×3.7 are bit-identical here and the arithmetic does **not** promise it
in general: a non-power-of-two scale rounds each close, and rounding can
COLLAPSE two distinct closes onto one double. The tie rule makes a collapse
invisible when the earlier close is the smaller (`<=` either way) and visible
when it is the larger, so a scale *can* move this column — on these seven
frames none collapses.

**A drift is not such a transform**, and does move it: `close * exp(0.004 t)`
is Spearman **0.210808** against the base walk, with 45 of 1,481 bars
bit-equal. That measurement is why "invariant to the price axis" must not be
read as "invariant to the path".

## The attainable values

The value is a function of the window's pattern COUNT VECTOR and nothing else.
Consecutive triples share a comparison — bit B of one code is bit A of the
next — which is a necessary structural constraint on any realisable sequence
of codes.

| length | count vectors realised by some ordering | count vectors satisfying the constraint | equal |
|---|---|---|---|
| 6 (4 triples) | **63** (exhaustive over all 720 orderings) | 63 | **yes** |
| 7 (5 triples) | **116** (exhaustive over all 5,040 orderings) | 116 | **yes** |
| **20 (18 triples)** | not exhaustible | **5,978** | not checked |

At the shipped length the constraint admits **5,978** count vectors carrying
**175** distinct values to 1e-12, spanning exactly 0.0 to the ceiling
1.7917594692280547. 200,000 random orderings of 20 distinct closes reach
**2,814** of them — random orderings concentrate on the high-entropy vectors —
and every vector they reach satisfies the constraint; the even split
`(3,3,3,3,3,3)` is among them, which is the second proof that the ceiling is
attained.

The equality at lengths 6 and 7 is **evidence** that the constraint is exactly
attainability, not a proof at length 20; the receipt says 5,978 is an upper
bound on the attainable set and a measured count of the satisfying one.

Every value the module emitted on four 1,500-bar frames is inside that
175-value set at 1e-12, and the raw float64 values are not (the accumulation
detail of §Gate A, A3 showing up as data). **A rank statistic over this column
therefore carries many tied ranks by construction** — 1,481 bars over 151–182
distinct float64 values, 88–119 of them distinct at 1e-12 — which lowers the
attainable \|ρ\| against a continuous comparator. That is a property of the
feature, stated here so a low Gate E figure is not read as stronger evidence
of independence than it is.

## What it reads

Medians by path SHAPE (1,500 bars each, 1,481 fired):

| path | p05 | median | p95 |
|---|---|---|---|
| mean-reverting (AR φ = −0.6) | 1.3801 | **1.6731** | 1.7729 |
| student-t(2) returns | 1.3297 | **1.6425** | 1.7540 |
| gaussian walk | 1.3485 | **1.6188** | 1.7540 |
| tick-rounded walk | 1.3006 | **1.6188** | 1.7540 |
| coarse grid | 1.1649 | **1.5654** | 1.7400 |
| two-point returns | 1.0879 | **1.3220** | 1.3801 |
| zigzag (alternating) | — | **0.693147** | (1 distinct value) |
| flat / monotone | — | **0.0** | (1 distinct value) |
| trending (drift 2.5σ a bar) | 0.0 | **0.0** | 0.4258 |

So the column is high and tight on ordinary data (median 1.62 on a walk,
against a 1.79 ceiling) and collapses only when the path becomes *ordered* —
by trending, by alternating, or by going flat.

**It cannot see magnitude.** Planting one outlier at bar 700 of the walk:

| planted move | bars moved | median over them | frame median | column identical to the +10 case |
|---|---|---|---|---|
| +10 sigma | 15 | 1.6731 | 1.6188 | — |
| +50 sigma | 15 | 1.6731 | 1.6188 | **bit-identical** |
| +1000 sigma | 15 | 1.6731 | 1.6188 | **bit-identical** |

All three put that close above everything around it, so the ordering — and the
column — is the same. Note also the direction: the outlier *raises* the value
slightly on the 15 windows that hold it, because it breaks up whatever order
the path had. Do not read this column as an outlier detector.

**Nearest shipped columns on ONE 1,500-bar synthetic walk — NOT Gate E** (7
columns, one frame; Gate E is 687 comparators over 89 frozen BIST frames):

| \|ρ\| | column | n |
|---|---|---|
| 0.3101 | `chop` (14) | 1481 |
| 0.1506 | `ts_binent_20` | 1480 |
| 0.0988 | `lean_hurst_100` | 1401 |
| 0.0954 | `rsi` (14) | 1481 |
| 0.0835 | `psl` (12) | 1481 |
| 0.0819 | `entropy` (20) | 1462 |
| 0.0813 | `ts_c3_20` | 1480 |

`psl` — the issue's top prototype comparator at 0.2046 — is 0.0835 here, and
`entropy` (Shannon entropy of normalised CLOSES, the nearest-sounding shipped
column) is 0.0819. One synthetic frame is not evidence about the 89, and these
figures are a sanity check, not a Gate E result.

## Gate E — attribution

**Measured: SHIP.** Run by issue-solver on the committed code after the
porting session, with
`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.statistics.ts_perment_20` at default parameters (`kwargs {}`, no
exclusions, no rename prefix), bands `r3-perframe-0.90`.

| column | max \|ρ\| | against | n | per-frame max median | verdict |
|---|---|---|---|---|---|
| `TS_PERMENT_20_3` | **0.2847825** (ρ = −0.2847825) | `inertia` (`compute_all`) | 395,984 | **0.2746913** vs `inertia`, over 89 frames | **SHIP** |

Both halves of the band rule are clear of the 0.90 strike line by a wide
margin, and of the 0.76 ship line: pooled 0.2848, per-frame max median 0.2747,
and **0 of the 89 frames** reaches \|ρ\| ≥ 0.90 against the top comparator
(`perframe_pct_frames_ge_090` = 0.0). `verdict_pooled_only` is SHIP too, so the
verdict does not hinge on which of the two rules is applied. No column is
removed and no waiver is needed.

The strongest comparator in each set:

| set | max \|ρ\| | against | n |
|---|---|---|---|
| engine `compute_all` (329 columns) | **0.2847825** | `inertia` | 395,984 |
| `ml_features` manifest `1d` (358 columns) | **0.2723871** | `ATR_Bars_Above` | 397,158 |

Run facts, from `meta.json` and `overlap_max.csv` of the output folder
`is91-ts_perment_20-cff57e6c`:

| | |
|---|---|
| measured | 2026-11-12 |
| universe | 89 frozen ALTPORT-1 BIST frames, 398,849 pooled bars |
| comparators | **687** = 329 `compute_all` + 358 manifest `1d` |
| degenerate comparators dropped | 0 |
| canary | `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS` **bit-equal** |
| module sha1 | `0f4f4fc76fa084516246f2ee6454564e48966aad` |
| `pandas_ta` tree sha1 | `d987c08d647ddf5cb89b532d645418e84e4c906b` |
| data stamp | `1be6495ef7095ff67ad8f59a2fc0311d74f02652` |
| versions | pandas 2.3.3 / numpy 1.26.4 |

Recorded with `python docs/gate_e_ledger.py record <run dir> --measured
2026-11-12`, which re-checks the module sha1 against this tree, the 89-frame
universe, the 687 comparators and the bit-equal canary before writing the row;
it printed `ts_perment_20:TS_PERMENT_20_3 SHIP 0.2848 vs inertia`.

Two readings worth keeping straight:

* **This is not the issue's number.** Issue #91's screen measured **0.2046 vs
  `psl`** on the four-pattern prototype; the port measures **0.2848 vs
  `inertia`** — a different, higher figure against a different comparator,
  which is what a column correlating 0.55 with the prototype should produce
  (see *The port is not the column the screen measured*). The issue listed
  `inertia` 0.1830 as the prototype's *second* comparator, so the port moved
  it to first and raised it; the screen's `psl` is not in the port's top row at
  all. Both verdicts are SHIP, by different measurements.
* **A low \|ρ\| here is partly structural.** The column takes 88–119 distinct
  values at 1e-12 over 1,481 synthetic bars (§The attainable values), so a rank
  statistic against a continuous comparator carries many tied ranks by
  construction and the attainable \|ρ\| is depressed. 0.2848 is a pass, not
  proof of unusual independence.

## Gate F — suites

Porting session, in this worktree:

* `python -m pytest tests/test_ts_perment_20.py -q` → **158 passed** in 6.82 s.
* `python -m pytest -q` → **3 failed, 6,085 passed, 83 skipped** in 134.00 s.

The three failures are the two `CLAUDE.md` *Known breaks* —
`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
which needs the sibling `../AlternativeRepos` checkout and is deselected in
CI, and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
the `supertrend` citation into the untracked `docs/pine/` — plus
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
reports `['mtd_ret', 'ts_perment_20']`: this port's owed row, and one owed
before this branch. CI into `dev` skips that test under
`GATE_E_PENDING_OK=1`.

Receipt session, after recording the Gate E row, in this worktree:

* `python -m pytest -q --tb=no -p no:warnings -r f` → **3 failed, 6,092
  passed, 83 skipped** in 133.74 s.

The same three test IDs fail, but the ledger one now reports **`['mtd_ret']`**
only: `ts_perment_20`'s row is recorded, and the remaining name is the row
owed before this branch and not this port's. The other two are the two *Known
breaks*. So this branch adds no failure, and the local pass count rose by 7
(6,085 → 6,092): `tests/test_gate_e_ledger.py` parametrises seven checks over
the ledger's rows — four over `LIVE` (module named, module unmoved, output
unmoved, waiver when STRUCK), two over `ROWS` (verdict follows the bands,
column fires on real data) and one over the indicators in `LIVE` (the row's
columns are the default output) — so a row that did not exist adds exactly
seven test items, all passing, including
`test_verdict_follows_the_bands[ts_perment_20:TS_PERMENT_20_3]`.

The launcher runs both repos' suites in clean worktrees; this file does not
claim them.

The launcher runs both repos' suites in clean worktrees; this file does not
claim them. The same counts, and the four review rounds that produced them,
are in `docs/reviews/auto-2026-11-12-ts-perment-20/99-summary.md`.

## Cost

The module holds one int8 code array of `n − 2` and, per ordering, one bool
array of `(n − length + 1, length − 2)`; the windows themselves are a
`sliding_window_view`, so they are a view and not a copy. Memory is therefore
O(n · length), not O(n). Times are the best of three; the peak is measured
with `tracemalloc`, which numpy's allocator reports into:

| bars | time | one bool window array (computed) | traced peak (measured) |
|---|---|---|---|
| 10,000 | ~3 ms | 0.2 MB | 0.6 MB |
| 100,000 | ~28 ms | 1.8 MB | 4.7 MB |
| 400,000 | **~117–120 ms** | 7.2 MB | **18.5 MB** |

The times are best-of-three wall clock on one machine and are the only
figures in this file that do not re-run to the digit; the traced peaks do.

The engine calls indicators per frame (the 89 ALTPORT-1 frames average ~4,500
bars), so this is disclosed rather than a problem. For comparison,
`ts_binent_20` on the same 400,000 bars is 244 ms and a 144.1 MB peak
(`docs/TsBinent20Measured.md`): the bool-per-ordering spelling is cheaper than
a float64 index array because the codes are int8 and the six passes are
sequential.

## Wiring

Five touch points, all taken:

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_perment_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_perment_20 import ts_perment_20` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `"ts_perment_20"` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_perment_20(length=None, offset=None)` |
| 5 | `tests/test_ts_perment_20.py` | 158 tests |

Plus the counts the suite checks: `README.md` (headline, accessor count,
`statistics` row), `docs/IndicatorDictionary.md` (regenerated),
`docs/MLCompanionContract.md` and `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL`).

## Assumptions recorded in this session

AskUserQuestion is unavailable to a headless session, so the conservative
(smaller-scope) reading was taken and logged:

1. **Dimension 3 and tau 1 are constants, not parameters.** Generalising the
   order would need a different pattern-counting implementation; the issue
   fixes 3. The 3 is in the column name (`TS_PERMENT_20_3`) so a later order
   cannot silently reuse it.
2. **`length` is the one parameter**, defaulting to the issue's 20, with
   `MIN_LENGTH = 4` (a three-close window is one triple and a constant 0).
3. **The six-pattern source form ships, not the prototype's four-pattern
   sum** — `CLAUDE.md`'s "Gate A starts from the source formula, not the
   prototype". The divergence is measured, disclosed here and in the module
   docstring, and it invalidates the issue's own Gate E figures for this port.
