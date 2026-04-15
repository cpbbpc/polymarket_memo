"""Exit mechanism model — per-world paths with probability and liquidity discount.

Equity-only. Token exits are treated qualitatively in the memo (§3.3) and are
not modelled here.

Each world has a plausible distribution over equity exit paths; each path has
an achievable multiple relative to modelled equity FDV and a median hold period.

The `realised_multiple_on_fdv` per path bundles TWO effects that would
otherwise be modeled separately:
  (a) liquidity haircut vs. pure public-market mark
  (b) multiple compression between Q1-2029-modelled and actual exit year
By the time an acquirer or public market transacts, growth has decelerated
and multiples have compressed. The blended discount captures both.

Strategic-acquisition factor is world-dependent: Bear implies an ICE-anchored
monopsony with a compressed price; Bull implies multi-bidder competition that
approaches an IPO mark. Wind-down recovery is deliberately low — a forced
US/EU geofence on a growth-priced Q1 2029 FDV leaves little franchise value.
IPO hold is 6yr to reflect that Polymarket would need S-1 prep, CFTC
clarity, and two audited years from a Q1 2029 modelled ARR base.
"""
from __future__ import annotations
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "exit_paths.json"


# Hold periods are path-level (world-invariant)
HOLD_YEARS_MEDIAN = {
    "strategic_acquisition": 3.5,
    "secondary_sale": 2.0,
    "ipo": 6.0,
    "wind_down": 2.5,
}

# Realised-multiple-on-modelled-FDV factors are per (world, path).
# Strategic varies by world: Bear = ICE monopsony (compressed); Bull = competitive bidding.
# Wind-down recovery at 0.08 is anchored on public-company crypto/fintech failure
# base rates: FTX equity ~0%, Celsius <5%, BlockFi near-zero, Voyager ~35% (asset
# recovery, not equity). 8% represents a weighted blend assuming the Bear wind-down
# is closer to FTX/BlockFi (total franchise impairment) than to Voyager (partial
# asset recovery). Note: this is pure wind-down. A US-geofence-only outcome where
# the offshore entity continues is modelled via the strategic-acquisition path at
# compressed valuation (0.72× Bear), not via wind-down.
REALISED_MULTIPLE_ON_FDV = {
    # Bear strategic at 0.72: ICE is most-likely acquirer but not a pure monopsonist.
    # Even under regulatory compression, CME / Nasdaq / Flutter are credible secondary
    # bidders at a compressed price, supporting a ~28% discount to modelled FDV.
    # Secondary sale at 0.80 across worlds: 25% discount to last round is the
    # conservative end of the late-stage secondary market; hot-name secondaries
    # (Stripe, SpaceX, OpenAI) regularly clear at 10-20% discounts.
    "Bear": {"strategic_acquisition": 0.72, "secondary_sale": 0.80, "ipo": 1.00, "wind_down": 0.08},
    "Base": {"strategic_acquisition": 0.85, "secondary_sale": 0.80, "ipo": 1.00, "wind_down": 0.08},
    "Bull": {"strategic_acquisition": 0.95, "secondary_sale": 0.80, "ipo": 1.00, "wind_down": 0.08},
}

PATH_NOTES = {
    "strategic_acquisition": "ICE most-likely acquirer ($2B anchor); possible bidders CME, NYSE, Nasdaq, Flutter. Bear = ICE-anchored compressed bid (0.72×); Bull = competitive bidding approaching IPO mark (0.95×).",
    "secondary_sale": "Late-stage secondary to new institutional round (SoftBank-style). Fastest liquidity, ~25% discount to last round.",
    "ipo": "Requires revenue ≥$1B, CFTC clarity, mature operating metrics. 6yr hold reflects S-1 prep + two clean audited years from Q1 2029 ARR base.",
    "wind_down": "Regulatory adverse outcome forcing US/EU geofence escalation; franchise impairment on a growth-priced Q1 2029 mark.",
}


WORLD_EXIT_DISTRIBUTION = {
    "Bear": {
        "strategic_acquisition": 0.55,
        "secondary_sale": 0.25,
        "ipo":              0.00,
        "wind_down":        0.20,
        "rationale": "Regulatory compression → strategic acquirer (likely ICE at compressed price) or slow decline. No IPO path.",
    },
    "Base": {
        "strategic_acquisition": 0.30,
        "secondary_sale":        0.35,
        "ipo":                   0.30,
        "wind_down":             0.05,
        "rationale": "Multiple paths viable. Secondary most likely near-term; IPO feasible 5–6yr out given CFTC clarity.",
    },
    "Bull": {
        "strategic_acquisition": 0.15,
        "secondary_sale":        0.20,
        "ipo":                   0.60,
        "wind_down":             0.05,
        "rationale": "Bull means prediction markets are a financial primitive worth public listing. IPO dominant; ICE-ceiling concern evaporates (bidding competition).",
    },
}


def compute_realised_fdv(worlds: list[dict], mult: dict, hold_years_target: float) -> dict:
    """For each (world, multiple_tag) cell, compute expected realised equity
    FDV at the target hold period. Uses probability-weighted exit-path mix
    with per-world strategic factors.

    Cells whose expected hold_years > target are prorated (partial return
    realised by target date).
    """
    out_cells = {}
    for w in worlds:
        name = w["name"]
        wp = w["probability"]
        rev = w["revenue_q1_2029"]
        dist = WORLD_EXIT_DISTRIBUTION[name]
        factors = REALISED_MULTIPLE_ON_FDV[name]
        mu = mult["per_world_equity_fdv"][name]["multiples"]
        for tag in ("low", "mid", "high"):
            equity_fdv = rev * mu[tag]
            realised = 0.0
            hold_weighted = 0.0
            for path_key in ("strategic_acquisition", "secondary_sale", "ipo", "wind_down"):
                p = dist[path_key]
                if p <= 0:
                    continue
                path_mult = factors[path_key]
                hold = HOLD_YEARS_MEDIAN[path_key]
                realised += p * equity_fdv * path_mult
                hold_weighted += p * hold

            if hold_weighted <= hold_years_target:
                realised_at_target = realised
            else:
                # Concave proration: late-stage private marks step up non-linearly
                # through rounds, and pre-IPO secondary liquidity is available 18-24mo
                # before listing. Linear proration zero-values time-until-exit and
                # under-weights late-stage mark-ups; exponent 0.75 reflects typical
                # LP return distribution across extended hold paths.
                realised_at_target = realised * (hold_years_target / hold_weighted) ** 0.75

            out_cells[f"{name}__{tag}"] = {
                "world": name,
                "multiple_tag": tag,
                "multiple": mu[tag],
                "joint_probability": wp / 3.0,
                "equity_fdv_modelled": equity_fdv,
                "equity_realised_fdv": realised,
                "hold_years_weighted": hold_weighted,
                "realised_at_target": realised_at_target,
            }
    ev = sum(c["joint_probability"] * c["realised_at_target"] for c in out_cells.values())
    return {"cells": out_cells, "probability_weighted_realised_fdv_at_target": ev,
            "target_hold_years": hold_years_target}


def _world_summary(worlds: list[dict], mult: dict) -> dict:
    """Per-world realised-multiple on modelled FDV and weighted hold (mid-multiple cell)."""
    out = {}
    for w in worlds:
        name = w["name"]
        dist = WORLD_EXIT_DISTRIBUTION[name]
        factors = REALISED_MULTIPLE_ON_FDV[name]
        realised_ratio = 0.0
        hold_weighted = 0.0
        for k in ("strategic_acquisition", "secondary_sale", "ipo", "wind_down"):
            p = dist[k]
            if p <= 0:
                continue
            realised_ratio += p * factors[k]
            hold_weighted += p * HOLD_YEARS_MEDIAN[k]
        out[name] = {
            "realised_multiple_on_modelled_fdv": realised_ratio,
            "hold_years_weighted": hold_weighted,
            "dominant_path": max(
                ((k, dist[k]) for k in ("strategic_acquisition", "secondary_sale", "ipo", "wind_down")),
                key=lambda kv: kv[1],
            )[0],
        }
    return out


def main() -> None:
    worlds = json.loads((ROOT / "outputs" / "world_outputs.json").read_text())["worlds"]
    mult = json.loads((ROOT / "outputs" / "multiples_by_world.json").read_text())

    results_3yr = compute_realised_fdv(worlds, mult, hold_years_target=3.0)
    results_5yr = compute_realised_fdv(worlds, mult, hold_years_target=5.0)

    out = {
        "basis": "equity-only (token not modelled; see memo §3.3)",
        "method": (
            "Per-world distribution over equity exit paths (M&A, secondary, IPO, wind-down); "
            "each path has a realisable multiple on modelled equity FDV (world-dependent for strategic) "
            "and a median hold period. Realised FDV at 3-year and 5-year hold computed. "
            "Cells = (world, low/mid/high multiple)."
        ),
        "realised_multiple_on_fdv": REALISED_MULTIPLE_ON_FDV,
        "hold_years_median": HOLD_YEARS_MEDIAN,
        "path_notes": PATH_NOTES,
        "world_exit_distribution": WORLD_EXIT_DISTRIBUTION,
        "per_world_summary": _world_summary(worlds, mult),
        "at_3_year_hold": results_3yr,
        "at_5_year_hold": results_5yr,
    }
    OUT.write_text(json.dumps(out, default=float, indent=2))
    print(f"wrote {OUT}")
    print(f"EXPECTED REALISED EQUITY FDV at 3yr hold: ${results_3yr['probability_weighted_realised_fdv_at_target']/1e9:.2f}B")
    print(f"EXPECTED REALISED EQUITY FDV at 5yr hold: ${results_5yr['probability_weighted_realised_fdv_at_target']/1e9:.2f}B")
    print("\nPER-WORLD REALISED EQUITY FDV AT 5YR (mid multiple cell):")
    for wn in ["Bear", "Base", "Bull"]:
        c5 = results_5yr["cells"][f"{wn}__mid"]
        print(f"  {wn:6s}  mid-mult cell  realised=${c5['realised_at_target']/1e9:.2f}B  hold={c5['hold_years_weighted']:.1f}yr")


if __name__ == "__main__":
    main()
