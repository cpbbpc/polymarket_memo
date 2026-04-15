-- Top 1000 wallets by 18-month cumulative USDC volume (ctfexchange only).
-- Output: data/dune/top_traders_18mo.csv
SELECT
  maker AS wallet,
  COUNT(*) AS trades,
  SUM(CASE WHEN makerAssetId = 0
           THEN makerAmountFilled / 1e6
           ELSE takerAmountFilled / 1e6 END) AS volume_usdc,
  MIN(evt_block_time) AS first_trade,
  MAX(evt_block_time) AS last_trade
FROM polymarket_polygon.CTFExchange_evt_OrderFilled
WHERE evt_block_time >= timestamp '2024-10-01'
  AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
GROUP BY maker
ORDER BY volume_usdc DESC
LIMIT 1000
