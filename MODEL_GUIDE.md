# Polymarket Valuation - Model & Assumptions Guide

This repository backs the investment memo at
`outputs/polymarket_memo.pdf`. It exists so the model and
assumptions are auditable - every number in the memo traces to code and
source data here.

Use this guide to inspect assumptions, stress-test inputs, or reconcile
specific memo claims against the underlying calculations.

## Key model anchors

| Anchor | Value | Source of truth |
|---|---|---|
| Monthly volume (Mar 2026, single-sided USDC) | $5.98B | `outputs/dune_aggregates.json` |
| Net protocol fees (Mar 2026) | $16.9M/mo, $203M annualised | derived from on-chain events |
| Net take rate (effective, post-refund) | 0.283% | derived; cross-checks DefiLlama within 2% |
| Volume scalars (Bear / Base / Bull) | 1.00× / 4.54× / 5.68× current | `analysis/growth_comps.py` (DK 2021–2024 handle comp: post-PASPA unlock + breakthrough-to-scale) |
| World probabilities (Bear / Base / Bull) | 29% / 32% / 38% | `analysis/worlds.py`; base rates from a 17-case high-relevance subset of `data/regulatory_events.json` |
| EV/Sales multiples (mid) | 10× / 25× / 50× | `analysis/comp_framework.py`; Coinbase, Robinhood, Kalshi, Hyperliquid comp panel |
| IPO hold period | 6yr | `analysis/exit_paths.py` (S-1 prep + two audited years from Q1 2029 ARR base) |
| Realised-FDV proration | `(target/hold)^0.75` sub-linear | `analysis/exit_paths.py` |

## Where to find each assumption

- `outputs/polymarket_memo.pdf` - memo prose; authoritative source for claims and wording
- `analysis/worlds.py` - per-world drivers + full docstring derivation of take rates and fee-bearing shares
- `analysis/growth_comps.py` - volume trajectories + DK handle comp methodology
- `analysis/comp_framework.py` - comp panel + per-world multiple ranges with rationale
- `analysis/exit_paths.py` - per-world exit-path mix (M&A / secondary / IPO / wind-down), realised-factor per path, proration
- `analysis/price_ladder.py` - entry-price ladder computation
- `analysis/regulatory_events.py` - regulatory base-rate derivation from the event dataset
- `data/regulatory_events.json` - curated regulatory-event dataset (42 total; 17 high-relevance used for base rates)
- `data/tam_sources.json` - Keyrock × Dune industry data anchors
- `data/regulatory.json` - state-AG counts, SCOTUS status, international blocks
- `data/fee_schedule.json` - per-category fee rates

## Stress-testing patterns

Common questions and where they can be probed:

- **"What if Bull take rate is 0.38% (matches Base)?"**
  → `analysis/worlds.py` - Bull block, `net_take_rate` field
  → re-run `worlds.py → comp_framework.py → exit_paths.py → price_ladder.py`

- **"What if Bull multiple is 40× instead of 50×?"**
  → `analysis/comp_framework.py` - `PER_WORLD_MULTIPLES["Bull"]["mid"]`
  → re-run `comp_framework.py → exit_paths.py → price_ladder.py`

- **"What if Bear probability is higher?"**
  → `analysis/worlds.py` - `probability` field in each World (must sum to 1)
  → full re-run from `worlds.py`

- **"What if Base growth is slower than DK's 4.54×?"**
  → `analysis/growth_comps.py` - `WORLD_SCALARS["Base"]` (Base scalar on the DK-handle anchor; Bull = 1.25× DK, Bear is an explicit multiplier on current Polymarket volume)
  → re-run `growth_comps.py → worlds.py → comp_framework.py → exit_paths.py → price_ladder.py`
  → the Keyrock × Dune industry projection is a cross-check on the implied Polymarket share, not an input — see the "internal-consistency checks" section below

## Methodology choices worth knowing

- **Revenue formula** (`analysis/worlds.py`): `TTM volume × net take rate`.
  The observed net take rate is on TOTAL volume (includes fee-free
  geopolitics carve-out and NegRisk legacy tail), so no separate
  fee-bearing-share multiplier - the drag is already embedded.

- **TTM proration** (`analysis/growth_comps.py`): growth worlds apply a
  0.87 ramp factor (TTM averages ~87% of endpoint on a geometric ramp).
  Flat trajectories (Bear) use endpoint × 12.

- **Realised vs modelled FDV** (`analysis/exit_paths.py`): sub-linear
  proration `(target / hold)^0.75` for paths with hold > 3yr target -
  captures some pre-IPO secondary liquidity rather than strict linear.

- **Industry-share vs TAM framework** (memo §2): sizing anchors on
  observed prediction-market industry data (Keyrock × Dune Nov-2025
  snapshot: $44B 2025 YTD, Polymarket 49% share, $156B Nov run-rate) and
  projects industry volume via 17–75% CAGR. Component TAM layers
  (sports handle, crypto-native, new-category) are sanity checks on
  where demand sits, not the SOM denominator.

## Quick internal-consistency checks

- **Bear revenue ≥ current observed ARR?** Yes - Bear is stagnation: TTM
  volume × observed take rate = $203M, matching current-state
  annualised. Bear is flat, not decline.
- **DK-handle volume scalars tie to Keyrock-industry share?** Yes by
  construction - Base 4.54× current = ~50% of a projected $650B 2029
  industry; Bull 5.68× = ~48% of $850B.
- **Net take rate anchored on observed?** Yes - 0.283% comes directly
  from Dune-derived net fees / Dune-derived volume for March 2026,
  cross-checked against DefiLlama's `fees/polymarket` endpoint within
  2%.

## Re-running the model after editing an assumption

The PDF in `outputs/` is the finished deliverable. Every table and chart
in it is backed by the JSONs in `outputs/`, and those are fully
reproducible - re-run the pipeline to regenerate them:

```bash
python3 analysis/dune_ingest.py
python3 analysis/growth_comps.py
python3 analysis/worlds.py
python3 analysis/comp_framework.py
python3 analysis/exit_paths.py
python3 analysis/price_ladder.py
python3 analysis/regulatory_events.py
python3 analysis/liquidity_concentration.py
```

Dependencies: Python 3.11, `pandas`, `pyarrow`.
