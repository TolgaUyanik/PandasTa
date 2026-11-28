# Implementing an indicator

From a source to a green suite, in order. Gate thresholds, the causal / scale-free contract and the
companion-column rules are not restated here: they live in [`CLAUDE.md`](../CLAUDE.md) (porting
sections, the ML feature contract) and [`docs/MLCompanionContract.md`](MLCompanionContract.md).
`tests/test_impl_doc.py` checks the touch points and categories below against the package.

## Touch points

`python docs/new_indicator.py <category> <name>` writes exactly these, each by sort order:

- `pandas_ta/<category>/<name>.py` — the indicator (body returns None until you write it)
- `pandas_ta/<category>/__init__.py` — one import line
- `pandas_ta/__init__.py` — one `Category` line
- `pandas_ta/core.py` — one `df.ta.<name>()` accessor
- `tests/test_<name>.py` — Gate B / C / D tests that fail until the indicator is real

Categories: `candles`, `cycles`, `momentum`, `overlap`, `performance`, `statistics`, `trend`,
`volatility`, `volume`.

No count anywhere needs a bump (#331): the README, the contract and the dictionary carry none.

## Steps

1. **Check it is new.** Search `docs/IndicatorDictionary.md` and `docs/EquivalentStrategies.md` for
   the formula and the name. A restatement of a shipped column is not a port.
2. **Scaffold.** `python docs/new_indicator.py <category> <name>`. It refuses a taken name and
   writes nothing then. `git status` shows the five paths above.
3. **Write the indicator.** Replace the `result = None` line with the computation, reading only bars
   `<= t`. Ship a scale-free column (a ratio or a distance, not a price level). The column name
   encodes the parameters. Cite the source in the module docstring.
4. **Gate A — correctness, by source kind** (strongest first):
   - *Pine script*: line by line against the source, citing its line numbers.
   - *TA-Lib*: cite the C function; `talib` is a dev-only oracle, imported by tests only.
   - *Another Python library*: compare in a subprocess against a pinned version; never copy its code.
   - *Paper or book*: a fixture computed by hand from the definition. The weakest of the four:
     say so in the receipt.
5. **Gates B, C, D.** Run `python -m pytest -q tests/test_<name>.py`. The scaffolded tests are the
   floor: a source-exec mutant that reads one bar ahead must be caught, x8 / x64 bit-identical,
   x10 / x3.7 within tolerance, not constant. Add the Gate A test, then rewrite the test module's
   docstring with what is pinned and the measured numbers. Gate C on real data is owner-only (the
   data lives in the private repo).
6. **Regenerate the dictionary.** `python docs/gen_indicator_dictionary.py docs/IndicatorDictionary.md`.
   It adds your row and your shortlist line; nothing else should move.
7. **Write the receipt.** `docs/<Name>Measured.md`: every number from a run, with the command that
   produced it.
8. **Gate E (owner-only).** The harness runs in the private repo; CI on `dev` marks the ledger row
   as owed until the owner records it with `python docs/gate_e_ledger.py record <run dir>
   --measured YYYY-MM-DD`.
9. **Gate F.** `python -m pytest -q` here; the private repo's suite is owner-only.
10. **Open the PR into `dev`.** The merge queue takes it from there.

`docs/gen_indicator_pages.py` (the per-indicator pages under `docs/indicators/`) is a batch run by
the owner, not a port step: it rewrites every page from its fact cache.
