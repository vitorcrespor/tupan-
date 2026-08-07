from xgboost import XGBRegressor
import os
import json

PARAM_LOG_PATH= os.getenv("PARAM_LOG_PATH")
SEED= os.getenv("SEED")
global seed
seed= int(SEED)

def price_suggestion(real_estate):

    with open(PARAM_LOG_PATH, "r") as f:
        params= json.load(f)
    
    model= XGBRegressor(objective="reg:squarederror", tree_method="hist",
                        enable_categorical=True, random_state=seed,
                        **params,)

    prediction= model.predict(real_estate.model_dump())
    
    return prediction


def analyze_tendency(tendent):
    
    with open(PARAM_LOG_PATH, "r") as f:
        params= json.load(f)
    
    model= XGBRegressor(objective="reg:squarederror", tree_method="hist",
                        enable_categorical=True, random_state=seed,
                        **params,)

    prediction= model.predict(tendent.model_dump())
    
    return prediction

    
    


    