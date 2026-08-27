"""Explicit offline command for training and persisting the price AVM.

Usage:
    python -m train.train_avm path/to/training-properties.json --trials 100

The JSON file must contain an array of ``real_estate`` payloads with a
``predictions.suggested_price`` target. It is intentionally not exposed by an
HTTP route.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from radar.data_base import data_type as data
from train.avm import train_price_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and persist the Tupan price AVM.")
    parser.add_argument("dataset", type=Path, help="JSON array of real_estate training payloads")
    parser.add_argument("--trials", type=int, default=100, help="Optuna trials (default: 100)")
    parser.add_argument("--seed", type=int, default=None, help="Optional deterministic random seed")
    parser.add_argument("--model-path", type=Path, default=None, help="Override AVM_MODEL_PATH")
    parser.add_argument("--metadata-path", type=Path, default=None, help="Override AVM_MODEL_METADATA_PATH")
    args = parser.parse_args()

    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("The AVM training dataset must be a JSON array of real_estate payloads.")
    records = [data.real_estate.model_validate(item) for item in payload]
    result = train_price_model(
        records,
        seed=args.seed,
        n_trials=args.trials,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
