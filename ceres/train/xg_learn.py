from xgboost import XGBRegressor
import optuna
from sklearn.metrics import root_mean_squared_error, pinball_loss
from sklearn.model_selection import train_test_split, TimeSeriesSplit
import pandas as pd
import numpy as np
import os
import json


#testar tecnincas de normalizacao!!!!!!!!!!!!!!!!
TS_PARAM_LOG_PATH= os.getenv("TS_PARAM_LOG_PATH")
OS_PARAM_LOG_PATH= os.getenv("OS_PARAM_LOG_PATH")

SEED= os.getenv("SEED", "42")
global seed
seed= int(SEED)


def run_optimize_time_series_logPrice_Percentile(train_dataset, percentile, time_span):
    with open(TS_PARAM_LOG_PATH, "r") as f:
        for line in f:
            if "PREDICTION" in line:
                if line == f"time_span: {time_span}":
                    return
        
    X= train_dataset.model_dump()
    dfX= pd.DataFrame(X)
    y= [x.suggested_price for x in train_dataset]
    y= pd.Series(y).shift(-time_span)
    
    dfX= dfX.loc[y.notna()].reset_index(drop= True)
    y= y.loc[y.notna()].reset_index(drop= True)
    
    for col in dfX.select_dtypes(include=["object"]).columns:
        dfX[col]= dfX[col].astype("category") 
    
    ts= TimeSeriesSplit()
    
    def objective(trial):
        params= {"objective": "reg:quantileerror", "quantile_alpha": percentile,
                "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.1, 0.8),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
                "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
                "random_state": seed,
                "tree_method": "hist",
                "enable_categorical": True}
        
        score= []
        for train, valid in ts.split(dfX):
            X_train, X_valid= dfX.iloc[train], dfX.iloc[valid]
            y_train, y_valid= y.iloc[train], y.iloc[valid]
            y_train_log= np.log(y_train)
            model= XGBRegressor(**params)
            model.fit(X_train, y_train_log)
            
            log_prediction= model.predict(X_valid)
            loss= pinball_loss(y_valid, log_prediction, alpha= percentile)
            
            score.append(loss)
        return sum(score)/len(score)
        
    sampler= optuna.samplers.TPESampler(seed= seed)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study= optuna.create_study(direction="minimize", sampler= sampler)
    study.optimize(objective, n_trials=100)
    
    best_model= XGBRegressor(objective="reg:quantileerror", quantile_alpha= percentile, 
                            tree_method="hist", enable_categorical=True, random_state=seed,
                            **study.best_params,)
    best_model.fit(dfX, y)
    
    log_data = {"PREDICTION": None, "time_span": time_span,
                "best_params": study.best_params.copy()}

    with open(TS_PARAM_LOG_PATH, "w") as f:
        json.dump(log_data, f, indent=4)
        f.write("\nEND\n")
    
    return best_model,study



def run_optimize_price(train_dataset, seed):
    """Legacy training entry point retained as an explicit persisted AVM run.

    It delegates to the versioned artifact trainer instead of leaving only an
    optimizer-parameter log, which was not sufficient for runtime inference.
    """
    from train.avm import load_price_model, train_price_model

    summary = train_price_model(train_dataset, seed=seed)
    model, _ = load_price_model()
    return model, summary


def run_optimize_luxury(train_dataset, seed):
    with open(OS_PARAM_LOG_PATH, "r") as f:
        for line in f:
            if "LUXURY" in line:
                return
                
    X= [x.model_dump(exclude= ("luxury",)) for x in train_dataset]
    dfX= pd.DataFrame(X)
    y= [x.suggested_price for x in train_dataset]
    
    for col in dfX.select_dtypes(include=["object"]).columns:
        dfX[col]= dfX[col].astype("category") 
    
    X_train, X_valid, y_train, y_valid = train_test_split(dfX, y, test_size=0.4, random_state=42)
    def objective(trial):
        params= {"n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.1, 0.8),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
                "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
                "random_state": seed,
                "tree_method": "hist",
                "enable_categorical": True}

        model= XGBRegressor(**params)
        model.fit(X_train, y_train)
        
        prediction= model.predict(X_valid)
        return root_mean_squared_error(y_valid, prediction)
    
    sampler= optuna.samplers.TPESampler(seed= seed)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study= optuna.create_study(direction="minimize", sampler= sampler)
    study.optimize(objective, n_trials=100)
    
    best_model= XGBRegressor(objective="reg:squarederror", tree_method="hist",
                        enable_categorical=True, random_state=seed,
                        **study.best_params,)
    best_model.fit(X_train, y_train)
    
    log_data = {"LUXURY": None, "best_params": study.best_params.copy()}

    with open(OS_PARAM_LOG_PATH, "w") as f:
        json.dump(log_data, f, indent=4)
        f.write("\nEND\n")
        
    return best_model, study

def run_optimize_price_combination(train_dataset, seed):
    with open(OS_PARAM_LOG_PATH, "r") as f:
        for line in f:
            if "PRICE_COMBINATION" in line:
                return
            
    avm_prices= [x.avm_price for x in train_dataset]
    neighboring_prices= [x.neighboring_price for x in train_dataset]
    similarity_prices= [x.similarity_price for x in train_dataset]


    y= [x.price for x in train_dataset]
    X_train, X_valid, y_train, y_valid= train_test_split(
        list(zip(avm_prices, similarity_prices, neighboring_prices)), y,
        test_size=0.4, random_state=42)
    X_valid= np.array(X_valid, dtype=float)

    def objective(trial):
        avm_weight= trial.suggest_float("avm_weight", 0.0, 1.0)
        similarity_weight= trial.suggest_float("similarity_weight", 0.0, 1.0 - avm_weight)
        neighboring_weight= (1.0- avm_weight- similarity_weight)
        prediction= (
            avm_weight * X_valid[:, 0]
            + similarity_weight * X_valid[:, 1]
            + neighboring_weight * X_valid[:, 2])

        return root_mean_squared_error(y_valid,prediction)
    
    sampler= optuna.samplers.TPESampler(seed= seed)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study= optuna.create_study(direction="minimize", sampler= sampler)

    study.optimize(objective, n_trials=100)
    best_weights= study.best_params.copy()
    best_weights["neighboring_weight"]= (1.0- best_weights["avm_weight"]
                                    - best_weights["similarity_weight"])
    
    log_data = {"PRICE_COMBINATION": None, "best_weights": best_weights.copy()}

    with open(OS_PARAM_LOG_PATH, "w") as f:
        json.dump(log_data, f, indent=4)
        f.write("\nEND\n")
        
    return best_weights, study
