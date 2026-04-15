"""Verified comp panel + per-world multiple ranges.

Panel of twelve names verified from public sources as of April 13 2026:
- Public stocks (stockanalysis.com): CME, HOOD, CRCL, NDAQ, ICE, COIN, DKNG, FLUT
- Crypto tokens (CoinGecko): HYPE (FDV), PUMP (circulating mcap)
- Private (press reports): Kalshi ($22B, March 2026), Tether (~$200B secondary, Forbes)

Worlds are anchored on specific comp clusters, not a blended regression:
  Bear cluster = DKNG + PUMP + COIN (distressed/post-bubble + crypto-native post-hype)
  Base cluster = COIN + NDAQ + ICE + HOOD (growth-stage retail trading + mature exchanges)
  Bull cluster = HYPE + Kalshi + CME (crypto-native category-defining + mature dominant
                                      + direct-peer private mark)
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "multiples_by_world.json"


# Verified comp panel — April 13 2026 snapshots.
# Sources: stockanalysis.com (public EV + TTM revenue), CoinGecko (circulating mcap +
# on-chain revenue via press), Bloomberg (Kalshi), Forbes (Tether secondary).
COMP_PANEL = [
    # (name, basis, valuation_usd, revenue_ttm_usd, notes)
    {"name": "Flutter",      "basis": "EV",          "valuation": 28.87e9,  "revenue": 16.41e9, "ev_sales": 1.8,  "group": "mature gambling"},
    {"name": "DraftKings",   "basis": "EV",          "valuation": 11.78e9,  "revenue":  6.05e9, "ev_sales": 1.9,  "group": "post-bubble sports"},
    {"name": "Pump.fun",     "basis": "circ mcap",   "valuation":  1.08e9,  "revenue":  0.49e9, "ev_sales": 2.2,  "group": "crypto post-hype"},
    {"name": "Coinbase",     "basis": "EV",          "valuation": 40.59e9,  "revenue":  7.18e9, "ev_sales": 5.7,  "group": "crypto retail platform"},
    {"name": "Nasdaq",       "basis": "EV",          "valuation": 56.54e9,  "revenue":  8.26e9, "ev_sales": 6.8,  "group": "mature exchange"},
    {"name": "Circle",       "basis": "EV",          "valuation": 19.88e9,  "revenue":  2.75e9, "ev_sales": 7.2,  "group": "stablecoin issuer"},
    {"name": "ICE",          "basis": "EV",          "valuation": 110.45e9, "revenue": 12.64e9, "ev_sales": 8.7,  "group": "mature exchange"},
    {"name": "Hyperliquid",  "basis": "FDV",         "valuation": 42.28e9,  "revenue":  0.90e9, "ev_sales": 47.0, "group": "crypto-native CLOB"},
    {"name": "Robinhood",    "basis": "EV",          "valuation": 62.38e9,  "revenue":  4.47e9, "ev_sales": 14.0, "group": "retail trading platform"},
    {"name": "Kalshi",       "basis": "last round",  "valuation": 22.00e9,  "revenue": 0.2635e9, "ev_sales": 83.5, "group": "direct private peer", "note": "$22B round (Mar 2026); 2025 fee revenue $263.5M per press reports (Yahoo Finance, Apr 2026). Implied ~83× TTM EV/Sales — hot-private category peak."},
    {"name": "CME Group",    "basis": "EV",          "valuation": 107.18e9, "revenue":  6.52e9, "ev_sales": 16.4, "group": "dominant mature exchange"},
    {"name": "Tether",       "basis": "secondary",   "valuation": 200.00e9, "revenue": 12.00e9, "ev_sales": 16.7, "group": "stablecoin issuer (float)"},
]

# Per-world multiple ranges. Polymarket net ARR as of Mar 2026 is ~$200M
# (after NegRisk-offset refunds). At $10-15B secondary marks this is ~50-75× ARR,
# in line with Kalshi (~83× TTM on $22B round) and Hyperliquid (~47× FDV) — the
# category's hot private/crypto-native comps. The multiples below reflect exit
# valuations 3 years out with moderate compression from today's category-leader levels.
PER_WORLD_MULTIPLES = {
    "Bear": {
        "low": 5.0, "mid": 10.0, "high": 15.0,
        "rationale": (
            "Anchored on mature-exchange cluster: Coinbase 5.7× (surviving-crypto-cycle), "
            "Nasdaq 6.8×, Circle 7.2×, ICE 8.7×, Pump.fun 2.2× (distressed crypto-native). "
            "Bear Polymarket is a stagnating franchise priced like a mid-tier public "
            "exchange that failed to unlock mainstream retail. 10× mid = CME/ICE-adjacent "
            "(mature dominant exchange but without growth premium). High 15× caps at "
            "CME 16.4× for a clean survive-and-grow outcome even without regulatory unlock."
        ),
        "anchor_comps": ["Pump.fun 2.2×", "Coinbase 5.7×", "ICE 8.7×", "Robinhood 14.0×", "CME 16.4×"],
    },
    "Base": {
        "low": 15.0, "mid": 25.0, "high": 35.0,
        "rationale": (
            "Anchored on growth-stage retail/prediction platforms with category-unlock "
            "underway: Coinbase 2021 peak (~20× at comparable growth stage), Robinhood "
            "14.0× (scaled retail benchmark). Kalshi's current ~83× TTM and Hyperliquid's "
            "~47× FDV sit well above this band — Base assumes Polymarket's multiple "
            "compresses closer to public-growth-stage comps as the category matures and "
            "hot-private/crypto-native premia fade. Base Polymarket under QCEX-unlock with "
            "sportsbook absorption prices like a growth-stage regulated exchange still "
            "compounding but past the private-market peak. Mid 25× sits above current "
            "Coinbase/Robinhood. High 35× reserves room for outperformance short of Bull "
            "category-definition."
        ),
        "anchor_comps": ["Robinhood 14.0×", "Coinbase 2021-peak ~20×", "Kalshi ~83× TTM (compresses out)", "Hyperliquid ~47× FDV (compresses out)", "early-stage premium to 35×"],
    },
    "Bull": {
        "low": 30.0, "mid": 50.0, "high": 75.0,
        "rationale": (
            "Anchored on today's category-defining hot privates: Kalshi $22B round / "
            "$263.5M 2025 fee revenue = ~83× TTM (per press reports Apr 2026), "
            "Hyperliquid $42.28B FDV / ~$900M revenue = ~47× FDV. Bull Polymarket is the "
            "category-defining event-contract primitive 3 years out; exit multiple "
            "compresses from today's 47–83× band toward 50× mid as the category matures "
            "and public comps become relevant. Low 30× floors at post-maturation public "
            "category-leader level. High 75× just under today's Kalshi mark — a reasonable "
            "ceiling if Polymarket holds or displaces Kalshi's position. Single biggest "
            "driver of valuation dispersion."
        ),
        "anchor_comps": ["Coinbase 2021-peak ~20×", "Hyperliquid ~47× FDV", "Kalshi ~83× TTM (Mar 2026 round)", "75× mid-high = modest compression off hot-private band"],
    },
}


def main() -> None:
    worlds = json.loads((ROOT / "outputs" / "world_outputs.json").read_text())["worlds"]
    per_world = {}
    for w in worlds:
        m = PER_WORLD_MULTIPLES[w["name"]]
        rev = w["revenue_q1_2029"]
        per_world[w["name"]] = {
            "revenue_q1_2029": rev,
            "multiples": m,
            "equity_fdv_low":  rev * m["low"],
            "equity_fdv_mid":  rev * m["mid"],
            "equity_fdv_high": rev * m["high"],
        }
    result = {
        "comp_panel_apr_2026": COMP_PANEL,
        "per_world_equity_fdv": per_world,
        "ice_floor_anchor": {
            "ev_usd": 2_000_000_000,
            "notes": "ICE investment at $2B implied is a FLOOR anchor (strategic investor transacted). Not a ceiling.",
        },
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, default=float, indent=2))
    print(f"wrote {OUT}")
    for name, d in per_world.items():
        print(f"  {name:6s}  equity_FDV: low=${d['equity_fdv_low']/1e9:.2f}B  mid=${d['equity_fdv_mid']/1e9:.2f}B  high=${d['equity_fdv_high']/1e9:.2f}B")


if __name__ == "__main__":
    main()
