-- Daily protocol fees charged, split by asset denomination and exchange.
-- Output: data/dune/fees_by_day_split.csv
-- Note: `tokenId = 0` means the fee was paid in USDC (exact USD).
-- `tokenId <> 0` means paid in an outcome token (USD-equivalent = amount * price at trade).
SELECT
  date_trunc('day', evt_block_time) AS day,
  'regular' AS exchange,
  SUM(CASE WHEN tokenId = 0 THEN amount / 1e6 ELSE 0 END) AS fee_usdc_direct,
  SUM(CASE WHEN tokenId <> 0 THEN amount / 1e6 ELSE 0 END) AS fee_outcome_raw,
  COUNT(CASE WHEN tokenId = 0 THEN 1 END) AS n_fees_usdc,
  COUNT(CASE WHEN tokenId <> 0 THEN 1 END) AS n_fees_outcome
FROM polymarket_polygon.ctfexchange_evt_feecharged
WHERE evt_block_time >= timestamp '2024-10-01'
GROUP BY 1
UNION ALL
SELECT
  date_trunc('day', evt_block_time) AS day,
  'negrisk' AS exchange,
  SUM(CASE WHEN tokenId = 0 THEN amount / 1e6 ELSE 0 END) AS fee_usdc_direct,
  SUM(CASE WHEN tokenId <> 0 THEN amount / 1e6 ELSE 0 END) AS fee_outcome_raw,
  COUNT(CASE WHEN tokenId = 0 THEN 1 END) AS n_fees_usdc,
  COUNT(CASE WHEN tokenId <> 0 THEN 1 END) AS n_fees_outcome
FROM polymarket_polygon.negriskctfexchange_evt_feecharged
WHERE evt_block_time >= timestamp '2024-10-01'
GROUP BY 1
ORDER BY 1, 2
