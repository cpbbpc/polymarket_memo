-- Fee refund events from the FeeModule contracts.
-- NOTE: These are EXCESS-FEE refunds (refunds when an order was charged more than the
-- operator's intent), NOT the daily maker-rebate distributions. Those rebates flow
-- through a different mechanism (daily USDC distribution off-chain to makers).
-- See: https://help.polymarket.com/en/articles/13364471-maker-rebates-program
-- Output: data/dune/rebate_events_monthly.csv
SELECT
  date_trunc('month', evt_block_time) AS month,
  'ctf_refund' AS kind,
  COUNT(*) AS n,
  SUM(CAST(feeCharged AS DOUBLE) / 1e6) AS fee_charged_raw,
  SUM(CAST(refund AS DOUBLE) / 1e6) AS refund_raw
FROM polymarket_polygon.feemodule_evt_feerefunded
WHERE evt_block_time >= timestamp '2025-12-01'
GROUP BY 1
UNION ALL
SELECT
  date_trunc('month', evt_block_time) AS month,
  'neg_refund' AS kind,
  COUNT(*) AS n,
  SUM(CAST(feeCharged AS DOUBLE) / 1e6) AS fee_charged_raw,
  SUM(CAST(refund AS DOUBLE) / 1e6) AS refund_raw
FROM polymarket_polygon.negriskfeemodule_evt_feerefunded
WHERE evt_block_time >= timestamp '2025-12-01'
GROUP BY 1
ORDER BY 1, 2
