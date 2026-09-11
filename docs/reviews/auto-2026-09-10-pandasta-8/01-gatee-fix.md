# 01 — GATEE-FIX (prerequisite, from `../Backtesting/TODO.md` TVPTA-9)

Pulled into this run by the owner's Phase 2 answer: *"Fix Gate E inside this run
first."* Scoped to the harness change and the ALTPORT screen. The retroactive
re-run of prior measurements stays with TVPTA-9.

## The defect

Every `measure_*_overlap_full.py` picked comparators with
`select_dtypes(include=[np.number])`. **17 call sites**, measured:

```
$ grep -rn "select_dtypes" scripts/analysis/measure_*.py | wc -l
17
```

The engine emits **492 columns, of which 7 are non-numeric** — so every Gate E
verdict this repo has taken was against **485** comparators and did not say so.

| column | dtype | levels |
|---|---|---|
| `Supertrend_Signal` | object | Bearish / Bullish |
| `PSAR_Signal` | object | Bearish / Bullish / **No_Data** |
| `QQE_Signal` | object | Bearish / Bullish / **No_Data** |
| `TD_Seq_Signal` | object | Bearish / Bullish / **No_Data** |
| `TREND_DIRECTION` | object | DOWN / UP |
| `FIB_ZONE` | object | BELOW_618 / ZONE_618 / ZONE_500 / ZONE_382 / ABOVE_236 / **NONE** |
| `PSAR_Reversal` | bool | False / True |

## The fix

`scripts/analysis/_comparators.py` — ONE coercion surface, the same structural
answer `docs/_altrepo_resolve.py` gave the altrepo scanners.

**It does NOT factorize blindly.** Spearman is a rank correlation; arbitrary
`factorize()` codes produce a number whose rank order is an artifact of
whichever category appeared first, unstable across frames. Every categorical the
engine emits is mapped through an EXPLICIT ORDERED scale, and anything unknown
returns all-NaN and is REPORTED as `unmapped` rather than silently coded.

**`No_Data` and `NONE` are sentinels, not levels** — they map to NaN. Coding them
as a third category would put "missing" on the same ladder as "bearish".

Measured after the fix, one BIST daily frame:

```
report: {'n_total': 492, 'n_numeric': 485, 'n_bool': 1, 'n_ordered': 6, 'n_unmapped': 0}
comparators: 492   (was 485 numeric-only)
PSAR_Signal    -> [-1.0, 1.0]              nan=2
FIB_ZONE       -> [0.0, 1.0, 2.0, 3.0, 4.0] nan=19
```

## It reproduces the finding that motivated it — and the published figure was a FLOOR

`SAREXTs` (TA-Lib's SAR direction flag, restored via `emit_dist=True`) against
the engine's existing direction columns, 10 BIST daily frames:

| comparator | frames | max abs rho | mean |
|---|---|---|---|
| **`PSAR_Signal`** | 10 | **1.0000** | **0.9656** |
| `QQE_Signal` | 10 | 0.6617 | 0.5998 |
| `Supertrend_Signal` | 10 | 0.3889 | 0.3019 |

TALIB-1 published **0.9598** for this pair and reverted the column on it. That
number was the floor, not the ceiling: on the worst frame the two are **rank
identical**. The revert was right and was under-argued.

⚠ On the numeric-only grid this pair did not exist at all. `SAREXTs` was
measured at **0.8393** against 485 columns and was on course to ship with a
disclosure.

## Status

Harness surface written and verified. **NOT yet wired into the 17 call sites** —
that is TVPTA-9's retroactive half and stays in `../Backtesting/TODO.md`.
ALTPORT-1 imports `_comparators.comparator_frame` directly, which is what the
owner's answer required.
