"""Three structural worlds (Bear/Base/Bull): deterministic driver values
+ probability weights, producing per-world TTM revenue at Q1 2029 (the
3-year-hold exit point from an April 2026 entry).

Volume trajectories come from analysis/growth_comps.py:
  Bear = 1.00× current PM volume (status quo; regulation fails to unlock)
  Base = 1.00× DK handle 3y multiple (one-for-one regulatory-unlock analogue)
  Bull = 1.25× DK handle 3y multiple (unlock + category-creation premium)

Net take rates are observed-anchored. March 2026 effective net = 0.28%
(gross 3.18% × 9% retention after FeeRefunded events). World forwards
scale off observed using category-mix and user-type assumptions.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "world_outputs.json"


@dataclass
class WorldDrivers:
    volume_monthly_usd: float       # Q1 2029 monthly run rate (exit-point reading)
    ttm_volume_annual_usd: float    # TTM Apr 2028 → Mar 2029 (used for revenue base)
    mau: float
    fee_bearing_share: float
    net_take_rate: float            # net of maker rebate (company take)
    data_and_clearing_revenue: float = 0.0  # non-trading revenue (QCEX clearing, data/index licensing)

    def trading_revenue(self) -> float:
        # net_take_rate is observed-anchored on TOTAL volume (includes fee-free
        # geopolitics + NegRisk legacy tail), so fee_bearing_share is narrative
        # context, not an additional multiplier (would double-count fee-free drag).
        return self.ttm_volume_annual_usd * self.net_take_rate

    def annual_revenue(self) -> float:
        return self.trading_revenue() + self.data_and_clearing_revenue


@dataclass
class World:
    name: str
    probability: float
    narrative: str
    regulatory_assumption: str
    drivers_q1_2029: WorldDrivers
    probability_sources: list[str] = field(default_factory=list)


def build_worlds(current_vol: float, current_mau: int) -> list[World]:
    """Current anchor (March 2026): volume $5.98B/mo combined, MAU 747k.
    Project to Q1 2029 exit (~36 months out, 3-year hold).

    Volume trajectories from analysis/growth_comps.py (DK-handle anchor + scalars):
      Bear: 1.00× current           → $5.98B/mo     (status quo)
      Base: 1.00× DK 3y handle mult → $27.17B/mo    (4.54× current)
      Bull: 1.25× DK 3y handle mult → $33.97B/mo    (5.68× current)

    Net take rates (observed-anchored, post-refund):
      Polymarket's NegRisk offset mechanism and maker rebates refund ~91% of
      gross fees. Observed March 2026 effective net take = 0.283% (gross 3.18%
      × 9% retention ratio). Cross-validated against DefiLlama $17M/month.

      Forward take rate derivation:
        Bear:  0.28% (status quo; 9% retention holds, current mix persists)
        Base:  0.38% (Bear × retention-lift 1.44× × gross-mix 0.92 = 13% retention.
                     Sportsbook migrants are hold-to-resolution users → less tail
                     clustering in p×(1−p) refund → modest retention lift. Sports-
                     heavy mix caps gross ceiling at 3.13% vs Bear 3.41%.)
        Bull:  0.40% (institutional-mix decomposition rather than a single retention
                     multiplier. Bull volume splits ~60% retail-like / ~40% institutional:
                       retail-like share priced at Base net (0.38%);
                       institutional share priced via two competing channels:
                         (a) probability-normalisation: mid-prob hedging lifts
                             retention ~2× (p×(1−p) maximal at p=0.5, collapses at tails);
                         (b) institutional tiering: maker rebates + volume tiers
                             compress gross ~45% (vs CME ~50%, Coinbase ~93% retail→inst).
                         → institutional net ≈ Base × 2.0 × 0.55 ≈ 0.42%.
                       Blended: 0.60 × 0.38% + 0.40 × 0.42% ≈ 0.40%.
                     Institutional venues compress take via tiering rather than
                     expanding it. Upside from institutional flow lives in a separate
                     data/clearing revenue line, not in trading take.)

      Data & clearing revenue (Bull only; non-trading line):
        QCEX clearing fees (~3% of trading): ~$45M
        Data/index licensing (probability feeds, media, structured-product issuers): ~$30M
        → $75M combined. Analogues: CME market data ~10% of total (mature),
          ICE data services ~19% (mature, post-NYSE). A 3-year-old franchise from
          standing start lands well below mature levels; $75M = ~5% of trading rev.
          Bear/Base = $0 (no institutional rails activated, no QCEX-at-scale).

    Fee-bearing share (mix-derived: non-politics 95% × share + politics × world-FBS):
      Politics has a drag from 2024-era NegRisk tail and the permanent
      geopolitics carve-out. Bear 70% (stagnation preserves NegRisk tail);
      Base 80% (2024-cycle winds down, 2028-cycle deploys fee-bearing);
      Bull 85% (full maturation, only permanent geopolitics drag remains).
      → Bear 89.5% / Base 91.7% / Bull 93.0%.
    """
    # Read comp-derived projections (canonical source).
    growth = json.loads((ROOT / "outputs" / "growth_comps.json").read_text())
    proj = growth["polymarket_projections"]
    bear_vol_mo = proj["Bear"]["monthly_volume_q1_2029_usd"]
    base_vol_mo = proj["Base"]["monthly_volume_q1_2029_usd"]
    bull_vol_mo = proj["Bull"]["monthly_volume_q1_2029_usd"]
    bear_ttm = proj["Bear"]["ttm_volume_q1_2029_usd"]
    base_ttm = proj["Base"]["ttm_volume_q1_2029_usd"]
    bull_ttm = proj["Bull"]["ttm_volume_q1_2029_usd"]

    bear = World(
        name="Bear",
        probability=5/17,
        narrative=(
            "Regulation fails to unlock. CFTC loss at Supreme Court OR state-AG "
            "cascade OR adverse AZ criminal verdict keeps Polymarket geofenced; "
            "QCEX launches late or narrow. No category inflection — the platform "
            "runs broadly at current scale with the existing user base. Volume "
            "stagnates at ~$6B/mo; category mix holds roughly at observed March "
            "2026 levels; net take stays near observed 0.28% post-refund."
        ),
        regulatory_assumption=(
            "1+ of: CFTC loss, state-AG cascade, AZ criminal verdict. Base rate: "
            "shutdown_us (12.5%) + geofence (12.5%) = 25% floor for adverse outcomes."
        ),
        drivers_q1_2029=WorldDrivers(
            volume_monthly_usd=bear_vol_mo,
            ttm_volume_annual_usd=bear_ttm,
            mau=current_mau * 1.0,           # stagnation — MAU holds roughly at observed
            fee_bearing_share=0.895,         # mix-derived: non-politics (78%) × 95% + politics (22%) × 70%.
                                             # politics drag = 2024-era NegRisk tail + permanent geopolitics
                                             # carve-out; 70% reflects slow NegRisk churn under stagnation.
            net_take_rate=0.00283,           # observed March 2026 effective net rate (post-refund).
                                             # NegRisk offsets + maker rebates refund ~91% of gross fees
                                             # (gross 3.18% → net 0.28%). Bear holds at observed under
                                             # status-quo assumption. Cross-validated against DefiLlama
                                             # ($17M/mo) and observed per Dune ingest.
        ),
        probability_sources=[
            "regulatory base rate 25% floor",
            "state AG momentum (12+ states, AZ criminal)",
            "competitive pressure from Kalshi post-CFTC",
        ],
    )
    base = World(
        name="Base",
        probability=5.5/17,
        narrative=(
            "Execution holds. CFTC clarity without retail restriction. QCEX launches "
            "Q3-Q4 2026. Fee ramp stays (observed no volume attrition through activations). "
            "Polymarket retains share in crypto/news/politics. Robinhood/ICE partners. "
            "Volume 4.54× from current (~$27.2B/mo by Q1 2029), tracking DraftKings' "
            "2021–2024 handle growth — a combined regulatory-unlock (continuing post-PASPA "
            "state-by-state legalisation) and breakthrough-to-scale (DK's first $1B-revenue "
            "year onward to $4.77B) analogue for the regime Polymarket enters post-QCEX."
        ),
        regulatory_assumption=(
            "CFTC wins or settles; QCEX operates as registered venue. "
            "Base-rate cluster: restructured + fine_and_continue + favorable-ongoing = ~62%."
        ),
        drivers_q1_2029=WorldDrivers(
            volume_monthly_usd=base_vol_mo,
            ttm_volume_annual_usd=base_ttm,
            mau=current_mau * 5.0,           # DraftKings-shape regulatory-unlock user growth
            fee_bearing_share=0.917,         # mix-derived: non-politics (78%) × 95% + politics (22%) × 80%.
                                             # 2024-era NegRisk tail decays under regulatory progress;
                                             # 2028-cycle NegRisk deploys fee-bearing from day one.
            net_take_rate=0.00380,           # Bear anchor 0.28% × retention lift 1.44× (9%→13%) ×
                                             # mix gross ratio 0.918 = 0.38%. Sportsbook migrants are
                                             # hold-to-resolution users; they don't exploit NegRisk
                                             # offsets the way politics-native retail does. Modest
                                             # retention improvement, partially offset by sports-heavy
                                             # mix having a lower fee-schedule ceiling.
        ),
        probability_sources=[
            "Kalshi CFTC DC Circuit win establishes event-contract precedent",
            "CFTC leadership signals pro-market (Pham chair)",
            "ICE investment = strategic legitimisation",
            "observed: MAU grew through all three fee activations, not down",
        ],
    )
    bull = World(
        name="Bull",
        probability=6.5/17,
        narrative=(
            "Prediction markets as financial primitive. ICE institutional distribution "
            "activates. Data/derivatives licensing becomes real. 2028 election supercycle "
            "drives non-sports volume sustained. Token launches with credible value capture. "
            "International TAM expands materially. Volume 5.68× from current (~$34.0B/mo by Q1 2029)."
        ),
        regulatory_assumption=(
            "CFTC clarity + federal preemption of state actions. Base-rate upside: "
            "no_action (12.5%) + favorable-restructured outcomes."
        ),
        drivers_q1_2029=WorldDrivers(
            volume_monthly_usd=bull_vol_mo,
            ttm_volume_annual_usd=bull_ttm,
            mau=current_mau * 7.0,           # DraftKings-shape + 1.25× category-creation premium
            fee_bearing_share=0.930,         # mix-derived: non-politics (80%) × 95% + politics (20%) × 85%.
                                             # Full regime maturation; fresh institutional categories deploy
                                             # fee-bearing from day one; only permanent geopolitics drag.
            net_take_rate=0.00400,           # Institutional-mix decomposition (see module docstring):
                                             # 60% retail-like @ Base net 0.38% + 40% institutional
                                             # @ 0.42% (retention lift 2.0× × tiering compression 0.55)
                                             # blends to ~0.40%. Upside over Base is modest because
                                             # institutional tiering (maker rebates, volume tiers)
                                             # compresses gross roughly as much as mid-probability
                                             # clustering lifts retention. Data/clearing captures the
                                             # institutional upside as a separate non-trading line.
            data_and_clearing_revenue=75e6,  # QCEX clearing ~$45M (~3% of trading) + data/index
                                             # licensing ~$30M. Conservative vs mature analogues
                                             # (CME data 10%, ICE data 19% of total); 3-year-old
                                             # franchise lands well below mature levels.
        ),
        probability_sources=[
            "structural primitive hypothesis (Coplan-led execution)",
            "ICE distribution activation (rumoured, not yet public)",
            "2028 US presidential cycle — observed 2024 peak was $450M/mo at 78k MAU",
            "growth signals: MAU 14%/mo, volume 28%/mo over last 6mo",
        ],
    )
    return [bear, base, bull]


def main() -> None:
    agg = json.loads((ROOT / "outputs" / "dune_aggregates.json").read_text())
    cs = agg["current_state"]
    current_vol = cs["volume_usdc_monthly"]
    current_mau = cs["mau_monthly"]
    worlds = build_worlds(current_vol, current_mau)
    out = []
    ev_revenue = 0.0
    for w in worlds:
        rev = w.drivers_q1_2029.annual_revenue()
        ev_revenue += w.probability * rev
        out.append({
            "name": w.name,
            "probability": w.probability,
            "narrative": w.narrative,
            "regulatory_assumption": w.regulatory_assumption,
            "drivers_q1_2029": asdict(w.drivers_q1_2029),
            "revenue_q1_2029": rev,
            "probability_sources": w.probability_sources,
        })
    prob_sum = sum(w["probability"] for w in out)
    result = {
        "worlds": out,
        "prob_weighted_revenue_q1_2029": ev_revenue,
        "probability_sum": prob_sum,
        "current_anchor": cs,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, default=float, indent=2))
    print(f"wrote {OUT}")
    for w in out:
        print(f"  {w['name']:6s} p={w['probability']:.3f} rev_q1_2029=${w['revenue_q1_2029']/1e9:.2f}B")
    print(f"  EV           rev_q1_2029=${ev_revenue/1e9:.2f}B  (prob_sum={prob_sum:.3f})")


if __name__ == "__main__":
    main()
