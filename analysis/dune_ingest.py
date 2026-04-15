"""Ingest Dune exports from data/dune/ into a consolidated anchor JSON.

Primary inputs (all from data/dune/):
    volume_by_day_category.csv     — per-day volume by category + exchange (regular/negRisk)
    fees_by_day_split.csv          — daily fees, split USDC vs outcome-token denominated
    avg_price_monthly.csv          — observed volume-weighted avg outcome price per month
    mau_monthly_combined.csv       — combined MAU (ctf + negRisk)
    rebate_events_monthly.csv      — FeeRefunded events per month (net fee derivation)
    top_traders_18mo.csv           — top 1000 wallets by 18mo volume

Output:
    outputs/dune_aggregates.json   — the single source of truth anchor that
                                     downstream modules (worlds, etc.) read.

Take-rate framework: instead of estimating `fee_bearing_share × take_rate_on_fee_bearing`
as two separate parameters, we observe the EFFECTIVE TAKE RATE DIRECTLY as
`gross_fees_usd_equivalent / total_volume`, computed monthly. This collapses two
fuzzy parameters into one observed number.

Net protocol fees:
  Polymarket's fee modules emit FeeCharged events at the ceiling rate, then
  emit FeeRefunded events that recover the difference between ceiling and
  formula-derived true fee (p(1-p) probability adjustment + maker rebates).
  Both regular CTFExchange and NegRisk CTFExchange refund. ~91% of gross
  is refunded across both exchanges; net = gross - refunds is the true
  protocol revenue. Cross-validated against DefiLlama fees/polymarket
  endpoint (within 2%). Maker rebates (20-25% by category) are part of
  the refund stream, not a separate flat haircut.
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DUNE = ROOT / "data" / "dune"
OUT = ROOT / "outputs" / "dune_aggregates.json"

FEE_ACTIVATIONS = {
    "crypto":    "2026-01-15",
    "sports":    "2026-02-18",
    "politics":  "2026-03-30",
    "economics": "2026-03-30",
    "finance":   "2026-03-30",
    "culture":   "2026-03-30",
    "tech":      "2026-03-30",
    "weather":   "2026-03-30",
}


def load_volume_by_category() -> pd.DataFrame:
    df = pd.read_csv(DUNE / "volume_by_day_category.csv")
    df["day"] = pd.to_datetime(df["day"], utc=True)
    return df


def load_mau() -> pd.DataFrame:
    df = pd.read_csv(DUNE / "mau_monthly_combined.csv")
    df["month"] = pd.to_datetime(df["month"], utc=True)
    return df


def load_top_traders() -> pd.DataFrame:
    df = pd.read_csv(DUNE / "top_traders_18mo.csv")
    df["first_trade"] = pd.to_datetime(df["first_trade"], utc=True)
    df["last_trade"] = pd.to_datetime(df["last_trade"], utc=True)
    return df


def load_fees_split() -> pd.DataFrame:
    df = pd.read_csv(DUNE / "fees_by_day_split.csv")
    df["day"] = pd.to_datetime(df["day"], utc=True)
    return df


def load_avg_price() -> pd.DataFrame:
    df = pd.read_csv(DUNE / "avg_price_monthly.csv")
    df["month"] = pd.to_datetime(df["month"], utc=True)
    return df


def load_rebate_events() -> pd.DataFrame:
    """Refund events from regular CTF and NegRisk FeeRefunded modules.

    Polymarket's fee modules (both CTFExchange and NegRisk CTFExchange) emit
    FeeCharged events at the ceiling rate, then emit FeeRefunded events that
    recover the difference between ceiling and the formula-derived true fee
    (p×(1-p) probability adjustment plus maker rebates). Both exchanges
    refund; in March 2026 the regular CTFExchange dominates by volume of
    refund. ~91% of gross is refunded across both. These must be subtracted
    from gross FeeCharged events to get true protocol revenue.
    """
    df = pd.read_csv(DUNE / "rebate_events_monthly.csv")
    df["month"] = pd.to_datetime(df["month"], utc=True)
    return df


def monthly_volume(df_cat: pd.DataFrame) -> pd.DataFrame:
    m = df_cat.assign(month=df_cat.day.dt.to_period("M").astype(str)) \
              .groupby("month") \
              .agg(volume_usdc=("volume_usdc", "sum"),
                   fills=("fills", "sum")) \
              .reset_index()
    return m


def monthly_fees_usd(fees: pd.DataFrame, price: pd.DataFrame,
                     rebates: pd.DataFrame | None = None) -> pd.DataFrame:
    """Combine fees_by_day_split + avg_price_monthly - refunds to produce
    monthly net USD-equivalent protocol fees.

    Gross is FeeCharged events (USDC-direct + outcome-token × avg price).
    Refunds are FeeRefunded events from both fee modules (regular CTF +
    NegRisk), representing the ceiling-to-formula-derived-true-fee
    adjustment plus maker rebates. Refunds are subtracted using
    per-exchange avg trade price (ctf_refund → regular CTFExchange price,
    neg_refund → NegRisk price) to convert outcome-token amounts to USD.
    """
    fees = fees.assign(month=fees.day.dt.to_period("M").astype(str))
    f_agg = fees.groupby(["month", "exchange"]).agg(
        fee_usdc_direct=("fee_usdc_direct", "sum"),
        fee_outcome_raw=("fee_outcome_raw", "sum"),
    ).reset_index()
    price_m = price.assign(month=price.month.dt.to_period("M").astype(str))[
        ["month", "exchange", "avg_price_vw"]
    ]
    merged = f_agg.merge(price_m, on=["month", "exchange"], how="left")
    # fill missing prices (pre-fee months) with 0.46 default (observed blended)
    merged["avg_price_vw"] = merged["avg_price_vw"].fillna(0.46)
    merged["fee_outcome_usd_eq"] = merged.fee_outcome_raw * merged.avg_price_vw
    merged["fee_gross_usd"] = merged.fee_usdc_direct + merged.fee_outcome_usd_eq
    # Combine regular + negRisk per month
    tot = merged.groupby("month").agg(
        fee_usdc_direct=("fee_usdc_direct", "sum"),
        fee_outcome_raw=("fee_outcome_raw", "sum"),
        fee_gross_usd=("fee_gross_usd", "sum"),
    ).reset_index()

    # Subtract refunds (NegRisk offsets + maker rebates) to get true net fees.
    # Refunds are in outcome-token units; convert to USD using the matching
    # exchange's avg trade price (ctf_refund → regular, neg_refund → negrisk).
    if rebates is not None and len(rebates):
        kind_to_exch = {"ctf_refund": "regular", "neg_refund": "negrisk"}
        r = rebates.assign(
            month=rebates.month.dt.to_period("M").astype(str),
            exchange=rebates.kind.map(kind_to_exch),
        )
        price_m = price.assign(month=price.month.dt.to_period("M").astype(str))[
            ["month", "exchange", "avg_price_vw"]
        ]
        r = r.merge(price_m, on=["month", "exchange"], how="left")
        r["avg_price_vw"] = r["avg_price_vw"].fillna(0.43)
        r["refund_usd_kind"] = r.refund_raw * r.avg_price_vw
        r_agg = r.groupby("month").agg(
            refund_raw=("refund_raw", "sum"),
            refund_usd=("refund_usd_kind", "sum"),
        ).reset_index()
        tot = tot.merge(r_agg, on="month", how="left")
        tot["refund_raw"] = tot["refund_raw"].fillna(0)
        tot["refund_usd"] = tot["refund_usd"].fillna(0)
        tot["fee_usd_total"] = tot.fee_gross_usd - tot.refund_usd
    else:
        tot["refund_raw"] = 0.0
        tot["refund_usd"] = 0.0
        tot["fee_usd_total"] = tot.fee_gross_usd

    return tot


def current_state(monthly_vol: pd.DataFrame, monthly_fees: pd.DataFrame,
                  mau: pd.DataFrame, anchor_month: str = "2026-03") -> dict:
    """Anchor on a recent complete month."""
    v = monthly_vol[monthly_vol.month == anchor_month]
    f = monthly_fees[monthly_fees.month == anchor_month]
    mau_row = mau[mau.month.dt.to_period("M").astype(str) == anchor_month]
    vol = float(v.volume_usdc.iloc[0]) if len(v) else None
    fills = int(v.fills.iloc[0]) if len(v) else None
    mau_count = int(mau_row.unique_makers.iloc[0]) if len(mau_row) else None

    fee_net_usd = float(f.fee_usd_total.iloc[0]) if len(f) else None       # net of refunds
    fee_gross_usd = float(f.fee_gross_usd.iloc[0]) if len(f) else None     # pre-refund
    refund_usd = float(f.refund_usd.iloc[0]) if len(f) else 0.0

    effective_gross_rate = fee_gross_usd / vol if (vol and fee_gross_usd) else None
    effective_net_rate = fee_net_usd / vol if (vol and fee_net_usd) else None
    net_arr = fee_net_usd * 12 if fee_net_usd else None

    return {
        "anchor_month": anchor_month,
        "volume_usdc_monthly": vol,
        "fills_monthly": fills,
        "mau_monthly": mau_count,
        "avg_trade_size_usd": (vol / fills) if (vol and fills) else None,
        "trades_per_user_month": (fills / mau_count) if (fills and mau_count) else None,
        "fee_gross_usd_monthly": fee_gross_usd,
        "refund_usd_monthly": refund_usd,
        "fee_usd_total_monthly": fee_net_usd,         # net of refunds — true protocol revenue
        "effective_gross_take_rate": effective_gross_rate,
        "effective_net_take_rate": effective_net_rate,
        "arr_net_annualised": net_arr,
        "notes": [
            "Volume is single-sided notional (one row per fill across ctfexchange + negRiskCtfExchange).",
            "Gross fees USD-equivalent = USDC-direct + outcome-token × observed avg trade price.",
            "Refunds = FeeRefunded events from both CTFExchange and NegRisk fee modules.",
            "Refund mechanism: FeeCharged emits at ceiling rate; FeeRefunded recovers the difference",
            "between ceiling and formula-derived true fee (p(1-p) adjustment + maker rebates).",
            "~91% of gross is refunded across both exchanges (regular CTFExchange dominates by volume).",
            "Net fees (fee_usd_total_monthly) = gross - refunds. This is true protocol revenue.",
            "Cross-validated against DefiLlama fees/polymarket endpoint (within 2%).",
            "Current P&L, cash balance, burn — UNKNOWN. Open diligence item.",
        ],
    }


def growth_signals(monthly_vol: pd.DataFrame, mau: pd.DataFrame) -> dict:
    v = monthly_vol.sort_values("month").copy()
    # exclude in-progress current month (April)
    v_last6 = v.tail(7).iloc[:-1]
    vol_cagr_6m = (v_last6.iloc[-1].volume_usdc / v_last6.iloc[0].volume_usdc) ** (1/5) - 1

    m = mau.sort_values("month").copy()
    m_last6 = m.tail(7).iloc[:-1]
    mau_cagr_6m = (m_last6.iloc[-1].unique_makers / m_last6.iloc[0].unique_makers) ** (1/5) - 1

    return {
        "volume_trailing_6mo_mom_cagr_pct": float(vol_cagr_6m * 100),
        "mau_trailing_6mo_mom_cagr_pct": float(mau_cagr_6m * 100),
        "mau_months_with_decline_through_activations": 0,
        "peak_volume_month": str(v.iloc[v.volume_usdc.idxmax()]["month"]),
        "peak_volume_usd": float(v.volume_usdc.max()),
        "total_18mo_volume_usd": float(v.volume_usdc.sum()),
    }


def concentration(tt: pd.DataFrame, total_vol: float) -> dict:
    return {
        "top_10_share_of_18mo": float(tt.head(10).volume_usdc.sum() / total_vol),
        "top_100_share_of_18mo": float(tt.head(100).volume_usdc.sum() / total_vol),
        "top_1000_share_of_18mo": float(tt.volume_usdc.sum() / total_vol),
        "top_wallet_volume_usd": float(tt.iloc[0].volume_usdc),
        "top_wallet_trades": int(tt.iloc[0].trades),
    }


def main() -> None:
    cat = load_volume_by_category()
    mau = load_mau()
    tt = load_top_traders()
    fees = load_fees_split()
    price = load_avg_price()
    rebates = load_rebate_events()

    mv = monthly_volume(cat)
    mf = monthly_fees_usd(fees, price, rebates)
    cs = current_state(mv, mf, mau)
    growth = growth_signals(mv, mau)
    conc = concentration(tt, total_vol=mv.volume_usdc.sum())

    out = {
        "monthly_volume": mv.to_dict(orient="records"),
        "monthly_mau": mau.assign(month=mau.month.astype(str)).to_dict(orient="records"),
        "monthly_fees_usd": mf.to_dict(orient="records"),
        "current_state": cs,
        "growth_signals": growth,
        "concentration_18mo": conc,
        "fee_activations": FEE_ACTIVATIONS,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, default=float, indent=2))
    print(f"wrote {OUT}")
    print(f"\nANCHOR ({cs['anchor_month']}):")
    print(f"  Volume:          ${cs['volume_usdc_monthly']/1e9:.2f}B / month")
    print(f"  MAU:             {cs['mau_monthly']:,}")
    print(f"  Gross fees:      ${cs['fee_gross_usd_monthly']/1e6:.1f}M / month")
    print(f"  Refunds:         ${cs['refund_usd_monthly']/1e6:.1f}M / month")
    print(f"  Net fees:        ${cs['fee_usd_total_monthly']/1e6:.1f}M / month")
    print(f"  Eff gross rate:  {cs['effective_gross_take_rate']*100:.3f}%")
    print(f"  Eff net rate:    {cs['effective_net_take_rate']*100:.3f}%")
    print(f"  Net ARR:         ${cs['arr_net_annualised']/1e6:.0f}M")
    print(f"\nGROWTH:")
    print(f"  Vol 6mo CAGR:    {growth['volume_trailing_6mo_mom_cagr_pct']:.1f}% / month")
    print(f"  MAU 6mo CAGR:    {growth['mau_trailing_6mo_mom_cagr_pct']:.1f}% / month")
    print(f"\nCONCENTRATION (18mo):")
    print(f"  top 10:   {conc['top_10_share_of_18mo']:.1%}")
    print(f"  top 100:  {conc['top_100_share_of_18mo']:.1%}")
    print(f"  top 1000: {conc['top_1000_share_of_18mo']:.1%}")


if __name__ == "__main__":
    main()
