# Liquidity trio — measured (`corwin_schultz`, `roll_spread`, `amihud`)

Issue #10 (migrated from `docs/issues/012-LIQUIDITY.md`), found by the ResearchIntel RAG
scan of 2026-10-22. Three estimates of trading cost / price impact from daily OHLCV
alone: Corwin-Schultz (2012) spread, Roll (1984) spread, Amihud (2002) illiquidity.

**Status: Gates A-D cleared (A/B/D as in the first session; C now has real-data counts
too); Gate E measured 2026-10-30 by the launcher's harness — all three columns verdict
`SHIP` under `r3-perframe-0.90` (none `STRUCK`, none `DISCLOSE`/`DISCLOSE_GAP`).** They
still ship as `df.ta.<name>()` accessors ONLY — held OUT of `Category` — because adding a
`Category` row requires a `docs/gate_e_ledger.csv` row
(`python docs/gate_e_ledger.py record <run dir> --measured 2026-10-30`), and that file is
outside this receipt session's allowed-to-modify set (see the issue-solver header). The
next session that has ledger access records the three rows and flips them into
`Category`; `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is what would catch a `Category` entry made without that row.

Shipped as **three modules** (see "Decisions" below), each one column:

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volatility/corwin_schultz.py` | volatility | `CS_1` | `[0, +inf)`, measured `[0, 0.0131]` |
| `pandas_ta/volatility/roll_spread.py` | volatility | `ROLL_20` | `[0, +inf)` or NaN, measured `[0.0278, 3.189]` |
| `pandas_ta/volume/amihud.py` | volume | `AMIHUD_21` | ratio to own history, measured `[0.371, 2.545]` |

Tests: `tests/test_corwin_schultz.py` (13), `tests/test_roll_spread.py` (11),
`tests/test_amihud.py` (13). Numbers: `python docs/measure_liq_proxy.py`. Environment:
pandas 2.3.3, numpy 1.26.4, Python 3.11.2. Measured 2026-10-30.

## Decisions (the issue's own list, made explicitly)

1. **One module with three columns, or three modules? Three modules.** `CLAUDE.md`'s
   architecture rule is "one indicator, one module," and these are three independent
   papers (Corwin & Schultz 2012, Roll 1984, Amihud 2002) answering three different
   questions, not three facets of one computation — unlike, say, `ichimoku_ml`'s eight
   columns from one indicator. Two land in `volatility` (`corwin_schultz`, `roll_spread`
   — both price-only, like `har_park`, `true_range`); `amihud` lands in `volume`, next to
   `mfi`/`vfi`/`cmf` — the existing convention for a column that combines price and
   volume. This also uses exactly the session's 3-new-file allowance.

2. **Amihud is not scale-free — normalised as a ratio to its own expanding median.**
   Raw Amihud (`mean(|r| / (P*V))`) scales with 1 / (currency × volume): a split, or
   comparing two tickers, moves it with no change in actual illiquidity. Of the issue's
   three options:
   - **log** does not survive a volume-only rescale: `log(illiq * k) = log(illiq) +
     log(k)`, additive, not cancelling.
   - **rolling rank** is scale-free but throws away magnitude — "twice as illiquid as
     usual" and "slightly more illiquid" become the same ordinal.
   - **ratio to its own rolling statistic** cancels the scale exactly (any constant `k`
     applied to price and/or volume for the whole series divides both the numerator and
     the implied baseline by the same `k`, which is what makes the ×8/×64 test below
     bit-identical) and keeps the magnitude. Chosen. It uses an *expanding* median (from
     inception, causal, one parameter) rather than a second rolling window, matching
     `maxvol_adv`'s peak/ADV ratio — the one other column in this repo with the same
     currency-scale problem.
   - First-bar boundary: the ratio of a value to a one-point median of itself is
     exactly `1.0`. This is a known degenerate case of a history-relative ratio with no
     history yet, not a bug — pinned by `test_hand_derived_value`.

3. **Roll: `cov(dp_t, dp_t-1) >= 0` reads NaN, not 0.** The issue flags this as
   "common." Measured (below): 604 of 1,179 post-warm-up synthetic bars (51.2%) — yes,
   common. `0` would claim "no cost here"; the model has no reading at all on these
   bars, which NaN states correctly and `0` does not. Same logic the repo already
   applies to `maxvol_adv`'s `NaN` where `ADV <= 0`.

4. **Corwin-Schultz: negative alpha is clipped to 0, matching AFML's own `getAlpha`
   exactly — not reverted to let negatives through.** `costs.py`'s cost-MODEL use of
   the same formula keeps negatives because a backtest P&L can net a negative cost
   against a later positive one; a FEATURE column has no such netting, so a negative
   "spread" is not a value a tree should see as a spread. **How often, measured on a
   1,200-bar synthetic walk (seed 11, tick 0.01):** clips (reads exactly 0) on
   **1,028 of 1,199 fired bars — 85.7%.** Re-measured with NO tick rounding at all:
   1,027 of 1,199 (85.6%) — essentially unchanged. **On this fixture the clip is NOT a
   tick-rounding artifact**, contrary to the issue's framing: it is Corwin-Schultz's own
   behaviour whenever a window's 2-day range is not much wider than its two single-day
   ranges (which a trending or volatile-relative-to-spread synthetic walk produces most
   of the time), tick-rounded or not. This is a synthetic measurement with a specific
   `spread_sigma`/`sigma` ratio, not a claim about real BIST ticks. **Real-data rate
   (Gate E's 89-frame run, 2026-10-30): clips to exactly 0 on 183,398 of 398,598
   non-NaN bars — 46.01%**, well under the synthetic fixture's 85.7%. "Many bars," as
   the issue says, not "most."

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (closed-form hand derivations, no module code reused) | **CS**: `high=e, low=1` on both bars of a 2-bar window gives `beta=2, gamma=1`, and `alpha` reduces symbolically to exactly `1`, so `CS = 2*tanh(0.5)` — matched to `1e-12`. Flat window (`high==low`) reads exactly `0`. **ROLL**: close alternating 100/101 (textbook bounce) gives `cov = -4/3` exactly and `ROLL = 4/sqrt(3)` at `length=4` — matched to `1e-9`. A pure uptrend (`cov == 0` exactly) reads NaN. **AMIHUD**: close 100→110→99, volume 1000/2000/1500, `length=1` gives `illiq[1]/illiq[2] = 0.675` exactly and `AMIHUD[2] = 80/67` — matched to `1e-9`. All three additionally checked against an independent per-bar loop (raw numpy, not the module's rolling calls) at several interior bars. |
| B Causality | pass, by measurement | Future-perturbation sweep (31 offsets, real module leaks at 0/31 for all three) plus one `importlib`-read, `exec`'d-in-memory look-ahead mutant per module. **CS** and **ROLL**'s mutants have a reach of exactly one bar below the perturbation boundary, so a boundary bar where both the real and mutant value are masked (CS's alpha clips to 0 on 85.7% of bars; ROLL's cov is non-negative on 51.2%) hides the leak there — measured catch: **CS 9/31, ROLL 18/31**. This is the `smc_sweep`/CANDLE-1 lesson applied directly: a test that checked only one offset would have had a 71% (CS) / 42% (ROLL) chance of missing the bug. **AMIHUD**'s mutant (low NaN rate, 1.8%) is caught at **31/31**. |
| C Reachability | synthetic + real | Synthetic, 1,200-bar fixture (seed 11/12/13, tick 0.01): **CS** fires 1,199/1,200, 172 distinct, 1,028 clipped to 0. **ROLL** fires 575/1,200 (604 of 1,179 post-warm-up bars NaN from `cov >= 0`), 575 distinct. **AMIHUD** fires 1,179/1,200, 1,175 distinct. Real data — 89 ALTPORT-1 BIST frames, 398,849 pooled bars, from the same Gate E run's `overlap_max.csv` (`non_nan`/`non_zero` columns): **CS\_1** non-NaN on 398,598/398,849 bars (99.94%, NaN 0.06%); of those, **reads exactly 0 on 183,398 (46.01%)** and fires non-zero on 215,200 (53.99%) — this is the issue's own question ("count how often it happens on real data") and the answer is roughly half, well under the synthetic fixture's 85.7%, so the synthetic rate overstated the real one. **ROLL\_20** non-NaN (finite) on 225,954/398,849 (56.57%; NaN 43.43% from `cov >= 0`, also "common" on real data), and every finite value is non-zero (225,954/225,954). **AMIHUD\_21** non-NaN on 387,045/398,849 (97.04%; NaN 2.96%), every finite value non-zero. |
| D Scale-free | pass | **CS**/**ROLL** (price-only): ×8/×64 bit-identical (`max|diff| = 0.0`, NaN masks matching); ×10/×3.7 within `6.65e-16`/`8.85e-16` (CS) and `7.15e-13`/`4.19e-13` (ROLL). **AMIHUD** (price AND volume axes, independently — the issue's own flagged risk): ×8/×64 bit-identical on BOTH axes; ×10/×3.7 within `7.11e-15`/`6.66e-15` (price) and `8.88e-16`/`6.66e-16` (volume). `0 < fires < n` plus > 100 distinct values, all three. |
| E Attribution | **measured 2026-10-30**, launcher's harness (`gate_e_overlap.py run --module pandas_ta.volatility.corwin_schultz` / `.roll_spread` / `pandas_ta.volume.amihud`), bands `r3-perframe-0.90`, 89 ALTPORT-1 frames, 687 comparators (329 `compute_all` + 358 manifest `1d`) | **CS\_1**: pooled max\|ρ\| `0.5671` vs `THERMO_pct_Pctl` (manifest, n=393,406); per-frame max median\|ρ\| `0.5656` vs the same comparator, 0/89 frames ≥0.90. Verdict **SHIP**. **ROLL\_20**: pooled max\|ρ\| `0.5375` vs `natr` (compute_all, n=225,954); per-frame max median\|ρ\| `0.5093` vs `natr`, 0/89 frames ≥0.90. Verdict **SHIP**. **AMIHUD\_21**: pooled max\|ρ\| `0.6431` vs `pvi` (compute_all, n=387,045); per-frame max median\|ρ\| `0.7979` vs `ZIGZAG` (89 frames, 3/89 = 3.37% of frames ≥0.90). Verdict **SHIP** — `expected_verdict` (`docs/gate_e_ledger.py`) bands DISCLOSE/DISCLOSE_GAP/SHIP off the pooled max only (`0.6431 < 0.76`), and STRUCK needs pooled **or** per-frame-median ≥ 0.90, which neither hits. **No column STRUCK; nothing to revert.** Run facts (`meta.json`, all three): `pandas_ta_src_sha1 65bad80a99b94ab97145d275cf405f3c15916432`, canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, `n_frames=89`, `pooled_bars=398849`. Full outputs: `is10-corwin_schultz-270316bb`, `is10-roll_spread-270316bb`, `is10-amihud-270316bb` (launcher run `20261030-003934-10`). |
| F Suites | this repo only | `python -m pytest -q` (2026-10-30, this receipt session, doc-only change): **2 failed / 3,295 passed / 83 skipped** — unchanged from the prior session, same two pre-existing failures (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, both CLAUDE.md "Known breaks"), neither naming `corwin_schultz`/`roll_spread`/`amihud`. `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` passes because the three are still accessor-only, not in `Category`. Parent repo's suite run by the launcher, not here. |

## Proxy overlap (NOT Gate E)

Spearman ρ on one synthetic 3,000-bar GBM walk (σ = 0.02, seed 1, tick 0.01):

| column | vs | ρ |
|---|---|---|
| `CS_1` | `NATR_14` | −0.1741 |
| `CS_1` | `TRUE_RANGE` (% of close) | −0.4144 |
| `CS_1` | `RVI_14` | −0.0111 |
| `ROLL_20` | `NATR_14` | 0.1808 |
| `ROLL_20` | `TRUE_RANGE` (% of close) | 0.0197 |
| `ROLL_20` | `RVI_14` | −0.1070 |
| `AMIHUD_21` | `MFI_14` | −0.1247 |
| `AMIHUD_21` | `CMF_20` | −0.0011 |
| `AMIHUD_21` | `VFI_14` | n/a — `VFI_14` is constant on this fixture; inconclusive, not reported as a number |

n (CS & ROLL both finite) = 1,814; n (AMIHUD finite) = 2,979. All measured |ρ| are well
under even the DISCLOSE band (0.76); this is a weak proxy signal on one synthetic walk,
not a Gate E substitute — the real engine's 687 comparators over 89 BIST frames may
differ. CS and ROLL correlate with each other only through the shared H/L-vs-close-change
structure of the walk; this fixture does not test that directly.

## To close

Gate E is measured (above): all three `SHIP`, none `STRUCK` — **nothing to revert**.
What is left is pure wiring, blocked only by this receipt session's file permissions,
not by any gate result:

1. A session with write access to `docs/gate_e_ledger.csv` records the three rows
   (`python docs/gate_e_ledger.py record <run dir> --measured 2026-10-30`, once per
   module, from the launcher's three run directories), then adds the three to
   `Category` (`pandas_ta/__init__.py`) and reinstates the `in ta.Category[...]`
   assertions in `tests/test_amihud.py` / `test_corwin_schultz.py` / `test_roll_spread.py`
   and the counts in `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`
   and `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL`/`CATEGORY_BUCKETS` — the same
   follow-through `efc5499` reverted, now in the other direction.
2. Both repos' suites green: this repo's `python -m pytest -q` result for this session
   is in the Gate F row above; parent repo run by the launcher.
