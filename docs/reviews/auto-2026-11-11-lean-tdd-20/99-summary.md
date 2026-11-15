# Run summary — 2026-11-11, `lean-tdd-20`

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `lean-tdd-20` (issue #87) | **PASS** | 4 (REVISE, REVISE, PASS, PASS) | `pandas_ta/statistics/lean_tdd_20.py`, `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_lean_tdd_20.py`, `tests/test_altport2_ports.py`, `docs/measure_lean_tdd_20.py`, `docs/LeanTdd20Measured.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `README.md` | Gate E, run by the launcher; then a receipt session records the `docs/gate_e_ledger.csv` row and writes the measured numbers into the receipt's Gate E section |

Rounds 3 and 4 both returned PASS with no CRITICAL and no MAJOR finding. Each
round's MINOR/NIT findings were applied anyway, which is why four rounds ran:
a PASS counts only when nothing lands after it, and the cap is four.

## What the four rounds actually caught

Every MAJOR was a prose defect over a clean measurement — the repo's named
dominant defect, four times:

* a shipped docstring asserting what Lean's C# does ("its divisor is the
  window's current count") twenty-two lines after saying Lean's code was not
  read here;
* "three independent draws (one seed per sigma)" over a harness line that
  passed the same seed three times;
* a Gate D relative bound published as 1.0e-14 while the harness printed
  1.218341e-14;
* an invented C# identifier, `minimumTargetReturn`, in a file whose third
  paragraph promises nothing was typed from expectation.

No reviewer found a defect in the arithmetic, the causality, the wiring or a
pinned constant. All four rounds re-ran the harness and the suite themselves
rather than reading the prose.

## Gates, as committed

| gate | outcome |
|---|---|
| A correctness | three hand-derived windows exact to the bit (0.5, sqrt(0.125), sqrt(0.25/3)); bit-equal to the screen prototype AND to the prototype imported from `docs/issues/screen/ind_screen.py` on 1,480 of 1,480 fired bars; within 1.7e-18 of an exact-sum scalar loop; four open readings priced, four spellings shown identical |
| B causality | real module leaks 0 of 36 J on all eight frame-probe cells; four mutants, each caught 36 of 36 by a directed probe whose premise (exactly one return changed, and it is a shortfall) is itself measured |
| C reachability | fired 1,480 of 1,500 with 1,094 distinct values on a walk; level tracks sigma on three independent draws; asymmetry is what it adds (median ratio 3.17 at equal volatility); it does NOT order persistence. Real-data counts owed with Gate E |
| D scale-free | bit-identical under x8/x64 on three frames; x10/x3.7 within 7.2e-17 absolute, with the tie-breaking on a 37-value frame disclosed rather than hidden |
| E attribution | **owed** — the launcher runs it; the receipt says pending and the ledger is untouched |
| F suites | this worktree: 109 passed in the module, and 3 failed / 5,679 passed / 83 skipped in the full run, the three being the two Known breaks plus the owed ledger row. The launcher runs both repos' suites in clean worktrees |

## Receipts

* `docs/LeanTdd20Measured.md` — every number, with what is synthetic and
  what is owed said out loud.
* `docs/measure_lean_tdd_20.py` — reprints all of it.
* `00-manifest.md` — the seven assumptions taken without asking.
* `01-lean-tdd-20.md` — the four verdicts, quoted in full.
