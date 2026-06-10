-- Daily volume by category (regular + negRisk), joined via on-chain token-registration
-- mapping and uploaded token-category dataset.
-- Output: data/dune/volume_by_day_category.csv
-- Uses uploaded CSV: dune.hepworth_team_bc43a1d9.dataset_pm_token_categories
-- (generated from data/dune/uploaded_token_categories.parquet via data/build_token_category_map.py)
WITH trades_regular AS (
  SELECT
    date_trunc('day', evt_block_time) AS day,
    CASE WHEN CAST(makerAssetId AS varchar) = '0' THEN takerAssetId ELSE makerAssetId END AS outcome_token_id,
    CASE WHEN CAST(makerAssetId AS varchar) = '0'
         THEN makerAmountFilled / 1e6 ELSE takerAmountFilled / 1e6 END AS volume_usdc,
    'regular' AS exchange
  FROM polymarket_polygon.ctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2024-10-01'
    AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
),
trades_negrisk AS (
  SELECT
    date_trunc('day', evt_block_time) AS day,
    CASE WHEN CAST(makerAssetId AS varchar) = '0' THEN takerAssetId ELSE makerAssetId END AS outcome_token_id,
    CASE WHEN CAST(makerAssetId AS varchar) = '0'
         THEN makerAmountFilled / 1e6 ELSE takerAmountFilled / 1e6 END AS volume_usdc,
    'negrisk' AS exchange
  FROM polymarket_polygon.negriskctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2024-10-01'
),
trades AS (SELECT * FROM trades_regular UNION ALL SELECT * FROM trades_negrisk),
token_map AS (
  SELECT DISTINCT tid, conditionId FROM (
    SELECT token0 AS tid, conditionId FROM polymarket_polygon.ctfexchange_evt_tokenregistered
    UNION ALL SELECT token1, conditionId FROM polymarket_polygon.ctfexchange_evt_tokenregistered
    UNION ALL SELECT token0, conditionId FROM polymarket_polygon.negriskctfexchange_evt_tokenregistered
    UNION ALL SELECT token1, conditionId FROM polymarket_polygon.negriskctfexchange_evt_tokenregistered
  )
),
categories_by_condition AS (
  SELECT condition_id, MAX(category) AS category
  FROM dune.hepworth_team_bc43a1d9.dataset_pm_token_categories
  GROUP BY condition_id
),
tagged AS (
  SELECT t.day, t.volume_usdc, tm.conditionId, t.exchange
  FROM trades t
  LEFT JOIN token_map tm ON t.outcome_token_id = tm.tid
)
SELECT
  tt.day,
  tt.exchange,
  COALESCE(c.category, 'unknown') AS category,
  SUM(tt.volume_usdc) AS volume_usdc,
  COUNT(*) AS fills
FROM tagged tt
LEFT JOIN categories_by_condition c ON tt.conditionId = c.condition_id
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
