-- Volume-weighted average outcome-token price per month, per exchange.
-- Computed from BUY fills only (where maker paid USDC → maker asset = 0).
-- Output: data/dune/avg_price_monthly.csv
-- Used to convert outcome-token-denominated fees into USD equivalents.
SELECT
  date_trunc('month', evt_block_time) AS month,
  'regular' AS exchange,
  SUM(CAST(makerAmountFilled AS DOUBLE)) / NULLIF(SUM(CAST(takerAmountFilled AS DOUBLE)), 0) AS avg_price_vw,
  COUNT(*) AS buy_fills,
  SUM(CAST(makerAmountFilled AS DOUBLE)) / 1e6 AS usdc_volume
FROM polymarket_polygon.ctfexchange_evt_orderfilled
WHERE makerAssetId = 0
  AND evt_block_time >= timestamp '2024-10-01'
  AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
GROUP BY 1
UNION ALL
SELECT
  date_trunc('month', evt_block_time) AS month,
  'negrisk' AS exchange,
  SUM(CAST(makerAmountFilled AS DOUBLE)) / NULLIF(SUM(CAST(takerAmountFilled AS DOUBLE)), 0) AS avg_price_vw,
  COUNT(*) AS buy_fills,
  SUM(CAST(makerAmountFilled AS DOUBLE)) / 1e6 AS usdc_volume
FROM polymarket_polygon.negriskctfexchange_evt_orderfilled
WHERE makerAssetId = 0
  AND evt_block_time >= timestamp '2024-10-01'
GROUP BY 1
ORDER BY 1, 2
