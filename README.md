# Polymarket Valuation Memo

**Question:** At what valuation should L1D invest in Polymarket?

The deliverable is `outputs/polymarket_memo.pdf`, a six-page
investment memo. This repository exposes the analysis and assumptions
underneath it so the model can be audited and stress-tested end-to-end.

## Recommendation

Equity participation at **$7.5B FDV** against a 3× return hurdle
on a three-year hold.

| Entry Point | Expected × | Posture |
|---|---|---|
| $7.5B | 3.45× | Yes |
| $10B | 2.59× | Subject to further DD |
| $12.5B | 2.07× | Pass |

Probability-weighted realised value (3-year hold): **$25.9B**.
Modelled equity value (reference ceiling): **$38.8B**.

## Current state (March 2026, on-chain)

- Monthly volume (single-sided USDC): **$5.98B**
- Unique active wallets: **747k**
- Net protocol fees: **$16.9M / month**
- Annualised net ARR: **$203M**
- Effective net take rate: **0.283%** (post-refund; gross 3.18% × 9% retention)

Cross-validated against DefiLlama `fees/polymarket` within 2%.

## Model in one paragraph

Three structural worlds (Bear / Base / Bull) with deterministic per-world
drivers. World probabilities (29% / 32% / 38%) derive from a US-weighted
regulatory-event base-rate dataset. Volume trajectories anchored on the
closest regulatory-unlock-plus-breakthrough analogue at scale - DraftKings'
2021–2024 handle growth (4.54× over three years), combining continuing
post-PASPA state-by-state unlock with DK's breakthrough-to-scale phase
(2021 was DK's first $1B-revenue year). Volume forecasts cross-check against an
independent industry-projection framework anchored on Keyrock × Dune's
observed Nov-2025 industry data (2025 YTD $44B, Polymarket 49% share,
$156B annualised run-rate). Take rates are observed on-chain and derived.
EV/Sales multiples anchor on a public-and-private comp panel (Coinbase,
Robinhood, CME, ICE, Kalshi, Hyperliquid). Modelled FDV converts to
realised value via per-world exit-path mix (M&A / Secondary / IPO /
Wind-down) with sub-linear proration on holds exceeding the 3-year target.

## Auditing the model

Every number in the memo traces to code and source data in this repo.
`MODEL_GUIDE.md` is a navigation guide for interrogating the assumptions,
probing sensitivities, and reconciling the memo's claims against the
underlying calculations.

Key auditable surfaces:

| Assumption | Where to inspect |
|---|---|
| Observed current state (volume, fees, MAU) | `outputs/dune_aggregates.json` (derived from `data/dune/*.csv`) |
| World probabilities (29 / 32 / 38%) | `analysis/worlds.py`; regulatory base rates in `outputs/regulatory_base_rates.json` |
| Volume scalars (1.0× / 4.54× / 5.68×) | `analysis/growth_comps.py`; DK handle comp |
| Net take rates (0.28 / 0.38 / 0.40%) | `analysis/worlds.py` docstring with derivation |
| EV/Sales multiples (10× / 25× / 50× mid) | `analysis/comp_framework.py`; comp panel + per-world rationale |
| Exit-path mix + realised factors | `analysis/exit_paths.py` (path weights, hold periods, proration) |
| Entry-price ladder | `outputs/price_ladder.json` (Expected × per FDV, realised at 3yr hold) |

## Repository layout

```
analysis/          Pipeline scripts (each writes one JSON to outputs/)
data/dune/         On-chain source CSVs + Dune SQL queries
data/*.json        Context data backing specific memo claims
outputs/           Canonical computed values + the final PDF
MODEL_GUIDE.md     Project guide for model interrogation
```
