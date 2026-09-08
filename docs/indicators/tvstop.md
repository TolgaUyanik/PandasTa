# `tvstop` — Terminal Velocity Stop (TVS)

> **INDREF page.** One page per indicator; section names and citation discipline match the parent
> repo's family docs (`../Backtesting/docs/indicators/family-trend-overlay.md`, §6 of which is the
> long-form version of this page inside the *Trend overlay* family). This page is the
> **indicator-local** view: everything a reader needs about `tvstop` without opening the family doc
> or the git log. Template and per-section provenance: [`_TEMPLATE.md`](_TEMPLATE.md).
>
> **Citation convention, inherited from SR-1** (the parent repo's support/resistance review round
> that made function-name citation mandatory after Python line numbers went stale mid-review):
> a code anchor is a FUNCTION NAME (`module.py::function`, or a `SI:`/`IE:` function reference) or a
> **source** line number in a Pine/C file, which is immutable. A Python line number may appear only
> as a *convenience suffix beside a function name*, never alone — `strategy_miner.py:84-88` is
> acceptable because the surrounding text names `exclude_exact`; a bare `foo.py:212` is not.
> `tests/test_indref_pages.py` accepts `tests/test_x.py::name` and, grudgingly, `tests/test_x.py:12`. `IE:` = `../Backtesting/backtesting_engine/indicator_engine.py`.
> Grep the function name.
>
> **MEASUREMENT LAW** — this repo's dominant historical defect is a claim written before it was
> measured. Every count, `only`, `never`, `all` and ρ below was read from a named artifact or re-run
> in-session. **§5, §7, §8, §9 and §11 are QUOTED from durable records whose CSVs no longer exist on
> disk — §7.5 says exactly which records and how to re-run them.** §6 is MIXED and the split is
> exact: **only** its clamp-tolerance counts (`31 of 648`, `516 of 9,587`) and its scale-invariance
> results are non-quoted — those are in `tests/test_tvstop.py` and were re-run green in-session.
> §6's fixture range (−3.36387..+3.60011), its real-data extremes (−9.073724 / +7.924619) and its
> collapsed-ATR readings (12.98, 42.96) are **quoted and pinned by no test** — see §13. §12
> restates §7, §8 and the header table and introduces no new number. The header table, §2, §3 and
> §10 were re-derived in-session from the live package, the `.pine` file and the parent repo's
> CSV/grep.

| | |
|---|---|
| Module | `pandas_ta/trend/tvstop.py` |
| Category | `trend` |
| Registered in `Category` | yes (`pandas_ta/__init__.py`, `"tvstop"` in the `trend` list) |
| Accessor | yes — `df.ta.tvstop()` (`pandas_ta/core.py`) |
| Tests | `tests/test_tvstop.py` — 32 `def test_` functions, **53 passed** (`python -m pytest tests/test_tvstop.py -q`, run 2026-09-07) |
| Inputs | H / L / C |
| Params (**declared signature**) | `atr_length=None`, `mult=None`, `multm=None`, `vmax=None`, `mamode=None`, `emit_dist=False` — verbatim from `inspect.signature`, as printed in the `tvstop` row of `docs/IndicatorDictionary.md` (grep the row — that file is generated and its line numbers move whenever an indicator is added; another worker is adding some right now) |
| Params (**effective defaults**) | `atr_length=14`, `mult=3.0`, `multm=3.0`, `vmax=0.3` — ⚠ **not in the signature.** This fork declares `None` and resolves inside the body via `_validated_int` / `_validated_float` fallbacks at `pandas_ta/trend/tvstop.py:337-340`, so a generator reading only `inspect.signature` reports `None` and is not wrong, merely useless. These four are the values the emitted column names encode (`TVS_FLIP_BULL_14_3_3_0.3`) and must be read from the source. |
| Warm-up (dictionary probe) | 14 |
| Engine wiring | `IE:_calculate_tvpta4_indicators` — `('tvstop', _tvstop, (high, low, close), {})` |
| Provenance | TradingView Pine v6, `7YXrxMjV-Terminal-Velocity-Stop-Lyro-RS.pine`, MPL-2.0, © LyroRS |
| Status | shipped 2026-08-27 as candidate 23 of **TVPTA-6** (the parent repo's sixth TradingView-Pine porting batch). **NOT YET MINED** — see §10. |

---

## 1. What it measures — a rate limiter on stop travel

`Supertrend` and `HALFTREND` are **ratchets**: in an uptrend the line is
`max(previous line, target)` — with Supertrend's target at `hl2 ± mult × ATR`, not `close ± mult ×
ATR` — so after a vertical candle the line *teleports* up to the new target and the first pause
knocks the position out. `PSAR` is not a teleport but is the opposite of a cap: it steps a
*proportion of the remaining gap* (`sar += af × (EP − sar)`) with an **accelerating** factor
0.02 → 0.2, so a wider gap produces a bigger absolute step. `cksp_*` carries **no state at all** —
`rolling(q).max(rolling(p).max(high) − x×ATR)`, a windowed statistic whose outer max is a lag, not a
speed cap. **None of those three caps travel, and neither does the ratchet pair.**

This source keeps the ratchet and adds a **speed limit**. `vmax` (default 0.3) is the terminal
velocity in **ATR per bar**: however violent the candle, the stop advances at most `vmax × ATR`.
That the other lines do not is measured, not argued — §7.4.

**The port ships neither the stop line nor the distance to it.** The source's payload is `stop`, a
raw price level, which this fork's scale-free law forbids (a tree cannot compare `SMA_10` to
`close`; the same applies to a stop line). `TVS_DIST = (Close − stop) / ATR` was built as the
scale-free replacement — the level is recoverable as `Close − TVS_DIST × ATR`, so nothing would have
been lost — and was then **deleted on its own overlap measurement** (§7). The source's `dir` is not
emitted either: the sign of `TVS_DIST` recovers it (§6 gives the one reachable exception), so a
separate direction column would have been redundant even before the deletion.

⚠ **Consequence worth stating plainly: the shipped pair tells a model when the direction CHANGED,
not what it currently is.** A model needing current direction must take it from
`Supertrend_Direction` or `HALFTREND_DIR`, which the engine already carries.

## 2. Columns and ML form

From `docs/IndicatorDictionary.md` (probe run 2026-09-07, synthetic 600-bar OHLCV series — forms
observed, not transcribed) and the parent repo's `docs/knowledgebase/IndicatorMLRegister.md`
(**`Verdict` column verbatim** — it is a single token; the parenthesised gloss is that register's
`why` column, also verbatim, and the last column is its `proposed action`):

| Column | dtype | Dictionary ML form | Register `Verdict` | Register `proposed action` | What it is |
|---|---|---|---|---|---|
| `TVS_FLIP_BULL_14_3_3_0.3` | float64 (0/1) | `BIN` | **OK** (register `why`: "0/1 event flag: the rate-limited trailing stop FLIPPING direction on this bar") | admitted (register-only, not individually validated) | direction flip to bull (Pine L86) |
| `TVS_FLIP_BEAR_14_3_3_0.3` | float64 (0/1) | `BIN` | **OK** (same `why` text — the register carries one shared gloss on both rows) | admitted (register-only, not individually validated) | direction flip to bear (Pine L87) |
| ~~`TVS_DIST_14_3_3_0.3`~~ | float64 | — not emitted by default, so the probe never sees it | **no register row — DELETED before it shipped** | — | `(Close − stop) / ATR`, signed |

⚠ The gloss "OK — discrete event" used in `../Backtesting/docs/indicators/family-trend-overlay.md`
is the **family doc's** wording, not the register's. Only `OK` is verbatim from the register.

`TVS_DIST` is still computed under `emit_dist=True`, deliberately, so the deletion stays
reproducible. The default two-column shape is pinned by
`test_default_output_omits_the_deleted_dist_column`.

⚠ The register's `Range` for the two flags reads `0..1`. Register ranges are generally **fixture
measurements, not bounds** — for these two the 0/1 range is by construction, but do not read any
other register Range as a cap (§6 shows what that costs for `TVS_DIST`).

## 3. Provenance

| | |
|---|---|
| Source | `docs/pine/7YXrxMjV-Terminal-Velocity-Stop-Lyro-RS.pine` (this repo, untracked — see `CLAUDE.md`); an identical copy sits at `../Backtesting/docs/TradingView/pine/` |
| Length | **116 content lines** — `wc -l` 116 and `grep -c ''` 116 agree (re-run 2026-09-07); the file is newline-terminated, so no off-by-one |
| Pine version | `//@version=6` |
| Licence | Mozilla Public License 2.0, © LyroRS |
| TA-Lib equivalent | **none** — TVS is not a TA-Lib function; there is no C reference to diff against |
| Gate A anchor | L61–L87. `tests/test_tvstop.py` carries a literal Pine-order transliteration of that block, written from the source rather than from the module, run bar-for-bar against the shipped implementation on the *same* ATR series so the comparison isolates the stop state machine and not the moving-average flavour. |

Cited line numbers re-verified in-session against the `.pine` file: L61 `atr = ta.atr(atrLen)`,
L66 `target`, L71 `step = math.max(math.min(target - stop, vmax * atr), -vmax * atr)`,
L74 `stop := math.max(stop, stop + step)`, L78/L84 the flip resets, L80 the downtrend mirror,
L86/L87 `flipUp` / `flipDown`.

## 4. Formula AS COMPUTED HERE

```
atr    = ta.atr(atr_length)                              # L61
target = dir == 1 ? close - mult*atr : close + multm*atr # L66
step   = max(min(target - stop, vmax*atr), -vmax*atr)    # L71
dir==1 : stop = max(stop, stop + step)                   # L74
         if close < stop: dir = -1; stop = close + multm*atr   # L76-78
else   : stop = min(stop, stop + step)                   # L80
         if close > stop: dir = +1; stop = close - mult*atr    # L82-84
flipUp   = dir==1  and dir[1]==-1                        # L86
flipDown = dir==-1 and dir[1]==1                         # L87
```

**Which half of the L71 clamp is dead, and where — the ratchet trap.** Writing `x = target − stop`
and `v = vmax × ATR ≥ 0`:

| Branch | Folded form | Dead half | Live rate limiter |
|---|---|---|---|
| uptrend (L74) | `max(0, max(min(x,v), −v))` = `max(0, min(x,v))` | the **lower** clamp `math.max(…, −vmax*atr)` | `math.min(…, vmax*atr)` |
| downtrend (L80) | `min(0, max(min(x,v), −v))` = `min(0, max(x,−v))` | the **upper** clamp `math.min(…, vmax*atr)` | `math.max(…, −vmax*atr)` |

Each half is dead in **exactly one** branch and load-bearing in the other, so **neither is globally
removable**. The port reproduces L71/L74/L80 literally rather than substituting the reduced forms,
so the code reads against the source line for line.

⚠ **The TVPTA-6 brief for this candidate named the wrong half** — it said L74 makes the `math.min`
half dead in the uptrend branch. `max(0, x)` discards *negative* steps, so it subsumes the `−v`
FLOOR, not the `+v` CEILING; deleting the `math.min` there removes the rate limit itself. Three
tests demonstrate this on data instead of asserting it:
`test_lower_clamp_is_dead_in_the_uptrend_branch` (bit-exact no-op on an all-uptrend series),
`test_upper_clamp_is_load_bearing_in_the_uptrend_branch` (>100 bars change, and only in the
loosening direction), `test_lower_clamp_is_not_globally_removable`.

**The flip resets bypass the rate limit.** L78/L84 assign `stop := close ± multiplier × atr`
outright: `vmax` governs travel WITHIN a direction, not the reset.

**A NaN bar is skipped, not consumed** — `stop`/`dir` carry across it. This is a deliberate
divergence from Pine, where `na` propagates through L71/L74, leaves `stop` na, and re-enters the L68
`if na(stop)` branch on the next bar, **resetting** the stop.

## 5. Causality (Gate B)

Bar-by-bar causal; `stop`/`dir` are recursive state carried forward, never read back.

Proved by **future-perturbation** — rewrite every bar from `j` onward, demand bars `[0:j]`
bit-identical — swept over **30 offsets in BOTH directions**. Both directions matter and the sweep
is not decoration: a one-bar leak proposes one step and the ratchet *discards* it when the sign is
wrong, so a single-offset one-directional version of this test passed both mutants during
development. Two perturbing look-ahead mutants (`importlib` source read, one write index shifted
forward, `exec`'d into a fresh in-memory module — never a hand-written copy) are each proved LIVE
against the real module first, then caught. Disagreement is scored only on cells finite in both
runs, after asserting the NaN masks match, because a bare `!=` on NaN-bearing floats passes on a
null mutant.

Truncation is kept as corroboration and its **measured** weakness is pinned rather than hidden: over
the same sweep it catches the `target` mutant **7 times** and the `flip` mutant **not at all**.

⚠ **Contamination reach is NOT bounded by `atr_length`.** An EMA/RMA stage makes a stated `length` a
decay constant rather than a window, so any window-based taint number is a floor. This indicator
adds a second, longer-lived carrier: `stop` is recursive state reset *only* by a direction flip.
Measured reach is in §9.

## 6. ML-suitability (Gate D, and what the deleted column looked like)

The two shipped flags are 0/1 by construction and scale-free trivially. Everything in the bullets
below describes **`TVS_DIST`, which is not shipped**; it is recorded because it is what a reader
needs to re-derive the column and the finding.

Scale-freeness: both `mult × ATR` and `vmax × ATR` are price-proportional, so `(Close − stop)/ATR`
is dimensionless. Verified invariant at ×10 and **bit-exactly at ×8** (an exact power of two leaves
every mantissa untouched), NaN masks identical.

- **`TVS_DIST` is unbounded in both directions.** Had it shipped, its register Range would have read
  **−3.36387..+3.60011** — a *fixture* measurement, not a bound. The generator's fixture draws a
  **half-normal spread `close × |N(0, 0.006)|`** around Close
  (`docs/gen_indicator_dictionary.py:26`, `rng = np.random.default_rng(7)` at :20, N = 600), then
  clamps High/Low against Open and Close; the spread is unbounded above, so the observed extremes
  are a property of one 600-bar seed-7 series and nothing caps them. ⚠ The `0.02` visible in that
  generator is **not** a fixture bound — it is the scale-classifier's tolerance at
  `gen_indicator_dictionary.py:112/114` (`abs(r - SCALE)/SCALE < 0.02`). An earlier round of this
  page misread it as "High/Low pinned at ±2 % of Close": right conclusion, invented mechanism.
  Cached BIST_100 daily frames reach **−9.073724** (ARCLK.IS) / **+7.924619** (GARAN.IS).
- **In the uptrend branch, `TVS_DIST > mult` is an iff detector of the clamp binding — exact in
  exact arithmetic, and at float64 it requires a ~1e-12 tolerance.** An unclamped positive step
  lands the stop *on* its target (`= mult`); a negative one is discarded by the ratchet (`< mult`);
  so the stop sits strictly below target only when the step was cut to `+vmax×ATR`. ⚠ That proof
  uses `stop_prev + (target − stop_prev) = target`, an identity float64 does not honour. Measured on
  the fork's own fixture `_walk(1200, seed=11)`, a strict `dist > mult` disagrees with a reference
  run recording when it actually clamped on **31 of 648** uptrend bars, and on a 20,000-bar walk
  (seed 7) on **516 of 9,587 (5.38 %)**; at `dist > mult + 1e-12` both counts are **0**. The
  tolerance in `test_dist_above_mult_is_exactly_the_clamp_binding` is load-bearing and a consumer
  thresholding this column must carry it. **No ratchet stop in this family can express that
  quantity**, because each closes the gap in one bar.
- **The sign is the direction, except at an exact 0 — which is reachable.** On a dead-flat stretch
  ATR falls to the fork's `non_zero_range` epsilon floor (2.220446049250313e-16), `target` rounds to
  `close`, the stop never moves, and every bar reads exactly 0.0 while `dir` is still 1. Do not read
  `sign(TVS_DIST)` as direction without handling 0.
- **A collapsed-but-positive ATR is an amplifier, deliberately not clipped.** On a 60-bar fixture
  flat at 50.0 that steps once to 50.5, `TVS_DIST` reads 12.98 and climbs to 42.96 against a `mult`
  of 3.0. Nothing reaches inf, nothing NaNs out, nothing looks broken. A clip would invent a
  threshold the source does not have.

## 7. Overlap (Gate E) — and why the headline column was deleted

Grid: every column against the **complete numeric column set** of
`IndicatorEngine(include_advanced=True).compute_all()`, comparators taken from `compute_all`'s own
output and never hand-reconstructed. **89 BIST_100 daily frames / 405,312 pooled bars / 478
comparators.** Harness `../Backtesting/scripts/analysis/measure_tvstop_overlap_full.py`.

Grid as measured (3 columns): **1,434 cells = 1,428 measured + 6 degenerate** (the hourly-only
`TOD_SLOT_RVOL_20_20` / `TOD_SLOT_VVOL_20_20` pair is all-NaN on daily frames by design, n = 0, one
cell each per TVS column). Shipped grid (2 columns): **956 cells = 952 measured + 4 degenerate.**

### 7.1 The deletion

🔴 **`TVS_DIST` measured ρ = +0.930462 against `RSI` (n = 404,066) and is DELETED** — above this
project's ~0.9 revert line.

**Not a pooling artifact**, which is what makes it a deletion rather than a disclosure. Per-frame
(harness `--stage 5`), one row per frame per comparator:

| cell | mean | median | min | max | frames |
|---|---|---|---|---|---|
| `TVS_DIST` × `RSI` | +0.9321 | +0.9329 | +0.8126 | +0.9595 | 89 |
| `TVS_DIST` × `cmo` | +0.9321 | +0.9329 | +0.8126 | +0.9595 | 89 |
| `TVS_DIST` × `ATRMAX_14_50` | +0.9072 | +0.9079 | +0.8504 | +0.9403 | 89 |
| `TVS_DIST` × `QQE_RSIMA` | +0.9021 | +0.9027 | +0.7801 | +0.9276 | 89 |
| `TVS_DIST` × `zscore` | +0.9021 | +0.9055 | +0.8075 | +0.9455 | 89 |
| `TVS_DIST` × `Supertrend_Direction` | +0.7822 | +0.7875 | +0.6515 | +0.8581 | 89 |

`cmo` is a monotone recode of `RSI`, so its identical value is a consistency check, not a second
finding — but `ATRMAX`, `QQE_RSIMA` and `zscore` are not. This is a whole **momentum
neighbourhood**. Pooled grid: 5 cells ≥ 0.90, 23 ≥ 0.80, 39 ≥ 0.76, median |ρ| 0.031098, min
0.000018.

**Mechanism, so the result is not re-discovered by accident.** In an uptrend the stop closes its gap
to target at no more than `vmax × ATR` per bar, so `Close − stop` **accumulates** the recent move in
ATR units — which is, to a monotone transform, what RSI reports. *The rate limiter turns the
distance into a slow momentum integrator.*

⚠ **Do not re-add it on the grounds that it is not a stop-lane duplicate.** True and irrelevant:
over all eleven stop-lane columns its maximum is **+0.786164** against `Supertrend_Direction` — only
the 0.76–0.80 ship-with-disclosure band. It died on a momentum oscillator, not on its own lane.

### 7.2 What ships

| Shipped column | measured max \|ρ\| | pair | n |
|---|---|---|---|
| `TVS_FLIP_BEAR_14_3_3_0.3` | **+0.219132** | `APUSH_BEAR_14_5_5` | 404,066 |
| `TVS_FLIP_BULL_14_3_3_0.3` | **+0.202650** | `IFVG_MIT_BEAR_14` | 404,066 |

**Shipped maximum for this port: +0.219132, n = 404,066** — second-lowest full-grid maximum in the
TVPTA-6 batch after DTDB's 0.1185, and below every other shipped maximum in that batch (FLAG_PEND
0.5769, RPO_VA_WIDTH 0.5486, APUSH 0.5090, IFVG 0.4624, SRCOR 0.4234, TOD 0.4141, MADIV 0.2823, SDZ
0.2400).

### 7.3 Siblings and the stop lane

Sibling cells (harness `--stage 4`; the main grid drops a port's own columns from its comparators):

| pair | basis | ρ | n |
|---|---|---|---|
| `TVS_FLIP_BULL` × `TVS_FLIP_BEAR` | full column | **−0.012078** | 404,066 |
| `TVS_DIST` × `TVS_FLIP_BULL` | full column | +0.117152 | 404,066 |
| `TVS_DIST` × `TVS_FLIP_BEAR` | full column | −0.138786 | 404,066 |
| `TVS_DIST` × (`FLIP_BULL` + `FLIP_BEAR`) | tautology marker, **not a gate** | −0.016025 | 404,066 |
| `TVS_DIST` × `TVS_FLIP_BULL` | support-conditional (flip bars) | +1.000000 | 9,644 |
| `TVS_DIST` × `TVS_FLIP_BEAR` | support-conditional (flip bars) | −1.000000 | 9,644 |

The two ±1.000000 cells are **degenerate by construction, not a finding**: the L78/L84 reset puts
`TVS_DIST` at ∓`mult` on a flip bar. ⚠ That identity holds by construction *in exact arithmetic* and
is **measured to 1e-12**, not at strict equality: `|TVS_DIST|` is within 1e-12 of `mult` on **9,644
of 9,644** flip bars but at strict `==` on only **1,067 of 9,644 (11.06 %)**.

The converse — the one thing not settled by construction — was measured rather than assumed:
**53,538 of 404,066 bars (13.25 %)** sit within 1e-12 of ±`mult`, of which 9,644 are flips, so
**P(flip | within band) = 0.180134**. Re-measured at strict `==` on the same pool: **6,220 of
404,066 (1.54 %)**, **P(flip | strict) = 0.171543**. On either basis the great majority of at-`mult`
bars are not flips, so the dense column is not a re-encoding of the sparse flags. What is *not*
defensible is calling either count "exactly ±`mult`".

Stop lane, all eleven columns (harness `--stage 6`, which coerces the three non-numeric ones —
`Supertrend_Signal` and `PSAR_Signal` are `object` strings, `PSAR_Reversal` is `bool` — that stage 2
cannot see; **33 cells, 33 measured, 0 degenerate**):

| stop column | `TVS_FLIP_BULL` | `TVS_FLIP_BEAR` | (`TVS_DIST`, deleted) |
|---|---|---|---|
| `Supertrend` | −0.002598 | +0.010891 | +0.007844 |
| `Supertrend_Direction` | +0.084545 | −0.104708 | +0.786164 |
| `Supertrend_Signal` (coerced) | +0.084545 | −0.104708 | +0.786164 |
| `PSAR` | −0.004055 | +0.010705 | +0.022871 |
| `PSAR_Signal` (coerced) | **+0.100242** | **−0.112036** | +0.506844 |
| `PSAR_AF` | −0.025278 | −0.026128 | +0.067967 |
| `PSAR_Reversal` (coerced) | +0.022919 | +0.023022 | +0.004433 |
| `HALFTREND` | −0.001590 | +0.008211 | +0.033350 |
| `HALFTREND_DIR` | −0.049362 | +0.038389 | +0.486839 |
| `cksp_CKSPl_10_3_20` | −0.000542 | +0.007874 | +0.015397 |
| `cksp_CKSPs_10_3_20` | −0.000046 | +0.008067 | +0.015176 |

`Supertrend_Signal` reproducing `Supertrend_Direction` to six decimals is the expected consistency
check (monotone recode). The shipped flags' lane maximum is **0.112036**, and against
`PSAR_Reversal` — the one engine column that fires on the same *kind* of event — just **+0.0229 /
+0.0230**. A stop flip under a rate limit is a different event from a PSAR reversal.

⚠ **Nine of those eleven columns are already excluded from mining** (re-grepped 2026-09-08 and it
holds: `strategy_miner.py:84-88` `exclude_exact`, `:137` the `cksp_` pattern) by the parent repo's
`strategy_miner.py` (`Supertrend`, `Supertrend_Signal`, `PSAR`, `PSAR_Signal`, `PSAR_AF`,
`PSAR_Reversal`, `HALFTREND` via `exclude_exact`; both `cksp_*` via the `cksp_` `exclude_patterns`
entry). Only `Supertrend_Direction` and `HALFTREND_DIR` reach a tree, and both are ±1 direction
states — so **the engine has no mineable continuous stop-distance column today.** Both shipped TVS
columns are admitted.

### 7.4 The rate limit itself, measured against the lane

*Quoted from the durable records named in §7.5 — the CSV is gone from disk.* The claim in §1, that
no other line in this lane caps travel, is a claim about the **distribution of per-bar movement**,
so it was tested directly: per-bar `|Δline| / ATR` on three cached BIST daily frames, flip/reversal
bars excluded where the line resets by design (harness `--stage 7`, artifact
`backtest_results/tvpta6/tvstop_travel_20260827.csv`).

| Line (GARAN.IS) | n | median | p99 | **max** | frac > 0.3 |
|---|---|---|---|---|---|
| **TVS stop, non-flip bars** | 6,543 | 0.0000 | **0.300000** | **0.300000** | **0.000000** |
| TVS stop, all bars (flip resets included) | 6,714 | 0.0000 | 2.7316 | 2.9896 | 0.0255 |
| `Supertrend` line | 6,715 | 0.0000 | 3.1244 | 3.9080 | 0.1979 |
| `PSAR` line, non-reversal bars | 6,137 | 0.1762 | 0.7249 | 2.3390 | 0.2516 |
| `HALFTREND` line | 6,714 | 0.0000 | 2.4469 | 6.6686 | 0.1186 |
| `cksp_CKSPl_10_3_20` | 6,699 | 0.0000 | 1.4661 | 3.9824 | 0.1267 |

The TVS non-flip maximum reads **0.300000 = `vmax`** on all three frames (GARAN.IS, AEFES.IS,
MGROS.IS) with **zero** bars above it. ⚠ **Both figures carry a tolerance and neither is a
strict-float claim.** The harness reports `round(max, 6)` of **0.3000000000000111** and counts bars
above `0.3 + 1e-9`. At strict `> 0.3` the count is **2,283 of the 17,598** non-flip bars, exceeding
by at most **1.11e-14** — the re-rounding of `stop + vmax×ATR` minus `stop`, not travel. The
comparison is against excesses of 10⁻¹ to 10², so the tolerance does not move the reading.

Every other line exceeds `vmax` on **10.5 % – 25.3 %** of bars, with per-line maxima of **1.11 –
9.80 ATR** across the three frames (the 1.11 is `PSAR` on AEFES.IS, the 9.80 `cksp_CKSPl` on
MGROS.IS). On the contaminated MGROS.IS frame `PSAR` reaches **776.6 ATR in a single bar** while the
TVS stop stays at 0.300000.

PSAR's acceleration was measured rather than asserted: Spearman(|prev gap to price|, |step|) =
**+0.821 / +0.782 / +0.791** across the three frames, with the median step **44×** larger in the top
gap quartile than the bottom (GARAN.IS 0.18547 vs 0.00420; artifact
`tvstop_psar_gap_20260827.csv`).

**This is the strongest single piece of evidence that the port is not a re-encoding of its lane**,
and the only measurement that directly demonstrates the mechanism §1 claims.

### 7.5 ⚠ Artifact availability — checked in-session 2026-09-07

The harness `../Backtesting/scripts/analysis/measure_tvstop_overlap_full.py` is **present** (43 KB).
Its output CSVs — `tvstop_overlap_*`, `tvstop_perframe_rho_*`, `tvstop_stoplane_*`,
`tvstop_sibling_*`, `tvstop_support_discrim_*`, `tvstop_flipident_*`, `tvstop_reachability_*`,
`tvstop_contamination_*`, `tvstop_travel_*`, `tvstop_psar_gap_*` and `tvstop_clamp_probe_*` — the
2026-08-27 stamps being `tvstop_overlap_20260827.csv`, `tvstop_perframe_rho_20260827.csv`,
`tvstop_stoplane_20260827.csv`, `tvstop_sibling_20260827.csv`,
`tvstop_reachability_20260827.csv`, `tvstop_contamination_20260827.csv`,
`tvstop_travel_20260827.csv`, `tvstop_psar_gap_20260827.csv`, `tvstop_clamp_probe_20260827.csv`,
`tvstop_flipident_20260827.csv` and `tvstop_support_discrim_20260827.csv` — **eleven names for the
eleven globs above; `flipident` backs §7.3's band-vs-strict counts and `support_discrim` backs its
±1.000000 support-conditional cells** — all written under `backtest_results/tvpta6/`, **were NOT
found on disk**:
`find ../Backtesting -iname "*tvstop*"` returns only the harness, and `backtest_results/tvpta6/`
currently holds four `fvg_*` files and nothing else. That directory is gitignored
(`../Backtesting/.gitignore:14`), so the CSVs were never committed and have since been cleaned.

**Every ρ, n and count in §5, §7, §8, §9 and §11 is therefore quoted from the durable records that
DO exist** —
`../Backtesting/docs/indicators/family-trend-overlay.md` §6,
`../Backtesting/docs/knowledgebase/IndicatorMLRegister.md` (rows `TVS_FLIP_BULL/BEAR`), the
`IE:_calculate_tvpta4_indicators` docstring, and the module + test docstrings in this repo — all of
which agree with each other.

⚠ **§6 is the exception, and it is the good kind.** Its `31 of 648`, `516 of 9,587 (5.38 %)`, the ×8
bit-exact / ×10 tolerance invariance and the NaN-mask equality are **not quoted** — they live in
this repo at `tests/test_tvstop.py::test_dist_above_mult_is_exactly_the_clamp_binding`
and `tests/test_tvstop.py::test_scale_invariance`, and they were **re-run green
in-session** (53 passed, 2026-09-07). Anyone can reproduce them in 13 seconds; no artifact hunt
required. §6's real-data extremes (−9.073724 / +7.924619) *are* quoted.

**To re-measure the rest rather than re-quote it**, run
`python3 scripts/analysis/measure_tvstop_overlap_full.py --stage 1` then `--stage 2`, followed by
`--stage 3` (contamination), `--stage 4` (siblings), `--stage 5` (per-frame), `--stage 6` (stop
lane), `--stage 7` (travel).

## 8. Reachability (Gate C)

Against `BeamMiner(min_support=30)` (`../Backtesting/backtesting_engine/contract_miner.py`), per
frame, **89 BIST_100 daily frames / 405,312 bars**:

| Column | populated | non-zero (pooled) | per-frame min / median / max | frames < 30 | frames with none |
|---|---|---|---|---|---|
| `TVS_FLIP_BULL_14_3_3_0.3` | 404,066 (99.69 %) | 4,788 (1.18 %) | 8 / 65 / 91 | **24 of 89** | **0 of 89** |
| `TVS_FLIP_BEAR_14_3_3_0.3` | 404,066 (99.69 %) | 4,856 (1.20 %) | 9 / 66 / 92 | **24 of 89** | **0 of 89** |

The median frame clears the gate twice over and **no frame is empty** — but **24 of 89 (27 %) sit
below it individually**, so roughly a quarter of frames contribute only by pooling. Pooled, both
clear by ~160×. The bull/bear near-symmetry (4,788 vs 4,856, 1.4 % apart) is expected: the source's
two branches are mirror images.

## 9. BIST specifics — DI-5 / DI-5b contamination

**Tag glossary for this section.** **DI-1** is the parent repo's BIST data-integrity fix that
removed unadjusted split cliffs by rejecting close-to-close moves beyond BIST's ±10 % limit.
**DI-5** and **DI-5b** are two frames that survive DI-1's test and are still corrupt: `MGROS.IS` and
`ARCLK.IS` carry absurd **High** values (`High > 2×Close`) that never show up as a c2c violation,
so an ATR-based indicator inherits them silently.

Measured per frame on the two escalated frames plus two clean controls (harness `--stage 3`):

| | MGROS.IS (DI-5) | ARCLK.IS (DI-5b) | AEFES.IS | GARAN.IS |
|---|---|---|---|---|
| bars | 5,678 | 6,729 | 5,662 | 6,729 |
| `High > 2×Close` bars | 162 (idx 0–161) | 784 (idx 0–794) | 0 | 0 |
| c2c > 10.5 % (DI-1's test) | **0** | **0** | 0 | 0 |
| flips, whole frame | 121 (2.14 %) | 157 (2.34 %) | 134 (2.37 %) | 171 (2.55 %) |
| ⚠ *denominator of that percentage* — 2.14 % resolves on **121/5,664** and 2.34 % on **157/6,715**, i.e. **bars minus the 14-bar ATR warm-up**, not on the 5,678 / 6,729 bar counts in the first row. (121/5,678 = 2.13 %, 157/6,729 = 2.33 %.) **Inferred**, not read off the CSV, which is gone — but the two subtractions land exactly. The expectation row below therefore multiplies the raw `flips/bars` fraction, not the displayed percentage; the two bases differ by 0.25 %. | | | | |
| ⚠ *the CSV's own `flips_inside` column has a construction **floor of 1*** — each span is defined to end at the next flip and includes it, so it can never read 0 on a non-empty reach. **That is why the rate comparison below uses the fixed `[i, i+14)` ATR window instead of the CSV column** — the window is not arbitrary, it is the one span that can honestly read zero. | | | | |
| **flips inside the `[i, i+14)` taint window** | **0 of 175 bars** | **0 of 808 bars** | — | — |
| expected flips in that window at the frame rate | 175 × (121/5,678) = **3.73** | 808 × (157/6,729) = **18.85** | — | — |
| taint reach to the next flip | 472 bars | 964 bars | — | — |
| expected flips in that reach at the frame rate | 10.08 | 22.54 | — | — |
| median ATR/Close inside | **2430.24** | **2.02** | — | — |
| median ATR/Close outside | 0.02849 | 0.02951 | 0.03062 | 0.03280 |
| `at_mult` rate inside / outside | **0.5066** / 0.1421 | 0.1621 / 0.1211 | — / 0.1245 | — / 0.1246 |

**The failure mode is SUPPRESSION, and it is silent.** An inflated High makes ATR enormous (2,430×
the close on MGROS.IS), so the stop sits absurdly far from price and can never be crossed: **zero**
flips over 175 and 808 tainted bars, where **~4 and ~19** were expected at the frames' own rates:
**175 × (121/5,678) = 3.73** and **808 × (157/6,729) = 18.85**. The multiplication is shown inline,
on the same basis it was computed, so a later condensation cannot re-break it. ⚠ Do **not**
substitute the displayed 2.14 % / 2.34 % into it — those resolve on bars-minus-warm-up (121/5,664,
157/6,715) and give 3.75 / 18.91. The two bases differ by 0.25 % and the discrepancy is immaterial
against a measured zero, but a reader checking the arithmetic must be told which one is on the page.
Absent events look exactly like a quiet period.

⚠ **Do not read the ~4 / ~19 off the `reach` row.** The 10.08 / 22.54 in the table are expectations
over the *reach to the next flip* (472 and 964 bars), a different and much longer span. Conflating
the two inflates the suppression claim by ~2.7×; round 2 of this page's review caught exactly that
substitution.

For the deleted `TVS_DIST` the shape was the *plausible pinned value*: with ATR enormous the clamp
never binds, the stop lands on its target essentially every bar, and the column pins within 1e-12 of
`+mult` on **50.66 %** of the tainted span against a **12.4 %** base rate on the clean controls
(AEFES.IS 0.124469 / GARAN.IS 0.124646; 13.25 % pooled).

⚠ `at_mult` is `abs(abs(TVS_DIST) - mult) < 1e-12` throughout this page — a band, not strict
equality.

⚠ **One hypothesis was tested and did NOT hold.** A stop left too *high* by a bad bar should be
cleared by a *fabricated* flip. Measured over the bad bar and the two following: **0 such flips on
162 MGROS.IS bad bars and 0 on 784 ARCLK.IS bad bars.** The taint suppresses flips; it does not
manufacture them.

⚠ **No range screen separates the contaminated frames from the clean ones.** MGROS.IS runs
**−7.4929 … +7.5016** against clean AEFES.IS **−7.4735 … +7.3346** and GARAN.IS **−6.8288 …
+7.9246** — within 0.02 and 0.17 of the clean pair. ARCLK.IS's **−9.0737** is the widest of the four
but only **21.4 % beyond** the clean pair's widest negative, and its positive tail (+6.9326) is the
*narrowest* of the four. So the honest statement is not "inside the envelope" — ARCLK.IS is
marginally outside it on one tail — but that a threshold tight enough to flag ARCLK.IS's 784
contaminated bars on a 21 % single-tail difference would reject clean frames wholesale, and would
still miss MGROS.IS's 162 entirely.

⚠ Both contaminated frames have their bad bars at the **start** of the series (index 0–161 and
0–794), so on these two frames the taint never reaches the modern era. That is a property of these
two frames, not a general result.

## 10. Mining track record — **never selected; never mined**

Re-run in-session 2026-09-07 against the parent repo:

```
grep -c 'TVS_'  ../Backtesting/datastore/source/StrategyMaster.csv     ->  0
grep -ci 'tvstop' ../Backtesting/datastore/source/StrategyMaster.csv   ->  0
grep -rl --no-ignore-files 'TVS_' ../Backtesting/backtest_results/     ->  0 files
```

**No mined rule references any `TVS_*` column, and no row in `StrategyMaster.csv` names `tvstop`.**
This is *expected*, not a negative result: the columns shipped 2026-08-27 and **no mining run has
been executed since**. Nothing on this page is a claim of edge. **INDREF-2** — the engine-side
results write-up that this page's series feeds, tracked in this repo's `TODO.md` — is where a
selected / never-selected verdict becomes meaningful.

⚠ The parent repo's default `grep` is a ugrep wrapper that honours `.gitignore`, and
`backtest_results/tvpta6/` is ignored at `.gitignore:14`. Always sweep with `--no-ignore-files`, as
above.

## 11. Improvement ideas — one measured, none taken

**The clamp binding, as its own column.** The genuinely novel quantity in this indicator is *whether
the rate limiter bound*; the deleted distance was only its proxy. A binary clamp flag was **probed**
against the same 478 comparators on the same pool:

| probe column | fire rate | max \|ρ\| | pair |
|---|---|---|---|
| `TVS_CLAMP_BULL` | 15.62 % | +0.745392 | `ATR_BREAKOUT_UP` |
| `TVS_CLAMP_BEAR` | 10.56 % | +0.678733 | `ATR_BREAKOUT_DN` |
| `TVS_CLAMP_ANY` | 26.17 % | +0.516067 | `ATR_BREAKOUT_UP` |

🔴 **That is a PROBE, not a verdict, and nothing was shipped on it.** The probe column was
reconstructed **outside** `IndicatorEngine.compute_all`, and its causality, scale-invariance and
contamination gates were **never run**. Anyone picking it up owes it the full gate stack.
ρ(`TVS_CLAMP_BULL`, `TVS_DIST`) = **+0.6289** and ρ(`TVS_CLAMP_ANY`, `TVS_DIST`) = **+0.1472**, so
the union form is the one that is genuinely not the deleted column. Artifact:
`backtest_results/tvpta6/tvstop_clamp_probe_20260827.csv` — **not found on disk, see §7.5**; this
whole table is quoted, not re-measured.

**Read the `TVS_DIST` deletion as evidence about the family's unbuilt normalisations.** The parent
family doc names four `dist_to_<overlay>_pct` columns as the *Trend overlay* family's
highest-leverage fix; **SRMIX-1** (the parent repo's 2026-08-30 support/resistance mixing batch)
built the `PSAR` and `ZIGZAG` ones and discharged the
momentum concern for `dist_to_psar_pct` (+0.676 median, 0 % of frames > 0.9). `Supertrend` and
`HALFTREND` remain **unbuilt** and the concern remains **open** for them. A distance to a *lagging*
stop line, ATR-normalised, is a momentum integrator, and the engine already carries 118
Oscillator/momentum columns. If those two are built, **measure them against `RSI`/`cmo` first.**

---

## 12. Gate ledger

| Gate | Verdict | Where the evidence is |
|---|---|---|
| A Correctness | PASS | literal Pine-order transliteration of L61–L87 in `tests/test_tvstop.py` (§3) |
| B Causality | PASS | 30-offset bidirectional future-perturbation sweep + 2 caught mutants (§5) |
| C Reachability | PASS pooled (~160×), PARTIAL per frame (24/89 below `min_support=30`, 0 empty) | §8 |
| D Scale-free | PASS — bit-identical at ×8, tolerance at ×10, NaN masks match | §6 |
| E Attribution | PASS as shipped (max +0.219132, n = 404,066) · **`TVS_DIST` FAILED at +0.930462 → deleted** | §7 |
| F Suites | PASS — 53 passed, `python -m pytest tests/test_tvstop.py -q`, 2026-09-07 | header table |

---

## 13. Provenance metrics

Machine-readable provenance for every number this page carries in a table. Format follows the
parent repo's knowledge-base v2 convention — `metric: value @ artifact/path` — and is parsed by
`tests/test_indref_pages.py`. A section registered here as `§n` is covered; a number in a table
outside a registered section, with no inline artifact citation and no `STUB:` token, **fails the
suite**.

⚠ `MISSING` below means the artifact was written on 2026-08-27 under the parent repo's gitignored
`backtest_results/tvpta6/` and is no longer on disk (checked 2026-09-07, §7.5). The value is quoted
from the durable record named alongside it. `MISSING` is a provenance statement, not an excuse: the
re-run command is in §7.5.

<!-- indref:metrics -->

| metric | n | @ artifact / provenance class |
|---|---|---|
| §0#P — header MEASUREMENT-LAW restatement of §6 values | n=7 | @ QUOTED — every one of these is repeated with its own row below; the header introduces no new number. @ ../Backtesting/docs/indicators/family-trend-overlay.md §6.5/§6.6 |
| §1#P — PSAR acceleration range 0.02 → 0.2 and `vmax` 0.3 | n=3 | @ docs/pine/7YXrxMjV-Terminal-Velocity-Stop-Lyro-RS.pine (vmax) and ../Backtesting/backtesting_engine/../pandas_ta/trend/psar.py (af range) |
| §3#T1 — licence version token | n=1 | @ docs/pine/7YXrxMjV-Terminal-Velocity-Stop-Lyro-RS.pine |
| §6#P — ML-suitability readings, MIXED — see the four rows that follow this one for the split | n=19 | @ QUOTED and reproducible in parts; @ tests/test_tvstop.py plus ../Backtesting/docs/indicators/family-trend-overlay.md §6.5 |
| §7#P — grid shape: 405,312 pooled bars, 1,434 cells = 1,428 + 6 | n=3 | @ ../Backtesting/scripts/analysis/measure_tvstop_overlap_full.py (MISSING csv) |
| §7.1#P — deletion narrative: +0.930462, pooled tallies, median/min |ρ| | n=11 | @ backtest_results/tvpta6/tvstop_overlap_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.6 |
| §7.1#T1 — per-frame ρ distribution, 6 cells × 4 stats | n=24 | @ backtest_results/tvpta6/tvstop_perframe_rho_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.6 |
| §7.2#P — shipped maximum in TVPTA-6 batch context | n=11 | @ backtest_results/tvpta6/tvstop_overlap_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.6 |
| §7.2#T1 — shipped maxima, 2 columns | n=4 | @ backtest_results/tvpta6/tvstop_overlap_20260827.csv (MISSING) |
| §7.3#P — band-vs-strict flip identity, P(flip|…), exclusion-list reading | n=21 | @ backtest_results/tvpta6/tvstop_flipident_20260827.csv and tvstop_support_discrim_20260827.csv (both MISSING); the nine-excluded-columns claim re-grepped 2026-09-08 @ ../Backtesting/backtesting_engine/strategy_miner.py |
| §7.3#T1 — sibling cells, 6 pairs | n=12 | @ backtest_results/tvpta6/tvstop_sibling_20260827.csv and tvstop_support_discrim_20260827.csv (MISSING) |
| §7.3#T2 — stop-lane grid, 11 rows × 3 columns | n=33 | @ backtest_results/tvpta6/tvstop_stoplane_20260827.csv (MISSING) |
| §7.4#P — travel tolerance disclosure, lane exceedance, PSAR gap Spearmans | n=21 | @ backtest_results/tvpta6/tvstop_travel_20260827.csv and tvstop_psar_gap_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.3 |
| §7.4#T1 — per-bar travel table, 6 lines | n=31 | @ backtest_results/tvpta6/tvstop_travel_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.3 |
| §7.5#P — restatement of §6's test-pinned and quoted values, plus the ±1.000000 back-reference in the eleven-name roll-call | n=5 | @ QUOTED — no new number; @ tests/test_tvstop.py and ../Backtesting/docs/indicators/family-trend-overlay.md §6.5 |
| §8#P — reachability reading: ~160× pooled clearance, 27 % of frames | n=5 | @ backtest_results/tvpta6/tvstop_reachability_20260827.csv (MISSING) |
| §8#T1 — reachability table, 2 columns | n=8 | @ backtest_results/tvpta6/tvstop_reachability_20260827.csv (MISSING) |
| §9#P — contamination narrative — measured half | n=28 | @ backtest_results/tvpta6/tvstop_contamination_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.9 |
| §9#P — contamination narrative — DERIVED half: the expected-flip products and the two-basis caveat | n=7 | @ DERIVED in-document 2026-09-08 from the flips/bars cells of the table above; NOT in any CSV and NOT in the durable records, which carry only the 2.14 % / 2.34 % rates |
| §9#T1 — contamination table — measured half | n=23 | @ backtest_results/tvpta6/tvstop_contamination_20260827.csv (MISSING) — QUOTED from ../Backtesting/docs/indicators/family-trend-overlay.md §6.9 |
| §9#T1 — contamination table — DERIVED half: the denominator caveat row and the expectation row | n=15 | @ DERIVED in-document 2026-09-08: 175 × (121/5,678) and 808 × (157/6,729); the bars−warm-up denominators 5,664 / 6,715 are INFERRED from 5,678−14 and 6,729−14 |
| §11#P — clamp-probe cross-correlations against TVS_DIST | n=5 | @ backtest_results/tvpta6/tvstop_clamp_probe_20260827.csv (MISSING) |
| §11#T1 — clamp-probe table, 3 rows | n=6 | @ backtest_results/tvpta6/tvstop_clamp_probe_20260827.csv (MISSING) |
| §12#T1 — gate ledger — restates §7 only | n=3 | @ QUOTED — no new number; @ backtest_results/tvpta6/tvstop_overlap_20260827.csv (MISSING) |

### Numbers with NO artifact and NO test — named individually

These four are quoted, pinned by nothing, and counted inside `§6#P` / `§(preamble)#P` above. They are
listed separately because a reader is entitled to know which numbers on this page rest on the family
doc alone.

| number | where it appears | status |
|---|---|---|
| `TVS_DIST` fixture range | §6, §(preamble) | QUOTED from `../Backtesting/docs/indicators/family-trend-overlay.md` §6.5 — **no artifact, no test.** `grep -rn` in `tests/` returns nothing for either endpoint. |
| real-data extremes (ARCLK.IS / GARAN.IS) | §6, §7.5 | QUOTED from the same source — **no artifact, no test.** |
| collapsed-ATR readings | §6, §(preamble) | QUOTED. `tests/test_tvstop.py::test_a_flat_patch_then_a_step_inflates_dist_far_beyond_mult` exercises this fixture but asserts only `> 10.0 × 3.0`, i.e. `> 30.0` — it does **not** pin either exact value. |
| clamp-tolerance and scale-invariance counts | §6 | **REPRODUCIBLE**, not quoted: `tests/test_tvstop.py::test_dist_above_mult_is_exactly_the_clamp_binding` and `tests/test_tvstop.py::test_scale_invariance`, re-run green 2026-09-07. |
