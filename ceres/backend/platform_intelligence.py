"""Explicit pre-serve platform intelligence preparation command.

Run this as a trusted release/ingestion step before serving the desktop API:
    python -m backend.platform_intelligence refresh-heatmap
    python -m backend.platform_intelligence train-avm --trials 100
    python -m backend.platform_intelligence train-transaction-avm --n-estimators 1800
"""

from __future__ import annotations

import argparse
import asyncio
import json

from backend.services.platform_intelligence import PlatformIntelligenceService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare global Tupan intelligence outside HTTP requests.")
    commands = parser.add_subparsers(dest="command", required=True)
    heatmap = commands.add_parser("refresh-heatmap", help="Publish one global platform heatmap snapshot.")
    heatmap.add_argument("--h3-resolution", type=int, default=9)
    heatmap.add_argument("--allow-empty", action="store_true", help="Allow an empty source set to replace an existing snapshot.")
    avm = commands.add_parser("train-avm", help="Train and publish the shared AVM from observed sales.")
    avm.add_argument("--trials", type=int, default=100)
    avm.add_argument("--seed", type=int, default=None)
    candidate = commands.add_parser(
        "train-transaction-avm",
        help="Train a research-aligned candidate from the explicit observation table.",
    )
    candidate.add_argument("--n-estimators", type=int, default=1800)
    candidate.add_argument("--seed", type=int, default=42)
    return parser


async def _run(args: argparse.Namespace) -> dict[str, object]:
    service = PlatformIntelligenceService()
    if args.command == "refresh-heatmap":
        result = await service.refresh_heatmap(h3_resolution=args.h3_resolution, allow_empty=args.allow_empty)
        return {
            "source_estate_count": result.source_estate_count,
            "aggregate_count": result.aggregate_count,
            "h3_resolution": result.h3_resolution,
            "period_start": result.period_start.isoformat(),
            "period_end": result.period_end.isoformat(),
        }
    if args.command == "train-transaction-avm":
        return await service.train_transaction_avm(seed=args.seed, n_estimators=args.n_estimators)
    return await service.train_avm(trials=args.trials, seed=args.seed)


def main() -> None:
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(_run(args)), sort_keys=True))


if __name__ == "__main__":
    main()
