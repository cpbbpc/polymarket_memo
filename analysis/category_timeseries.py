"""Per-category monthly volume share from Dune export.

Uses data/dune/volume_by_day_category.csv which joins on-chain token registration
to our uploaded category tags. Coverage improves over time (only active markets
are in the snapshot — older resolved markets show as 'unknown').

Output: outputs/category_timeseries.json
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DUNE = ROOT / "data" / "dune"
OUT = ROOT / "outputs" / "category_timeseries.json"


def main() -> None:
    df = pd.read_csv(DUNE / "volume_by_day_category.csv")
    df["day"] = pd.to_datetime(df["day"], utc=True)
    df["month"] = df.day.dt.to_period("M").astype(str)

    # Pivot: month × category volume
    monthly = df.groupby(["month", "category"]).volume_usdc.sum().reset_index()
    pivot = monthly.pivot(index="month", columns="category", values="volume_usdc").fillna(0)
    pivot["total"] = pivot.sum(axis=1)

    # Known-category share (excludes 'unknown')
    known_cols = [c for c in pivot.columns if c not in ("unknown", "total")]
    pivot["known_total"] = pivot[known_cols].sum(axis=1)
    pivot["known_share"] = pivot["known_total"] / pivot["total"]

    # Regular vs negRisk split
    ex = df.groupby(["month", "exchange"]).volume_usdc.sum().reset_index()
    ex_pv = ex.pivot(index="month", columns="exchange", values="volume_usdc").fillna(0)
    ex_pv["negrisk_share"] = ex_pv.get("negrisk", 0) / (ex_pv.get("negrisk", 0) + ex_pv.get("regular", 0))

    out = {
        "monthly_by_category": pivot.reset_index().to_dict(orient="records"),
        "monthly_exchange_split": ex_pv.reset_index().to_dict(orient="records"),
        "latest_month": str(pivot.index.max()),
        "latest_category_mix_of_known": {
            c: float(pivot.loc[pivot.index.max(), c] / pivot.loc[pivot.index.max(), "known_total"])
            for c in known_cols if pivot.loc[pivot.index.max(), c] > 0
        },
        "notes": [
            "'unknown' category = markets not in our active-markets snapshot (mostly pre-2026 resolved markets).",
            "Coverage rises in recent months as the snapshot is dominated by still-active markets.",
            "Latest mix is informative for CURRENT composition; historical mix should be interpreted with caveats.",
        ],
    }
    OUT.write_text(json.dumps(out, default=float, indent=2))
    print(f"wrote {OUT}")
    print("latest month:", out["latest_month"])
    print(f"negRisk share (latest):", f"{ex_pv.iloc[-1]['negrisk_share']:.1%}")
    print("category mix of KNOWN volume (latest):")
    for c, v in sorted(out["latest_category_mix_of_known"].items(), key=lambda x: -x[1]):
        print(f"  {c:10s}  {v:.1%}")


if __name__ == "__main__":
    main()
