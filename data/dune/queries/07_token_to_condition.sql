-- Token_id → condition_id mapping for all registered outcome tokens.
-- Used to join trade-level events back to per-market metadata.
-- Output: data/dune/token_to_condition.parquet (gitignored - regenerate from this query)
SELECT DISTINCT conditionId, token0, token1
FROM polymarket_polygon.ctfexchange_evt_tokenregistered
UNION
SELECT DISTINCT conditionId, token0, token1
FROM polymarket_polygon.negriskctfexchange_evt_tokenregistered
