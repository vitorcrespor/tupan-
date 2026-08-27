import os
import json
from train.avm import predict_price, train_price_model

PARAM_LOG_PATH= os.getenv("PARAM_LOG_PATH")
SEED= os.getenv("SEED", "42")
global seed
seed= int(SEED)


class ForecastArtifactMissingError(RuntimeError):
    """Raised when the legacy forecast has no persisted inference artifact."""

def price_suggestion(real_estate) -> float:
    """Runtime AVM inference only; never trains or reconstructs an unfitted model."""
    return predict_price(real_estate)


def train_price_suggestion(train_dataset, *, n_trials: int = 100, model_path=None, metadata_path=None):
    """Explicit offline AVM training compatibility entry point."""
    return train_price_model(
        train_dataset,
        seed=seed,
        n_trials=n_trials,
        model_path=model_path,
        metadata_path=metadata_path,
    )


def luxury_prediction(real_estate) -> dict:
    from xgboost import XGBRegressor

    with open(PARAM_LOG_PATH, "r") as f:
        for line in f:
            if "LUXURY" in line:
                params= json.load(line)
                if line.startswith("END"):
                    break
                
            model= XGBRegressor(objective="reg:squarederror", tree_method="hist",
                                    enable_categorical=True, random_state=seed,
                                    **params,)
            
            prediction= model.predict(real_estate.model_dump())
    
    return prediction


def analyze_tendency(tendent, percentile, time_span, *, allow_legacy_training: bool = False):
    """Run the legacy tendency routine only when explicitly authorized.

    Its original fallback calls the optimizer when saved parameters are not
    present.  That is training and must never happen on a normal HTTP
    forecasting request.  The API therefore uses the default inference-only
    mode, which makes the missing persisted time-series artifact explicit.
    Offline callers that deliberately need the legacy experimental routine
    must opt in with ``allow_legacy_training=True``.
    """
    if not allow_legacy_training:
        raise ForecastArtifactMissingError(
            "No persisted time-series forecast artifact is available. "
            "The legacy optimizer may only run in an explicit offline workflow."
        )
    return _legacy_analyze_tendency(tendent, percentile, time_span)


def train_tendency_legacy(train_dataset, percentile, time_span):
    """Explicit offline compatibility entry point for legacy optimization."""
    from train.xg_learn import run_optimize_time_series_logPrice_Percentile

    return run_optimize_time_series_logPrice_Percentile(train_dataset, percentile, time_span)


def _legacy_analyze_tendency(tendent, percentile, time_span):
    from xgboost import XGBRegressor
    from train.xg_learn import run_optimize_time_series_logPrice_Percentile

    
    with open(PARAM_LOG_PATH, "r") as f:
        for line in f:
            if "PREDICTION" in line:
                if line == f"time_span: {time_span}":
                    while line != "END":
                        params= json.load(line)
    
    if params is None:
        model, params= run_optimize_time_series_logPrice_Percentile(tendent, percentile, time_span)
        
                    
    model= XGBRegressor(objective="reg:quantileerror", quantile_alpha= percentile,
                        enable_categorical=True, random_state=seed,
                        **params,)

    prediction= model.predict(tendent.model_dump())
    
    return prediction



    
    


    
