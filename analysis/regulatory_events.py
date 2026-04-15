"""Compute base-rate probabilities for regulatory outcomes from historical dataset.

Drops FTX/Binance-style category-error cases by construction (they aren't in
data/regulatory_events.json). Uses only high+medium relevance events for
base-rate counting; low-relevance events are documented for context but
excluded from the denominator.
"""
from __future__ import annotations
import collections, json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "regulatory_events.json"
OUT = ROOT / "outputs" / "regulatory_base_rates.json"


def main() -> None:
    doc = json.loads(IN.read_text())
    events = doc["events"]
    high = [e for e in events if e["relevance"] == "high"]
    medplus = [e for e in events if e["relevance"] in ("high", "medium")]

    def rates(evs: list[dict]) -> dict:
        c = collections.Counter(e["outcome"] for e in evs)
        n = sum(c.values())
        return {"n": n, "rates": {k: v / n for k, v in c.items()}, "counts": dict(c)}

    out = {
        "high_relevance_only": rates(high),
        "high_plus_medium": rates(medplus),
        "notes": [
            "Used as calibration for world-level regulatory-outcome probabilities.",
            "Bear world assumption: weight shifts toward shutdown_us / geofence_and_continue.",
            "Base world: weight on restructured / fine_and_continue / no_action.",
            "Bull world: no_action / DCM-registration pathway dominates.",
            "Explicit exclusion of FTX/Binance fraud cases — not an analogue for Polymarket's market conduct.",
        ],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")
    print(json.dumps(out["high_relevance_only"], indent=2))


if __name__ == "__main__":
    main()
