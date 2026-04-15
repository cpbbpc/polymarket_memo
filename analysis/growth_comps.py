"""Volume projection — DraftKings-handle anchor + world scalars.

Methodology rationale:
  The Polymarket thesis is that regulatory unlock (QCEX launch, federal
  preemption) drives mainstream retail onto the rails. DraftKings' handle
  growth 2021 → 2024 is the closest adjacent analogue: state-by-state sports
  legalisation caused handle to compound 4.54× over 3 years, dominated by new
  addressable markets going live (not same-store growth).

  DK handle (10-K): $11.4B 2021 → $21.4B 2022 → $32.8B 2023 → $51.8B 2024.
  Three-year multiple = 51.8 / 11.4 = 4.54×.

  Handle (not revenue) is the right unit because:
   - Revenue bundles hold-rate expansion and product-mix which don't transfer.
   - Polymarket revenue = volume × fee-bearing-share × take-rate; volume is
     the exogenous input, take-rate is a separate (mix-derived) lever.
   - Comparing Polymarket on-chain notional to DK handle is volume-native.

  World scalars on the DK-handle anchor:
    Bear  = 1.00× current (status quo — regulation disappoints, Polymarket
            stagnates at current run rate; no unlock materialises)
    Base  = 1.00× DK (one-for-one regulatory-unlock analogue; QCEX + state
            resolution replicates the DK state-by-state dynamic)
    Bull  = 1.25× DK (same unlock spine plus a category-creation premium
            reflecting Polymarket becoming the category-defining event-contract
            primitive with institutional hedging adoption)

  Robinhood and Flutter are retained in the comp panel as cross-references
  but are NOT used as primary world anchors. Robinhood's 2020–23 arc is
  dominated by meme-stock and interest-income factors unrelated to a
  regulatory-unlock thesis; Flutter's 2018–21 is M&A-contaminated (Stars
  Group 2020).

  Polymarket monthly volume is projected by interpolating geometrically
  from current (Apr 2026) to the Q1 2029 endpoint multiple; TTM revenue
  averages the final 12 months before the endpoint (Apr 2028 → Mar 2029)
  and lands at ~87% of the endpoint-annualised value.

Sources: DraftKings 10-K (handle disclosure 2021–2024); Keyrock × Dune
category-level data as cross-reference for total prediction-market TAM.
Numbers rounded; intent is the *shape* of growth, not GAAP precision.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "outputs" / "growth_comps.json"

# --- Primary anchor: DraftKings handle 2021 → 2024 ---
DK_HANDLE = {
    "anchor_year": 2021,
    "anchor_handle_b": 11.4,
    "series_handle_b": [(1, 21.4), (2, 32.8), (3, 51.8)],
    "note": "DraftKings 10-K handle disclosure. 2021→2024 window chosen because it "
            "combines (a) continuing state-by-state regulatory unlock post-PASPA and "
            "(b) DK's breakthrough-to-scale phase (2021 is first $1B-revenue year at "
            "$1.30B, reaching $4.77B by 2024). Captures regulatory-unlock-plus-scale-"
            "breakthrough regime Polymarket enters post-QCEX. Milestones: NY online "
            "launch Jan 2022, OH/MA/KY 2023, NC/VT 2024. 3y handle multiple = 51.8 / 11.4 = 4.54×.",
}

# Cross-reference comps retained in panel (not used as primary anchors)
REFERENCE_COMPS = {
    "Robinhood_rev": {
        "anchor_year": 2020,
        "anchor_rev_m": 959,
        "series_rev_m": [(1, 1815), (2, 1358), (3, 1865), (4, 2954)],
        "note": "Retail-trading revenue. Dominated by meme-stock cycle (2020–21) "
                "and interest-income expansion (2022–23) — does not transfer to "
                "Polymarket's regulatory-unlock thesis. Retained for reference only.",
    },
    "Flutter_rev": {
        "anchor_year": 2018,
        "anchor_rev_m": 2200,
        "series_rev_m": [(1, 2530), (2, 5130), (3, 7990)],
        "note": "Global sportsbook revenue. 2020 M&A-contaminated (Stars Group). "
                "Retained for reference only.",
    },
}

# --- World scalars on DK-handle anchor ---
# Bear is an explicit multiplier on CURRENT Polymarket monthly volume
# (thesis: stagnation, not a scalar of DK growth).
# Base/Bull are multipliers on the DK 3y handle multiple (4.54×).
WORLD_SCALARS = {
    "Bear": {"type": "current_multiplier", "value": 1.00,
             "rationale": "Status quo. Regulation fails to unlock, Polymarket "
                          "stagnates at roughly current run rate."},
    "Base": {"type": "dk_handle_multiplier", "value": 1.00,
             "rationale": "One-for-one DraftKings regulatory-unlock analogue. "
                          "QCEX launch + state resolution replicates state-by-state "
                          "sports legalisation dynamic."},
    "Bull": {"type": "dk_handle_multiplier", "value": 1.25,
             "rationale": "Same regulatory-unlock spine as Base plus a 1.25× "
                          "category-creation premium reflecting Polymarket "
                          "becoming the category-defining event-contract primitive "
                          "with institutional hedging adoption."},
}

# Proration: TTM Apr 2028 → Mar 2029 averages ~87% of Q1 2029 endpoint-annualised
# (calibrated to geometric-growth ramp over 3 years).
TTM_RAMP_FACTOR = 0.87


def project_monthly_volume(current_monthly_v, endpoint_multiple, horizon_months=36):
    """Geometric interpolation from month 0 (anchor) to horizon_months
    (Q1 2029 endpoint). Returns (monthly_endpoint, ttm_final_12mo_avg)."""
    endpoint_monthly = current_monthly_v * endpoint_multiple
    # TTM over final 12 months of the ramp averages ~TTM_RAMP_FACTOR × endpoint × 12.
    # Only applied when there's actual growth; flat trajectories (e.g. Bear 1.0×) use endpoint × 12.
    ramp = TTM_RAMP_FACTOR if endpoint_multiple > 1.0 else 1.0
    ttm_final = ramp * endpoint_monthly * 12
    return endpoint_monthly, ttm_final


def build():
    # Polymarket anchor (Mar 2026 monthly volume)
    pm_current_monthly = 5.98e9
    dk_3y_multiple = DK_HANDLE["series_handle_b"][-1][1] / DK_HANDLE["anchor_handle_b"]

    projections = {}
    for world, sc in WORLD_SCALARS.items():
        if sc["type"] == "current_multiplier":
            endpoint_multiple = sc["value"]
            anchor_description = f"{sc['value']:.2f}× current PM volume"
        elif sc["type"] == "dk_handle_multiplier":
            endpoint_multiple = dk_3y_multiple * sc["value"]
            anchor_description = (f"{sc['value']:.2f}× DK 3y handle multiple "
                                  f"({dk_3y_multiple:.2f}× → {endpoint_multiple:.2f}× net)")
        else:
            raise ValueError(f"unknown scalar type {sc['type']}")

        endpoint_monthly, ttm_final = project_monthly_volume(pm_current_monthly, endpoint_multiple)

        projections[world] = {
            "scalar_type": sc["type"],
            "scalar_value": sc["value"],
            "anchor_description": anchor_description,
            "endpoint_multiple_vs_current": endpoint_multiple,
            "monthly_volume_q1_2029_usd": endpoint_monthly,
            "ttm_volume_q1_2029_usd": ttm_final,
            "rationale": sc["rationale"],
        }

    out = {
        "method": (
            "DraftKings-handle anchor + world scalars. "
            "DK handle 2021→2024 = 4.54× (post-PASPA state-by-state unlock + DK breakthrough-to-scale: first $1B-revenue year to $4.77B) "
            "is the regulatory-unlock analogue. "
            "Bear = 1.00× current volume (stagnation, no unlock). "
            "Base = 1.00× DK handle multiple (one-for-one unlock). "
            "Bull = 1.25× DK handle multiple (unlock + category-creation premium). "
            "TTM revenue averages final 12 months before Q1 2029 endpoint "
            f"(~{TTM_RAMP_FACTOR*100:.0f}% of endpoint-annualised)."
        ),
        "primary_anchor": {
            "source": "DraftKings 10-K handle disclosure",
            "anchor_year": DK_HANDLE["anchor_year"],
            "anchor_handle_b": DK_HANDLE["anchor_handle_b"],
            "y3_handle_b": DK_HANDLE["series_handle_b"][-1][1],
            "three_year_multiple": round(dk_3y_multiple, 3),
            "note": DK_HANDLE["note"],
        },
        "reference_comps": REFERENCE_COMPS,
        "world_scalars": WORLD_SCALARS,
        "polymarket_anchor_monthly_usd": pm_current_monthly,
        "polymarket_projections": projections,
        "ttm_ramp_factor": TTM_RAMP_FACTOR,
    }

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}\n")

    print("=== DK-handle anchor ===")
    print(f"  {DK_HANDLE['anchor_year']} handle: ${DK_HANDLE['anchor_handle_b']}B")
    print(f"  {DK_HANDLE['anchor_year']+3} handle: ${DK_HANDLE['series_handle_b'][-1][1]}B")
    print(f"  3y multiple: {dk_3y_multiple:.2f}×\n")

    print("=== World projections (Polymarket Q1 2029) ===")
    print(f"{'World':6s}  {'Scalar':>28s}  {'Endpoint mo vol':>18s}  {'TTM rev base':>14s}  {'×current':>9s}")
    for w, p in projections.items():
        print(f"{w:6s}  {p['anchor_description']:>28s}  "
              f"${p['monthly_volume_q1_2029_usd']/1e9:>7.2f}B   "
              f"${p['ttm_volume_q1_2029_usd']/1e9:>7.1f}B   "
              f"{p['endpoint_multiple_vs_current']:>6.2f}×")


if __name__ == "__main__":
    build()
