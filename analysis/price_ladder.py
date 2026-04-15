"""Equity-only price ladder: probability of clearing each return hurdle at each entry FDV.

Consumes world_outputs.json, multiples_by_world.json, and exit_paths.json. Uses
the low/mid/high multiple triangle per world as three equally-weighted scenarios
within that world, yielding nine (world, multiple) cells weighted by world
probability / 3.

Two ladders are produced:
  (a) MODELLED — uses Q1 2029 equity FDV directly. Reference / ceiling case; what
      the book is worth if every cell crystallises at its modelled mark.
  (b) REALISED @3yr — uses realised FDV at a 3-year hold from exit_paths.py
      (probability-weighted over strategic / secondary / IPO / wind-down paths,
      with per-world strategic factors). This is the recommendation basis.

Token upside is treated qualitatively in the memo (§3.3) and is NOT priced into
this ladder. Warrant coverage sensitivity has been removed: it conflated equity
and token pricing by stacking speculative token economics on top of equity
claims. An equity round is priced on equity; a token round would be priced
separately against crypto-native comps.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "price_ladder.json"

TIERS = [
    {"fdv":  2_500_000_000, "label": "$2.5B (ICE-level secondary)"},
    {"fdv":  5_000_000_000, "label": "$5B (early secondary)"},
    {"fdv":  7_500_000_000, "label": "$7.5B (recommended ceiling)"},
    {"fdv": 10_000_000_000, "label": "$10B (Jan 2026 secondary)"},
    {"fdv": 12_500_000_000, "label": "$12.5B (speculative upper-range)"},
    {"fdv": 15_000_000_000, "label": "$15B (aggressive upper range)"},
    {"fdv": 20_000_000_000, "label": "$20B (rumoured March 2026 primary round)"},
    {"fdv": 25_000_000_000, "label": "$25B (post-CFTC-clarity)"},
]

HURDLES = {"2x": 2.0, "3x": 3.0, "5x": 5.0, "10x": 10.0}

TARGET_HOLD_YEARS = 3.0


def build_cells(exit_paths: dict | None = None):
    """Return cells dict. Each cell carries both the modelled FDV and, if
    exit_paths is provided, the realised-at-3yr FDV from the exit-path model."""
    worlds = json.loads((ROOT / "outputs" / "world_outputs.json").read_text())["worlds"]
    mult = json.loads((ROOT / "outputs" / "multiples_by_world.json").read_text())["per_world_equity_fdv"]
    realised_cells = (exit_paths or {}).get("at_3_year_hold", {}).get("cells", {})
    cells = {}
    for w in worlds:
        name = w["name"]
        rev = w["revenue_q1_2029"]
        wp = w["probability"]
        mu = mult[name]["multiples"]
        for tag in ("low", "mid", "high"):
            key = f"{name}__{tag}"
            rc = realised_cells.get(key, {})
            cells[key] = {
                "world": name,
                "multiple_tag": tag,
                "multiple": mu[tag],
                "revenue_q1_2029": rev,
                "equity_fdv_modelled": rev * mu[tag],
                "equity_fdv_realised_3yr": rc.get("realised_at_target"),
                "hold_years_weighted": rc.get("hold_years_weighted"),
                "joint_probability": wp / 3.0,
            }
    return cells


def _ladder(cells: dict, valuation_key: str) -> tuple[list, float]:
    ev = sum(c["joint_probability"] * c[valuation_key] for c in cells.values())
    rows = []
    for t in TIERS:
        row = {"entry_fdv": t["fdv"], "label": t["label"],
               "expected_return_multiple": ev / t["fdv"]}
        for hn, h in HURDLES.items():
            row[f"p_clear_{hn}"] = sum(
                c["joint_probability"] for c in cells.values()
                if c[valuation_key] >= t["fdv"] * h
            )
        rows.append(row)
    return rows, ev


REC_MAP = [
    (0.70, "AGGRESSIVE YES \u2014 plurality of worlds clear 3\u00d7"),
    (0.50, "YES, CORE POSITION \u2014 majority-weighted clearance"),
    (0.30, "CONDITIONAL YES \u2014 size down; coin-flip territory"),
    (0.15, "PASS unless token optionality materialises"),
    (0.00, "PASS \u2014 dominated bet"),
]


def _rec(p: float) -> str:
    for thresh, label in REC_MAP:
        if p >= thresh:
            return label
    return "PASS"


def main():
    exit_paths = json.loads((ROOT / "outputs" / "exit_paths.json").read_text())
    cells = build_cells(exit_paths)

    modelled_ladder, ev_modelled = _ladder(cells, "equity_fdv_modelled")
    realised_ladder, ev_realised = _ladder(cells, "equity_fdv_realised_3yr")

    # Recommendation is driven by realised@3yr
    for row in realised_ladder:
        row["recommendation_at_3x_hurdle"] = _rec(row["p_clear_3x"])
    for row in modelled_ladder:
        row["recommendation_at_3x_hurdle"] = _rec(row["p_clear_3x"])

    # What-has-to-be-true at $20B for 3x on realised@3yr (the honest frame)
    RUMORED = 20_000_000_000
    target = RUMORED * 3.0
    clearing = {k: v for k, v in cells.items() if v["equity_fdv_realised_3yr"] >= target}
    wht = {
        "rumored_entry_fdv": RUMORED,
        "source": "Reuters / Polymarket reporting March 2026",
        "basis": "realised equity FDV at 3-year hold",
        "target_realised_fdv_for_3x": target,
        "cells_that_clear": clearing,
        "aggregate_probability_clear_3x": sum(c["joint_probability"] for c in clearing.values()),
    }

    result = {
        "basis": "equity-only (no token / warrant layer); recommendation anchored on realised FDV at 3yr hold",
        "target_hold_years": TARGET_HOLD_YEARS,
        "ladder_realised_3yr": realised_ladder,
        "ladder_modelled": modelled_ladder,
        "cells": cells,
        "what_has_to_be_true_rumored_round": wht,
        "hurdles": HURDLES,
        "probability_weighted_equity_fdv_modelled": ev_modelled,
        "probability_weighted_equity_fdv_realised_3yr": ev_realised,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, default=float, indent=2))
    print(f"wrote {OUT}")
    print(f"prob-weighted equity FDV — modelled: ${ev_modelled/1e9:.2f}B   realised@3yr: ${ev_realised/1e9:.2f}B")
    for label, rows in [("MODELLED", modelled_ladder), ("REALISED @3yr (recommendation basis)", realised_ladder)]:
        print(f"\n=== {label} ===")
        print(f"{'entry':>14s} {'exp_mult':>9s} {'P(2x)':>7s} {'P(3x)':>7s} {'P(5x)':>7s} {'P(10x)':>7s}  recommendation")
        for r in rows:
            print(f"  ${r['entry_fdv']/1e9:>5.1f}B    {r['expected_return_multiple']:>7.2f}x  "
                  f"{r['p_clear_2x']:>6.1%} {r['p_clear_3x']:>6.1%} {r['p_clear_5x']:>6.1%} {r['p_clear_10x']:>6.1%}  "
                  f"{r['recommendation_at_3x_hurdle']}")
    print(f"\nRumoured $20B on realised@3yr: {wht['aggregate_probability_clear_3x']:.1%} chance of clearing 3\u00d7")


if __name__ == "__main__":
    main()
