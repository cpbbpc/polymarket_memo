# data/dune - on-chain data layer

Primary data for the Polymarket memo. Every CSV in this directory has a
corresponding SQL query in `queries/` so the data is fully reproducible
from Dune Analytics.

## Files in the repo

| File | Source query | Notes |
|---|---|---|
| `volume_by_day_category.csv` | `queries/02_volume_by_day_category.sql` | Per-day volume by category × exchange (regular / NegRisk). |
| `volume_by_month_category.csv` | `queries/02_volume_by_day_category.sql` (monthly aggregation) | Monthly category-level volume series. |
| `fees_by_day_split.csv` | `queries/03_fees_by_day_split.sql` | Daily fees, split USDC-denominated vs outcome-token-denominated, by exchange. |
| `avg_price_monthly.csv` | `queries/04_avg_price_monthly.sql` | Volume-weighted average outcome price per month (used to USD-equivalent outcome-token fees). |
| `mau_monthly_combined.csv` | `queries/05_mau_monthly_combined.sql` | Unique makers per month (regular + NegRisk combined). |
| `top_traders_18mo.csv` | `queries/06_top_traders.sql` | Top 1,000 wallets by 18-month cumulative volume (ctfExchange only). |
| `top_traders_march2026.csv` | `queries/06_top_traders.sql` (Mar 2026 window) | Top wallets by March 2026 volume. |
| `top_markets_march2026.csv` | `queries/10_concentration_current_month.sql` | Market-level concentration for the anchor month. |
| `rebate_events_monthly.csv` | `queries/08_rebate_events.sql` | `FeeRefunded` events per month (NegRisk offsets + maker rebates). Net protocol revenue = gross fees − these refunds. |

## Queries only (output not committed)

A few large or unused exports are not committed; the SQL is included for
reproducibility:

- `queries/01_volume_by_day_token.sql` - per-day, per-token volume (~2.6M rows; large parquet).
- `queries/07_token_to_condition.sql` - token-id → condition-id map (~1.3M rows).

## Conventions

- **Volume** is single-sided USDC notional. Multiply by 2 to compare with
  Polymarket's public "volume" figure, which counts both sides.
- **Fees** come in two denominations on-chain:
  - `tokenId = 0` → USDC (exact USD).
  - `tokenId ≠ 0` → outcome token (convert to USD by multiplying by observed
    avg price from `avg_price_monthly.csv`).
- **Maker rebate** is 20% (crypto) / 25% (other) per Polymarket fee
  schedule, distributed off-chain daily in USDC. In the net-fee derivation
  this is captured on-chain via `FeeRefunded` events.

## Regenerating

1. Open Dune Analytics (https://dune.com) and paste the SQL from `queries/`.
2. Run (volume queries take ~1-5 min).
3. Download CSV and place in `data/dune/` with the filename shown above.
4. Re-run `python3 analysis/dune_ingest.py` to refresh `outputs/dune_aggregates.json`.
