# WAVEPM-14-100 — `wavepm` measured (PandasTa issue #261)

**Port:** `pandas_ta/volatility/wavepm.py` → one column, `WAVEPM_14_100`
(`WAVEPM_{length}_{lookback}`).
**Source:** Mark Whistler, *Volatility Illuminated* (c. 2016), "Wave PM" (Price Mass). No text
of the book with a formula was readable (issue #261, 2026-11-08). The definition is finta's
`WAVEPM` (`finta/finta.py`, LGPL-3.0) as transcribed in the issue: the standard deviation is
divided by the mean, and finta's constant 3.2, which multiplies both numerator and denominator,
cancels and is left out. The math is ported, not the code. The ProRealCode port (which does not
divide by the mean) is the reading not taken (§A4). Nothing here tests predictive value.
**Status (2026-11-26): Gate A cleared against finta's own code (§A0). Gate E DISCLOSE_GAP,
0.8088 vs `CHOP` (§E).** §A0 and §E were added at merge time and are NOT printed by
`docs/measure_wavepm.py`: §A0 comes from `tests/test_wavepm.py::test_gate_a_matches_finta_wavepm`,
§E from the Gate E harness run recorded in `docs/gate_e_ledger.csv`.
**Measured:** 2026-11-23, on this tree, by `python docs/measure_wavepm.py`
(pandas 2.3.3, numpy 1.26.4). Every figure below is printed by that script.

    r[T]          = std(close, 14)[T] / sma(close, 14)[T]          (ddof = 0)
    WAVEPM_14_100 = tanh(r[T] / sqrt(mean(r[T-99 .. T] ** 2)))     in [0, 1) for prices

---

## ⚠ What this port does NOT establish

- **Gate C on real data** is measured only as the Gate E run's counts (§E): 388,881 non-NaN,
  388,879 non-zero bars pooled over the 89 frames. Every count in §C is synthetic.
- **Non-redundancy (§F) is synthetic.** It is a disclosure, not Gate E.

---

## A0 Gate A — finta's own code

finta's `WAVEPM` is on its GitHub master only; no PyPI release carries it (1.3 has none).
Source: peerchemist/finta@af01fa5 `finta/finta.py` L2262-L2303.

- L2279-L2280: `ma = rolling(period).mean()`, `std = rolling(period).std(ddof=0)` — mu, sigma.
- L2299-L2300: `dev = 3.2 * std`, `power = (dev / ma) ** 2` — 3.2² · r².
- L2293-L2295: `variance = rolling(lookback).sum(power) / lookback`, `calc_dev = sqrt(variance) * ma`,
  `y = dev / calc_dev` — 3.2 · r · mu / (3.2 · rms · mu) = r / rms, so the 3.2 cancels.
- L2282-L2290: a hand-written tanh, (1 − e^{−2x}) / (1 + e^{−2x}) for x > 0 and its mirror
  otherwise — tanh(x).
- Warm-up: finta's rolling windows use the default `min_periods` = window, so it is NaN on the
  same first length + lookback − 2 bars; a zero rms gives 0/0 = NaN in both.

`tests/test_wavepm.py::_finta_wavepm` transcribes those lines (constant and tanh included).
Against it the module has identical NaN masks on all eight frames, max |diff| 3.33e-16 on the
seven moving frames (2.22e-16 on `coarse`).

## A1 Gate A — the issue's finta form by explicit loops

`_oracle` sums every window bar by bar. It uses no rolling window and shares no code with the module.

| frame | fired | masks | max \|diff\| |
|---|---:|---|---:|
| walk | 1388 | True | 3.249e-11 |
| trend | 1388 | True | 6.693e-12 |
| range-bound | 1388 | True | 3.269e-13 |
| grid | 1388 | True | 2.367e-12 |
| heavy-tailed | 1388 | True | 1.187e-11 |
| jump | 1388 | True | 3.833e-12 |
| flat | 0 | True | — |
| coarse | 1388 | True | 1.046e-11 |
| **pooled** | **9,716** | | |

The column is not bit-equal to the oracle, because pandas' rolling sums are online. Other windows
on `walk` / `coarse`, with masks equal, give max |diff|: (5, 20) 3.147e-10 / 4.996e-15,
(20, 50) 1.066e-11 / 2.315e-12, (30, 200) 4.194e-12 / 2.555e-12. A hand frame
(`test_gate_a_hand_frame`, length 2, lookback 2) pins r = 0 → 0.0 and one tanh value by hand.

## A4 The readings not taken

| frame | ddof 0 vs ddof 1, max \|diff\| | ProRealCode (no /mean), Spearman | ProRealCode, max \|diff\| |
|---|---:|---:|---:|
| walk | 3.331e-16 | 0.9902 | 0.0779 |
| trend | 3.886e-16 | 0.9982 | 0.0879 |
| range-bound | 3.331e-16 | 0.9961 | 0.0363 |
| grid | 3.331e-16 | 0.9909 | 0.0543 |
| heavy-tailed | 3.331e-16 | 0.9940 | 0.0755 |
| jump | 3.331e-16 | 0.9942 | 0.0882 |
| coarse | 5.551e-16 | 0.9777 | 0.0786 |

ddof rescales every r by the same constant, which cancels in r / rms, so the choice does not
matter. The ProRealCode reading is a close relative but a different column.

## B Gate B — causality

| frame | module | mean-lead | std-lead | rms-lead | output-early |
|---|---:|---:|---:|---:|---:|
| walk | 0 | 36 | 36 | 36 | 36 |
| trend | 0 | 36 | 36 | 36 | 36 |
| range-bound | 0 | 36 | 36 | 36 | 36 |
| grid | 0 | 36 | 36 | 36 | 36 |
| heavy-tailed | 0 | 36 | 36 | 36 | 36 |
| jump | 0 | 36 | 36 | 36 | 36 |
| flat | 0 | 0 | 36 | 36 | 36 |
| coarse | 0 | 36 | 36 | 36 | 36 |

The table counts catches out of 36 tail offsets (1464..1499). The mutants are read off the
shipped source, edited by one `.shift(-1)` each, and `exec`'d in memory. With every bar except
bar 0 as a split point, the module is caught on 0 of 1,499 on all eight frames. On unperturbed
`walk`, each mutant moves 1,387 of the 1,387 bars where both fire.

## C Gate C — reachability (synthetic)

| frame | fired | first | distinct | == 0 | > 0.5 | > 0.9 | min | max | mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| walk | 1388 | 112 | 1388 | 0 | 1163 | 141 | 0.2658 | 0.9794 | 0.6891 |
| trend | 1388 | 112 | 1388 | 0 | 1132 | 166 | 0.2081 | 0.9921 | 0.6761 |
| range-bound | 1388 | 112 | 1388 | 0 | 1236 | 144 | 0.2587 | 0.9768 | 0.6982 |
| grid | 1388 | 112 | 1388 | 0 | 1159 | 155 | 0.2184 | 0.9917 | 0.6839 |
| heavy-tailed | 1388 | 112 | 1388 | 0 | 982 | 150 | 0.0558 | 0.9979 | 0.6185 |
| jump | 1388 | 112 | 1388 | 0 | 1116 | 125 | 0.0915 | 1.0000 | 0.6533 |
| flat | 0 | — | | | | | | | |
| coarse | 1388 | 112 | 1286 | 99 | 1225 | 104 | 0.0000 | 0.9737 | 0.6892 |

The warm-up is exactly length + lookback − 2 = 112 bars. Every frame's max is below tanh(10),
the bound at lookback 100: r² ≤ 100 · rms². (`jump`'s 1.0000 is a rounding of a value below that
bound.) `coarse` reads exactly 0.0 on 99 bars, where the 14-bar window holds a single price.
`flat` fires nowhere, because rms = 0.

## D Gate D — scale

| frame | x8 | x64 | x10 max \|diff\| | x3.7 max \|diff\| | masks |
|---|---|---|---:|---:|---|
| walk | True | True | 3.384e-11 | 1.705e-11 | True |
| trend | True | True | 1.465e-11 | 6.082e-12 | True |
| range-bound | True | True | 4.904e-13 | 2.617e-13 | True |
| grid | True | True | 3.744e-12 | 3.174e-12 | True |
| heavy-tailed | True | True | 6.024e-11 | 8.753e-11 | True |
| jump | True | True | 3.790e-12 | 4.566e-12 | True |
| flat | True | True | — | — | True |
| coarse | True | True | 6.835e-12 | 1.405e-11 | True |

At price levels 1e-6, 1e+6 and 1e+100, each frame fires on 1,388 bars and x8/x64 is
bit-identical. The values sit within 6.807e-11 / 2.741e-11 / 3.667e-11 of level 100.

## F Non-redundancy (SYNTHETIC, a disclosure — not Gate E)

| comparator | median \|ρ\| | max \|ρ\| |
|---|---:|---:|
| raw r = std14/sma14 (not shipped) | 0.9301 | 0.9679 |
| `chop` `CHOP_14_1_100` | 0.7930 | 0.8721 |
| `er` `ER_10` | 0.5462 | 0.7344 |
| `natr` `NATR_14` | 0.3938 | 0.5895 |
| `j_damiani` `J_DAMIANI_13_40` | 0.3773 | 0.5496 |
| `bbands` `BBB_5_2.0` | 0.3302 | 0.3751 |

The medians are per frame over the seven moving frames. `CHOP_14_1_100` sits in the 0.76–0.80
DISCLOSE band on these synthetic frames. Gate E on real data decides the verdict: DISCLOSE_GAP (§E).

## G Bad bars

A NaN, +inf or −inf close at bar 700 of `walk` moves 0 earlier bars. It empties 113 bars
(700 .. 812), and the 687 bars after them fire. The output is bit-identical to a NaN plant. There
is no mask: pandas' rolling windows already return NaN over an infinity. A mask was written,
measured as a no-op, and deleted.

## L Short and degenerate frames

A 112-bar frame is refused (`None`). A 113-bar frame fires 1 bar, and a 117-bar frame fires 5.
Frames of all NaN, all 0.0, all −5.0 or all 100.0 fire on 0 bars and raise nothing. The negated
`walk` fires 1,388 bars in [−0.9794, −0.2658], the exact negative of the positive column.

## M Wiring counts (read back from the package)

380 registered in `Category`; volatility bucket 39. The dictionary has 725 tagged columns
(SF 359, PX 137, BIN 104, ORD 59, CONST 43, ?? 21, PX2 2). Its row: `WAVEPM_14_100` `SF`,
warm-up 112.

## W / Z

The docstring's first paragraph is 131 characters, and the dictionary's `desc()` cut returns it
whole. Cost on this machine: about 10 ms for 100,000 bars and about 35 ms for 400,000 bars, varying
from run to run (two runs printed 8–10 ms and 33–35 ms). Peak memory was about 6 MB and
about 23 MB.

## E Gate E — real data (2026-11-26)

`gate_e_overlap.py run --module pandas_ta.volatility.wavepm --name pr378-wavepm`, 89 BIST
frames, 687 comparators, recorded in `docs/gate_e_ledger.csv`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---:|---|---:|---:|---|
| `WAVEPM_14_100` | 0.8088 | `CHOP` (compute_all) | 388,831 | 0.8200 (`CHOP`) | DISCLOSE_GAP |

Next comparators: `BB_BWidth_Pctl` (manifest) 0.7184, `chop` 0.7004. DISCLOSE_GAP is not STRUCK,
so no waiver is needed; the overlap with `CHOP` is disclosed here. Share of frames with a
per-frame |ρ| ≥ 0.90: 0.0.
