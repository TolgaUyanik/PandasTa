# -*- coding: utf-8 -*-
"""MULTIL-0: the length grid feeds an engine change, so it gets a guard.

The first version of this artifact shipped three CRITICAL defects, and none of
them would have failed anything, because there was no test:

* the docstring claimed the **Grid A / BIST_100** universe while the selector
  `os.listdir`-ed the cache and took the first 40 files in ASCII order -- 12 of
  40 were BIST_100, and the sample stopped at the letters "AN";
* Spearman coefficients were pooled with `np.mean`, which is biased near 1;
  Fisher-z moved `sma 10/50` 0.8907 -> 0.9338 and `ema 50/200` 0.8609 -> 0.9206,
  i.e. two rows labelled shippable were in the revert band;
* the deliverable was "a table AND a kept set"; only the table existed, and a
  list of surviving PAIRS is not a set (`rsi` 7/28 and 7/50 both clear while
  28/50 reverts at 0.956).

So these guards pin the universe, the pooling, the band arithmetic, and the
transitivity of the kept set.
"""
import csv
import os
from itertools import combinations

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FORK = os.path.dirname(_HERE)
GEN = os.path.join(_FORK, "docs", "gen_multil_length_grid.py")
GRID_CSV = os.path.join(_FORK, "docs", "multil_length_grid.csv")
KEPT_CSV = os.path.join(_FORK, "docs", "multil_kept_set.csv")

REVERT = 0.90
DISCLOSE = 0.76


def _rows(path):
    if not os.path.exists(path):
        pytest.skip(f"{path} absent")
    with open(path, encoding="utf8") as fh:
        return list(csv.DictReader(fh))


def test_the_generator_and_both_artifacts_exist():
    assert os.path.exists(GEN), GEN
    assert os.path.exists(KEPT_CSV), (
        "the kept set is half the MULTIL-0 deliverable and is missing; a table "
        "of pairwise rho is not a kept set"
    )


def test_the_band_constants_match_the_documented_gate():
    """0.90 / 0.76 come from CLAUDE.md's Gate E. Drift breaks the verdicts."""
    text = open(GEN, encoding="utf8").read()
    assert "REVERT = 0.90" in text, "revert band no longer 0.90"
    assert "DISCLOSE = 0.76" in text, "disclosure band no longer 0.76"
    claude = open(os.path.join(_FORK, "CLAUDE.md"), encoding="utf8").read()
    assert "0.76" in claude and "0.9" in claude, (
        "CLAUDE.md no longer documents the Gate E bands this script applies"
    )


def test_every_verdict_follows_from_its_own_rho():
    """The verdict column must be derivable from the number beside it.

    Not a restatement: a hand-edited verdict, or a band applied to the arithmetic
    mean instead of the pooled value, fails here.
    """
    wrong = []
    for row in _rows(GRID_CSV):
        rho = abs(float(row["spearman_z_pooled"]))
        above = int(row["frames_above_revert"])
        frames = int(row["frames"])
        if rho >= REVERT:
            expected = "revert - redundant"
        elif above > frames / 2:
            expected = "revert - redundant (majority of frames)"
        elif rho >= DISCLOSE:
            expected = "ship with disclosure"
        else:
            expected = "ship"
        if row["verdict"] != expected:
            wrong.append((row["indicator"], row["length_a"], row["length_b"],
                          row["verdict"], expected))
    assert wrong == [], f"verdicts that do not follow from their rho: {wrong}"


def test_pooling_is_fisher_z_not_an_arithmetic_mean():
    """Both columns are emitted; they must actually differ somewhere.

    If `spearman_z_pooled` were quietly set to the arithmetic mean, every band
    decision would silently revert to the biased estimator that produced two
    false all-clears.
    """
    rows = _rows(GRID_CSV)
    assert rows and "spearman_z_pooled" in rows[0], "no pooled column"
    assert "spearman_mean_arith" in rows[0], "the arithmetic mean is not shown"
    differ = [r for r in rows
              if abs(float(r["spearman_z_pooled"])
                     - float(r["spearman_mean_arith"])) > 1e-6]
    assert differ, (
        "the z-pooled and arithmetic columns are identical on every row; "
        "pooling has reverted to np.mean"
    )
    # And z-pooling must be the one that is >= the arithmetic mean near 1,
    # which is the whole reason it matters.
    high = [r for r in rows if float(r["spearman_mean_arith"]) > 0.8]
    assert all(float(r["spearman_z_pooled"]) >= float(r["spearman_mean_arith"])
               - 1e-9 for r in high), (
        "z-pooled fell below the arithmetic mean on a high-correlation row; "
        "the transform is wrong"
    )


def test_the_kept_set_is_transitively_clean():
    """Every PAIR inside a kept set must clear the band, not just some.

    `rsi {7,28,50}` passes a pair-by-pair eyeball and contains a 0.956 pair.
    This re-derives it from the grid rather than trusting the kept-set file.
    """
    grid = {}
    for row in _rows(GRID_CSV):
        grid[(row["indicator"], int(row["length_a"]), int(row["length_b"]))] = \
            abs(float(row["spearman_z_pooled"]))

    dirty = []
    for row in _rows(KEPT_CSV):
        kept = [int(x) for x in row["kept"].split()] if row["kept"] else []
        for a, b in combinations(sorted(kept), 2):
            rho = grid.get((row["indicator"], a, b))
            if rho is not None and rho >= REVERT:
                dirty.append((row["indicator"], a, b, rho))
    assert dirty == [], (
        f"kept sets containing a redundant pair: {dirty}. A set of surviving "
        f"pairs is not a kept set."
    )


def test_the_universe_is_bist_100_not_whatever_listdir_returned():
    """The claim that broke last time, as a test.

    The generator must select from `backtesting_engine.config.BIST_100`, and the
    realised frame count must be plausible for it -- not the 40-file
    alphabetical prefix of a 578-file cache.
    """
    text = open(GEN, encoding="utf8").read()
    assert "from backtesting_engine.config import BIST_100" in text, (
        "the generator no longer selects the BIST_100 universe"
    )
    assert "os.listdir(CACHE)" not in text, (
        "the generator is back to listing the whole cache directory"
    )
    rows = _rows(GRID_CSV)
    frames = {int(r["frames"]) for r in rows}
    assert max(frames) > 40, (
        f"max frame count is {max(frames)}; the 40-frame alphabetical "
        f"truncation appears to be back"
    )


def test_dropped_frames_are_counted_not_swallowed():
    """A silent skip is how this repo loses a column. Every row must account."""
    rows = _rows(GRID_CSV)
    assert "frames_dropped" in rows[0], (
        "the CSV does not record dropped frames; a reader cannot tell a "
        "measured pair from a mostly-skipped one"
    )
    for row in rows:
        assert int(row["frames"]) > 0, row


def test_cmo_is_not_back_in_the_grid():
    """`cmo == 2*rsi - 100` to 2.8e-14 on this fork: Spearman 1.0.

    It sat in the candidate grid producing rows digit-identical to `rsi`'s, and
    the grid is structurally blind to it because it only compares lengths WITHIN
    an indicator. Re-adding it would put a perfectly redundant family back into
    a table whose purpose is to find redundancy.
    """
    text = open(GEN, encoding="utf8").read()
    grid_block = text[text.index("GRID = {"):text.index("PRICE_LEVEL")]
    assert '"cmo"' not in grid_block, (
        "`cmo` is back in GRID; it is an affine reparameterisation of `rsi` "
        "(2*rsi-100) and cannot be assessed by a within-indicator grid"
    )
    assert "2 * rsi - 100" in text or "2*rsi - 100" in text, (
        "the measured cmo/rsi relationship is no longer recorded, so the next "
        "reader will re-add it"
    )


def test_the_kept_set_is_maximal_not_merely_clean():
    """Half the definition was untested.

    "Largest subset whose every pairwise rho clears the band" — the previous
    guard only checked CLEAN. Shipping `willr [7]` instead of `[7 14 28]` would
    have failed nothing.
    """
    from itertools import combinations

    grid, blocked = {}, {}
    for row in _rows(GRID_CSV):
        ind = row["indicator"]
        pair = (int(row["length_a"]), int(row["length_b"]))
        grid[(ind, *pair)] = abs(float(row["spearman_z_pooled"]))
        blocked.setdefault(ind, set())
        if row["verdict"].startswith("revert"):
            blocked[ind].add(pair)

    undersized = []
    for row in _rows(KEPT_CSV):
        ind = row["indicator"]
        candidates = [int(x) for x in row["candidates"].split()]
        kept = [int(x) for x in row["kept"].split()] if row["kept"] else []
        best = 0
        for size in range(len(candidates), 0, -1):
            if any(not any(tuple(sorted(p)) in blocked.get(ind, set())
                           for p in combinations(sub, 2))
                   for sub in combinations(candidates, size)):
                best = size
                break
        if len(kept) < best:
            undersized.append((ind, kept, best))
    assert undersized == [], (
        f"kept sets smaller than the maximum clean subset: {undersized}"
    )


def test_the_kept_set_uses_the_verdict_not_the_bare_rho():
    """The majority-of-frames rule must bind the kept set too.

    Filtering on pooled rho alone reinstates the estimator round 1 called
    insufficient — a pair redundant on most frames could re-enter a kept set.
    """
    from itertools import combinations

    reverting = {(r["indicator"], int(r["length_a"]), int(r["length_b"]))
                 for r in _rows(GRID_CSV) if r["verdict"].startswith("revert")}
    leaked = []
    for row in _rows(KEPT_CSV):
        kept = [int(x) for x in row["kept"].split()] if row["kept"] else []
        for a, b in combinations(sorted(kept), 2):
            if (row["indicator"], a, b) in reverting:
                leaked.append((row["indicator"], a, b))
    assert leaked == [], f"kept sets containing a reverting pair: {leaked}"


def test_the_realised_universe_is_written_down():
    """The docstring promised it; for one round no output contained a ticker.

    Unverifiability is what made the false-universe CRITICAL survive review.
    """
    path = os.path.join(_FORK, "docs", "multil_universe.csv")
    assert os.path.exists(path), (
        "docs/multil_universe.csv is missing; a reader cannot tell which "
        "tickers produced these numbers"
    )
    rows = _rows(path)
    used = [r for r in rows if r["status"] == "used"]
    assert used, "no ticker recorded as used"
    frames = {int(r["frames"]) for r in _rows(GRID_CSV)}
    assert max(frames) == len(used), (
        f"grid reports up to {max(frames)} frames but the universe file lists "
        f"{len(used)} used tickers"
    )


def test_rows_beyond_the_documented_gate_e_band_are_flagged():
    """0.80-0.90 is a region CLAUDE.md's Gate E never ruled on.

    This grid calls it shippable-with-disclosure. That is a decision, and it
    must be visible per row rather than buried in a band constant.
    """
    rows = _rows(GRID_CSV)
    assert "beyond_documented_gate_e" in rows[0], (
        "the CSV does not flag rows where this grid is more permissive than "
        "the documented Gate E band"
    )
    for row in rows:
        rho = abs(float(row["spearman_z_pooled"]))
        expected = str(0.80 <= rho < 0.90)
        assert row["beyond_documented_gate_e"] == expected, (
            f"{row['indicator']} {row['length_a']}/{row['length_b']} rho={rho} "
            f"flagged {row['beyond_documented_gate_e']}, expected {expected}"
        )


def test_the_backtesting_writeback_matches_the_kept_set():
    """`Backtesting/TODO.md` is what MULTIL-1 reads. Nothing bound it to the CSV.

    It published `rsi` keep `7 28` under the words "this is the list MULTIL-1
    wires, and nothing else" while the CSV said `7 50` -- the choice the
    generator's own docstring records as a corrected defect. The write-back was
    produced before a tie-break fix and never re-synced, and no test looked.
    """
    bt = os.path.join(os.path.dirname(os.path.dirname(_FORK)),
                      "Backtesting", "TODO.md")
    if not os.path.exists(bt):
        pytest.skip("Backtesting/TODO.md absent")
    text = open(bt, encoding="utf8").read()
    if "## MULTIL" not in text:
        pytest.skip("MULTIL section not present")
    block = text[text.index("## MULTIL"):]
    block = block[:block.index("## ") if "## " in block[3:] else len(block)]

    wrong = []
    for row in _rows(KEPT_CSV):
        want = row["kept"] or "—"
        line = [l for l in block.splitlines()
                if l.startswith(f"| `{row['indicator']}` |")]
        if not line:
            wrong.append((row["indicator"], "absent from the write-back", want))
            continue
        if f"**{want}**" not in line[0]:
            wrong.append((row["indicator"], line[0].strip(), want))
    assert wrong == [], (
        f"Backtesting/TODO.md disagrees with multil_kept_set.csv: {wrong}"
    )
