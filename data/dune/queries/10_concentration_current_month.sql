-- Current-month concentration snapshot (March 2026 anchor).
-- Two parts, exported separately.

-- Part A: Top-50 markets by March 2026 volume (combined exchanges)
-- Output: data/dune/top_markets_march2026.csv
WITH current_month_trades AS (
  SELECT
    CASE WHEN CAST(makerAssetId AS varchar) = '0' THEN takerAssetId ELSE makerAssetId END AS outcome_token_id,
    CASE WHEN CAST(makerAssetId AS varchar) = '0'
         THEN makerAmountFilled / 1e6 ELSE takerAmountFilled / 1e6 END AS volume_usdc
  FROM polymarket_polygon.ctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2026-03-01'
    AND evt_block_time <  timestamp '2026-04-01'
    AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
  UNION ALL
  SELECT
    CASE WHEN CAST(makerAssetId AS varchar) = '0' THEN takerAssetId ELSE makerAssetId END AS outcome_token_id,
    CASE WHEN CAST(makerAssetId AS varchar) = '0'
         THEN makerAmountFilled / 1e6 ELSE takerAmountFilled / 1e6 END AS volume_usdc
  FROM polymarket_polygon.negriskctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2026-03-01'
    AND evt_block_time <  timestamp '2026-04-01'
),
token_map AS (
  SELECT DISTINCT tid, conditionId FROM (
    SELECT token0 AS tid, conditionId FROM polymarket_polygon.ctfexchange_evt_tokenregistered
    UNION ALL SELECT token1, conditionId FROM polymarket_polygon.ctfexchange_evt_tokenregistered
    UNION ALL SELECT token0, conditionId FROM polymarket_polygon.negriskctfexchange_evt_tokenregistered
    UNION ALL SELECT token1, conditionId FROM polymarket_polygon.negriskctfexchange_evt_tokenregistered
  )
)
SELECT tm.conditionId AS condition_id, SUM(t.volume_usdc) AS volume_usdc, COUNT(*) AS fills
FROM current_month_trades t
LEFT JOIN token_map tm ON t.outcome_token_id = tm.tid
GROUP BY 1
ORDER BY 2 DESC
LIMIT 50;

-- Part B: Top-100 traders by March 2026 volume (combined)
-- Output: data/dune/top_traders_march2026.csv
WITH all_trades AS (
  SELECT maker,
    CASE WHEN CAST(makerAssetId AS varchar) = '0'
         THEN makerAmountFilled / 1e6 ELSE takerAmountFilled / 1e6 END AS volume_usdc
  FROM polymarket_polygon.ctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2026-03-01'
    AND evt_block_time <  timestamp '2026-04-01'
    AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
  UNION ALL
  SELECT maker,
    CASE WHEN CAST(makerAssetId AS varchar) = '0'
         THEN makerAmountFilled / 1e6 ELSE takerAmountFilled / 1e6 END AS volume_usdc
  FROM polymarket_polygon.negriskctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2026-03-01'
    AND evt_block_time <  timestamp '2026-04-01'
)
SELECT maker AS wallet, SUM(volume_usdc) AS volume_usdc, COUNT(*) AS trades
FROM all_trades
GROUP BY 1
ORDER BY 2 DESC
LIMIT 100;
