-- Monthly unique makers (MAU) across regular + negRisk exchanges.
-- Output: data/dune/mau_monthly_combined.csv
-- Dedup filter: for regular exchange, filter to taker = CTFExchange so maker = the real participant.
-- NegRisk has no equivalent contract-as-taker pattern (all makers are real participants).
WITH all_makers AS (
  SELECT date_trunc('month', evt_block_time) AS month, maker
  FROM polymarket_polygon.ctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2024-10-01'
    AND taker = 0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e
  UNION ALL
  SELECT date_trunc('month', evt_block_time) AS month, maker
  FROM polymarket_polygon.negriskctfexchange_evt_orderfilled
  WHERE evt_block_time >= timestamp '2024-10-01'
)
SELECT month, COUNT(DISTINCT maker) AS unique_makers, COUNT(*) AS fills
FROM all_makers
GROUP BY 1
ORDER BY 1
