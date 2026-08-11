from xgboost import XGBRegressor
import os
import json
import train.xg_class as xg
from train.xg_learn import run_optimize_time_series_logPrice_Percentile

PARAM_LOG_PATH= os.getenv("PARAM_LOG_PATH")
SEED= os.getenv("SEED")
global seed
seed= int(SEED)

def price_suggestion(real_estate) -> dict:

    with open(PARAM_LOG_PATH, "r") as f:
        for line in f:
            if "SUGGESTION" in line:
                params= json.load(line)
                if line.startswith("END"):
                    break
                
            model= XGBRegressor(objective="reg:squarederror", tree_method="hist",
                                    enable_categorical=True, random_state=seed,
                                    **params,)
            
            prediction= model.predict(real_estate.model_dump())
    
    return prediction


def luxury_prediction(real_estate) -> dict:
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


def analyze_tendency(tendent, percentile, time_span):
    
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

    
    


    