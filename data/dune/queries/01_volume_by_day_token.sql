-- Daily USDC volume per outcome_token_id on ctfexchange ONLY.
-- Output: data/dune/volume_by_day_token.parquet (gitignored - regenerate from this query)
-- Run time: ~1-2 min. Result ~2.6M rows, 332MB as CSV, 193MB as parquet.
SELECT
  date_trunc('day', evt_block_time) AS day,
  CASE WHEN makerAssetId = 0 THEN takerAssetId ELSE makerAssetId END AS outcome_token_id,
  COUNT(*) AS fills,
  SUM(CASE WHEN makerAssetId = 0
           THEN makerAmountFilled / 1e6
           ELSE takerAmountFilled / 1e6 END) AS volume_usdc,
  -- Note: fee_usdc_estimated below is INVERTED (takerAmount/makerAmount for BUY should have been makerAmount/takerAmount)
  -- Use fees_by_day_split.sql instead for correct fees. Column kept for backward compat.
  SUM(CASE WHEN makerAssetId = 0
           THEN fee * (takerAmountFilled::DOUBLE) / makerAmountFilled / 1e6
           ELSE fee / 1e6 END) AS fee_usdc_estimated
FROM polymarket_polygon.CTFExchange_evt_OrderFilled
WHERE evt_block_time >= timestamp '2024-10-01'
  AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
GROUP BY 1, 2
ORDER BY 1 DESC
