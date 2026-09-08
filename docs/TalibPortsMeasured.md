# TA-Lib ports — measured (TALIB-1)

The ten `port` rows of `../AlternativeRepos/altrepo_talib.csv`, one row per indicator, with
the number behind every gate. Reverted columns stay in the table: **the measurement is the
deliverable**, and a column that was built, measured and deleted is the expected outcome of
Gate E, not a failure.

Environment: `talib` 0.7.1, pandas 2.3.3, numpy 1.26.4. Measured 2026-09-08.

Reproduce:

```sh
python -m pytest tests/test_talib1_ports.py -q              # Gates A-D
cd ../Backtesting
python scripts/analysis/measure_talib1_overlap_full.py --stage 1   # cache, ~55 min
python scripts/analysis/measure_talib1_overlap_full.py --stage 2   # the grid
python scripts/analysis/measure_talib1_overlap_full.py --stage 3   # candidate x candidate
python scripts/analysis/measure_talib1_overlap_full.py --stage 4   # the stop lane, coerced
```

Outputs, under `../Backtesting/backtest_results/talib1/`:
`talib1_overlap_max.csv` (the verdict table), `talib1_overlap_top25.csv` (the 25 closest
comparators per column, so a maximum can be read as isolated or as a whole lane),
`talib1_reachability.csv` (Gate C, per ticker), `talib1_sibling_overlap.csv`,
`talib1_stop_lane.csv` (stage 4). `backtest_results/` is gitignored, so these are
reproducible rather than committed.

## How to read the columns

| column | meaning |
|---|---|
| Gate A max\|diff\| | largest absolute disagreement with `talib` on the bars TA-Lib itself publishes |
| n | comparable bars behind that number |
| warm-up | bars TA-Lib withholds (its declared lookback at unstable period 0), and the internal priming length the port had to reproduce |
| Gate D | scale-free verdict for the columns actually shipped |
| Gate E max ρ | largest \|Spearman ρ\| against the engine's full production column set |
| verdict | SHIP (\|ρ\| < 0.76) · DISCLOSE (0.76–0.90) · REVERT (≥ 0.90), taken over the numeric grid AND the three coerced non-numeric columns of stage 4 |

Gate A sample: 20 daily BIST frames drawn with `random.Random(0)` from
`../Backtesting/datastore/cache/*_1d.parquet`.

## The table

### Per indicator

| indicator | Gate A max\|diff\| | n | warm-up (TA-Lib lookback / internal priming) | Gate B | Gate C fires | Gate D | Gate E max \|rho\| (against, n) | verdict |
|---|---|---|---|---|---|---|---|---|
| `HT_DCPERIOD` | 1.26e-11 | 28,548 | 32 discarded / 12 primed | leak 0.0 | 405,405 / 89 frames | scale-free (bars) | **0.3729** (`ADX`, 405,405) | **SHIP** |
| `HT_DCPHASE` | 5.57e-10 | 27,928 | 63 discarded / 37 primed | leak 0.0 | 402,646 / 89 | scale-free (degrees) | **0.6203** (`WT2`, 402,646) | **SHIP** |
| `HT_PHASOR` → `HT_PHASOR_IP` | 1.87e-13 | 28,548 | 32 / 12 | leak 0.0 | 405,405 / 89 | raw is PX → ships as % of close | **0.7533** (`fisher_FISHERTs_9_1`, 405,405) | **SHIP** (near the 0.76 line) |
| `HT_PHASOR` → `HT_PHASOR_Q` | 3.18e-13 | 28,548 | 32 / 12 | leak 0.0 | 405,405 / 89 | raw is PX → ships as % of close | **0.4077** (`ebsw`, 404,782) | **SHIP** |
| `HT_SINE` → `HT_SINE` | 6.10e-12 | 27,928 | 63 / 37 | leak 0.0 | 402,646 / 89 | scale-free, bounded [-1, 1] | **0.5865** (`StochRSI_D`, 402,646) | **SHIP** |
| `HT_SINE` → `HT_LEADSINE` | 9.67e-12 | 27,928 | 63 / 37 | leak 0.0 | 402,646 / 89 | scale-free, bounded [-1, 1] | **0.7322** (`ppo_PPOs_12_26_9`, 402,646) | **SHIP** |
| `HT_TRENDMODE` | **0.0** | 27,928 | 63 / 37 | leak 0.0 | 402,646 finite, 337,054 in trend mode / 89 | binary 0/1 | **0.3585** (`BB_BWidth`, 402,646) | **SHIP** |
| `HT_TRENDLINE` → `HT_TRENDLINE_DIST` | **0.0** (on the level) | 27,928 | 63 / 37 | leak 0.0 | 402,646 / 89 | scale-free (%), but see verdict | **0.9576** (`bias`, 402,646) | **REVERT — column deleted** |
| `MAMA` → `MAMAd` | 2.67e-06 | 28,548 | 32 / 12 | leak 0.0 | 405,405 / 89 | scale-free (%), but see verdict | **0.9148** (`NWE_MID_200_8.0_8.0`, 390,453) | **REVERT — column deleted** |
| `MAMA` → `MAMAf` | 2.73e-04 (FAMA) | 28,548 | 32 / 12 | leak 0.0 | 405,405 / 89 | scale-free (%), but see verdict | **0.9408** (`QQE_RSIMA`, 405,405) | **REVERT — column deleted** |
| `SAREXT` → `SAREXTd` | **0.0** (on the level) | 29,168 | 1 / n/a | leak 0.0 | 408,164 / 89 | scale-free (%), but see verdict | **0.9850** (`dist_to_psar_pct`, 408,075) | **REVERT — column deleted** |
| `SAREXT` → `SAREXTs` | **0.0** (on the level) | 29,168 | 1 / n/a | leak 0.0 | 408,164, both states / 89 | binary ±1 | **0.9598** (`PSAR_Signal`, 408,075) — 0.8393 on the numeric grid alone | **REVERT — column deleted** |
| `IMI` | 1.42e-14 | 26,138 | 13 / n/a | leak 0.0 | 348,155 finite, 326,942 non-zero / 89 | scale-free, bounded [0, 100] | **0.7046** (`PRESSURE_PULSE_20_14_50_5`, 348,155) | **SHIP** |
| `BETA` | 4.9e-12 at p99.8; 3.4e+06 on 46 of 29,088 | 29,088 | 5 / n/a | leak 0.0 | 407,808 / 89 | scale-free (returns/returns) | **0.3610** (`DMP`, 407,007) | **SHIP**, but NOT registered (needs a benchmark) |

Gate E pool: 89 daily BIST_100 frames, **408,253 bars**, against **485** numeric
comparator columns from `IndicatorEngine(include_advanced=True).compute_all()` —
the production config, not `include_advanced=False`, which silently drops
`natr`. 28 of the 6,790 cells were degenerate (constant or n < 100) and are
reported rather than folded in; `TOD_SLOT_*` is hourly-only and all-NaN on
daily frames by design.

### The non-numeric comparators, and why stage 4 is not optional

`select_dtypes(include=[np.number])` silently drops three engine columns:
`Supertrend_Signal` and `PSAR_Signal` are OBJECT columns holding the literal
strings `"Bullish"` / `"Bearish"`, and `PSAR_Reversal` is bool. They are
invisible to the main grid — and `PSAR_Signal` is the single closest analogue
in the whole engine to a new SAR direction flag.

Stage 4 re-runs the stop lane with all three coerced to float. It changed a
verdict:

| column | numeric grid | with the three coerced | verdict |
|---|---|---|---|
| `SAREXTs_0.02_0.2` | 0.8393 (`dist_to_psar_pct`) → DISCLOSE | **0.9598** (`PSAR_Signal`) | **REVERT** |

The widened stage 4 measured **all fourteen** candidates against those three
columns, not just the stop-shaped ones — scoping it to `SAREXT*`/`HT_TREND*`/
`MAMA*` was a first-run mistake, because a candidate never measured against
the invisible comparators has an unmeasured corner. `SAREXTs` is the only one
that breaches 0.90; the eight columns that ship top out at **0.4302**
(`HT_LEADSINE` vs `Supertrend_Signal`).

### What that means, in one line each

* **8 columns SHIP into the sweep**: `HT_DCPERIOD`, `HT_DCPHASE`,
  `HT_PHASOR_IP`, `HT_PHASOR_Q`, `HT_SINE`, `HT_LEADSINE`, `HT_TRENDMODE`,
  `IMI_14`. Highest overlap among them: `HT_PHASOR_IP` at 0.7533.
* **`BETA_5` ships as a callable** but is deliberately never swept — it needs
  a benchmark series.
* **5 columns were DELETED on their own measurement**: `SAREXTd_0.02_0.2`
  (0.9850), `SAREXTs_0.02_0.2` (0.9598), `HT_TRENDLINE_DIST` (0.9576),
  `MAMAf_0.5_0.05` (0.9408), `MAMAd_0.5_0.05` (0.9148). The brief predicted
  rho ~ 0.9 reverts because TA-Lib and pandas_ta share heritage; that is
  exactly what happened, and every one is a "distance from a smoothed price",
  "distance from a SAR" or "SAR direction" shape the engine already carries.
* **Three whole indicators were emptied of features by that**: `ht_trendline`,
  `mama` and `sarext` now return TA-Lib's raw price levels, are OUT of
  `Category`, and are in `strategy`'s exclusion list. They remain callable so
  the ports are not lost and Gate A stays reproducible; `emit_dist=True`
  brings the deleted columns back for re-measurement only.
* **Sibling overlap** (`talib1_sibling_overlap.csv`, candidate × candidate,
  excluded from the main grid by construction): the highest surviving pair is
  `HT_DCPHASE` × `HT_LEADSINE` at −0.7881, which is expected — `HT_LEADSINE`
  is `sin(DCPhase + 45°)`. `HT_SINE` × `HT_LEADSINE` is 0.6795. Nothing among
  the eight shipped columns reaches 0.90 against another shipped column.

## Gate A — what was hard, and where the port is not exact

**Seven of the ten are one state machine.** `HT_DCPERIOD`, `HT_DCPHASE`, `HT_PHASOR`,
`HT_SINE`, `HT_TRENDLINE`, `HT_TRENDMODE` and `MAMA` are seven read-outs of the Hilbert
machinery in `pandas_ta/cycles/_hilbert.py`, not seven algorithms. That this is the right
shape was measured rather than assumed: with a single core, all seven reproduce `talib`.

**Two warm-ups, not one.** TA-Lib primes its 4-bar price smoother before the state machine
starts, and the priming length differs by declared lookback: **12 bars** for the lookback-32
read-outs (`HT_DCPERIOD`, `HT_PHASOR`, `MAMA`) and **37 bars** for the lookback-63 ones
(`HT_DCPHASE`, `HT_SINE`, `HT_TRENDLINE`, `HT_TRENDMODE`). Found by scanning 12..45 against
`talib` and taking the value that produced 0.0.

This is the trap in the whole task. At warm-up 12 the lookback-63 family is wrong by up to
**0.18 price units** (`HT_TRENDLINE`) and **70 degrees** (`HT_DCPHASE`) — and the error is a
warm-up transient that decays to *exactly zero* by roughly bar 700. `HT_DCPERIOD` is exact at
warm-up 12. So a port that used one warm-up everywhere and checked `HT_DCPERIOD`, or checked
only the tail of a long series, would have looked correct and shipped wrong.

**The Hilbert taps are summed in TA-Lib's order on purpose.** `_hilbert()` evaluates
`-a*x[t-6] + a*x[t] - b*x[t-4] + b*x[t-2]` in that sequence because that is the order
TA-Lib's `DO_HILBERT_*` macro accumulates its circular buffer in. The algebraically identical
one-expression form is a legal rewrite and a *numerically different* one: MAMA's alpha is
`fastlimit/deltaPhase` clamped to `[slowlimit, fastlimit]`, so a 1-ulp difference in the
ill-conditioned `atan(Q1/I1)` — and `I1` passes through zero whenever price goes flat, which
tick-rounded BIST data does constantly — flips alpha between 0.05 and 0.5. Measured on
`PETKM_IS_1d` (6,762 bars): reordered 1.11e-2 on MAMA, TA-Lib's order 2.7e-13.

**Where the port is deliberately not exact — two populations, both identified.**

* **MAMA / FAMA, 2.7e-06 / 2.7e-04.** All of it is one bar of one frame: `ISMEN_IS_1d` bar
  2327, where our detrender rounds to exactly 0.0 and TA-Lib's — which agrees with ours only
  to 1.9e-13, see `HT_PHASOR` — does not. The clamped alpha turns that knife edge into 0.05
  against 0.5 and the recursion carries it. Two other readings of the `I1 == 0` case were
  tried and measured: using `det[t-2]` gave 151.0, and treating the division as C's
  `Q1/0.0 → ±inf → atan → ±90°` gave 1.83. The shipped guard is the best of the three.
* **BETA, 3.4e+06 at the maximum.** Pooled over the 20 frames / 29,088 bars the median is
  4.4e-15 and p99.8 is 4.9e-12; **46 bars (0.158%)** exceed 1e-8. On those bars the median
  denominator `n·Sxx − Sx²` is **1.78e-14** against **7.47e-03** on the bars that agree.
  Runs of identical highs cancel TA-Lib's uncentred sum of squares to noise, and its own
  `denominator == 0` guard does not fire at 1.78e-14, so both sides are returning
  cancellation noise. The port keeps TA-Lib's algebraic form rather than a centred one,
  because Gate A is agreement with TA-Lib and a centred form would be a different indicator
  on exactly those bars.

## Gate B — causality

Prefix truncation cannot certify a recursion; it cannot see back-dating. The detector used is
future perturbation: add 50 to every bar from index J onward, and assert that nothing before
J moves. Every shipped column measures a leak of **0.0**. The detector is itself validated by
a mutant — `out["dcperiod"][t]` rewritten to `out["dcperiod"][max(t-25, 0)]`, `exec`'d in
memory — which the same test must catch, so a green result cannot come from a sleeping test.

## Gate D — what ships, and what does not

Four of the ten TA-Lib functions emit **price levels**: `HT_TRENDLINE`, `MAMA`, `FAMA` and
`SAREXT` (signed). A price level is not an ML feature — a tree cannot compare it with
`close` — so, following `pandas_ta/trend/pivot.py`, a scale-free companion was built for each.
**Gate E then killed every one of those companions.** Both facts belong in the same table:

| TA-Lib output | companion built | outcome |
|---|---|---|
| `HT_TRENDLINE` | `HT_TRENDLINE_DIST` = 100·(close/trendline − 1) | **deleted**, ρ +0.9576 vs `bias` |
| `MAMA`, `FAMA` | `MAMAd` = 100·(close/MAMA − 1), `MAMAf` = 100·(MAMA/FAMA − 1) | **both deleted**, ρ +0.9148 / +0.9408 |
| `SAREXT` | `SAREXTd` = 100·(close/\|SAR\| − 1), `SAREXTs` = sign(SAR) | **both deleted**, ρ +0.9850 / +0.9598 |
| `HT_PHASOR` inphase/quadrature | `HT_PHASOR_IP`, `HT_PHASOR_Q` = 100·component/close | **ship**, ρ 0.7533 / 0.4077 |

So the Gate D conversion succeeded on all four — the companions ARE scale-free — and Gate E
then found that three of the four were already in the engine under other names. Only
`HT_PHASOR`'s pair survived both gates.

`HT_DCPERIOD` (bars), `HT_DCPHASE` (degrees), `HT_SINE`/`HT_LEADSINE` (bounded [−1, 1]),
`HT_TRENDMODE` (binary), `IMI` (bounded [0, 100]) and `BETA` (returns over returns) are
already scale-free; that was verified, not assumed. All nine surviving columns (the eight
swept ones plus `BETA_5`) are **bit-identical** under ×8 and ×64 and agree to 1e-8 relative
under ×10 and ×3.7, with matching NaN masks. The four raw levels — `HT_TRENDLINE`, `MAMA`,
`FAMA`, `SAREXT` — are asserted to FAIL the same test, so the claim that they are price
levels is falsifiable rather than decorative.

The dictionary generator, which probes the live package independently, independently tags
every shipped column `SF` or `BIN` — see `docs/IndicatorDictionary.md`.

## Wiring

**Six are registered** in `Category` and reachable as `df.ta.<name>()`: `ht_dcperiod`,
`ht_dcphase`, `ht_phasor`, `ht_sine`, `ht_trendmode` (cycles) and `imi` (momentum).

**Four are callable but deliberately never swept** — absent from `Category` AND present in
`AnalysisIndicators.strategy`'s default exclusion list. Both halves are required:
`strategy("all")` enumerates *accessors*, so removing a name from `Category` alone still runs
it, and that took the multiprocessing pool down with a `ValueError` earlier in this batch.

| name | why it is not swept |
|---|---|
| `beta` | needs a second, BENCHMARK series a single-frame sweep cannot supply |
| `ht_trendline` | emits a PRICE LEVEL; its scale-free companion failed Gate E |
| `mama` | emits PRICE LEVELS; both scale-free companions failed Gate E |
| `sarext` | emits a signed PRICE LEVEL; both companions failed Gate E |

`Category` went **215 → 224 → 221**: +9 when all nine candidates were registered, then −3
when `ht_trendline`, `mama` and `sarext` were unregistered on their Gate E measurements. 215
is the value measured immediately before the TALIB-1 registration edit — a sibling batch was
adding indicators to the same file concurrently, so it is not a historical constant, and the
README / CLAUDE.md headline counts are reconciled once by the batch coordinator, not here.

## The coverage CSV

`../AlternativeRepos/altrepo_talib.csv` was regenerated with `docs/gen_altrepo_talib.py`
after the ports landed. **The gap went from 10 to 0.** The ten rows resolved as:

| verdict | rows |
|---|---|
| `have` (behaviourally identical to `talib` on the probe frame) | `HT_DCPERIOD`, `HT_DCPHASE`, `HT_SINE`, `HT_TRENDLINE`, `IMI`, `MAMA`, `SAREXT` |
| `port - alternate impl` | `BETA`, `HT_PHASOR`, `HT_TRENDMODE` |

Whole-CSV split after regeneration: `have` 43, `port - alternate impl` 30,
`n/a - routed to CANDLE-2` 61, `n/a - arithmetic helper` 26,
`unknown - not comparable` 1 — 161 rows, gap 0.

`HT_TRENDLINE`, `MAMA` and `SAREXT` read `have` *because of* the Gate E
reverts: with their derived columns deleted they emit TA-Lib's raw output
again, so the scanner's behavioural probe matches exactly. `alternate impl` is
the right verdict for the other three and not a hedge:

* `HT_PHASOR` ships the scale-free form rather than TA-Lib's raw output *by
  design* (Gate D above);
* `BETA` diverges by 4.17 on the 255-value probe frame — the ill-conditioned
  denominator described under Gate A, on a short synthetic series;
* `HT_TRENDMODE` agrees on all 197 overlapping values of the probe frame but
  withholds 63 bars that `talib` publishes, because `talib` returns an integer
  array which cannot carry the NaN its own 63-bar lookback implies.

`docs/verify_gap_rows.py ta-lib` reports `gap_rows: 0`, `reproducible: {}`,
`have_probed: 12`, `detected_have: 12`. `../AlternativeRepos/IndicatorList.md`
was regenerated from the CSV; `tests/test_indicator_list_tables.py` and
`tests/test_altrepo_talib_csv.py` are green (13 passed).
