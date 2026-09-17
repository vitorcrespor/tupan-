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
from pathlib import Path

from dotenv import load_dotenv

from backend.services.platform_intelligence import PlatformIntelligenceService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare global Tupan intelligence outside HTTP requests.")
    commands = parser.add_subparsers(dest="command", required=True)
    heatmap = commands.add_parser("refresh-heatmap", help="Publish global market-heat snapshots for one or more H3 resolutions.")
    heatmap.add_argument(
        "--h3-resolution", dest="h3_resolutions", type=int, action="append",
        help="H3 resolution to publish; repeat the flag for multiple independent publications (default: 9).",
    )
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
    ingestion = commands.add_parser(
        "import-itbi-campinas-observations",
        help="Preview or idempotently import the structured Campinas ITBI observations for offline AVM training.",
    )
    ingestion.add_argument("--source", type=Path, default=None, help="Curated workbook; defaults to the local Campinas ITBI source.")
    ingestion.add_argument("--geocode-cache", type=Path, default=None, help="Existing local neighborhood-geocode cache; Google is never called.")
    ingestion.add_argument("--apply", action="store_true", help="Persist observations. Without this flag, only validate and report coverage.")
    commands.add_parser(
        "publish-liquidity-model",
        help="Publish the global right-censored listing-liquidity survival model.",
    )
    return parser


async def _run(args: argparse.Namespace) -> dict[str, object]:
    service = PlatformIntelligenceService()
    if args.command == "refresh-heatmap":
        results = await service.refresh_heatmaps(h3_resolutions=args.h3_resolutions or [9], allow_empty=args.allow_empty)
        publications = [{
            "source_estate_count": result.source_estate_count,
            "sale_source_count": result.sale_source_count,
            "aggregate_count": result.aggregate_count,
            "heat_cell_count": result.heat_cell_count,
            "liquidity_cell_count": result.liquidity_cell_count,
            "h3_resolution": result.h3_resolution,
            "period_start": result.period_start.isoformat(),
            "period_end": result.period_end.isoformat(),
        } for result in results]
        # Preserve the original one-resolution result shape for scripts that
        # already consume it, while making all publications explicit.
        return {**(publications[0] if len(publications) == 1 else {}), "publications": publications}
    if args.command == "train-transaction-avm":
        return await service.train_transaction_avm(seed=args.seed, n_estimators=args.n_estimators)
    if args.command == "import-itbi-campinas-observations":
        if args.apply:
            return await service.import_itbi_campinas_observations(
                source=args.source,
                geocode_cache=args.geocode_cache,
            )
        report = await service.preview_itbi_campinas_observations(
            source=args.source,
            geocode_cache=args.geocode_cache,
        )
        return report
    if args.command == "publish-liquidity-model":
        return await service.publish_liquidity_survival_model()
    return await service.train_avm(trials=args.trials, seed=args.seed)


def main() -> None:
    # FastAPI loads this file during app startup. The offline publisher runs in
    # a separate process, so it must load the same backend-only configuration
    # before constructing its platform repository.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    args = _parser().parse_args()
    print(json.dumps(asyncio.run(_run(args)), sort_keys=True))


if __name__ == "__main__":
    main()
