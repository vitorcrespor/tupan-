from xgboost import XGBRegressor
import optuna
from sklearn.metrics import root_mean_squared_error
import menu.data_type as data
from sklearn.model_selection import train_test_split
import pandas as pd


def run_optimize(X_train, X_valid, y_train, y_valid, seed= 42):
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
    
    model= XGBRegressor(objective="reg:squarederror", tree_method="hist",
                        enable_categorical=True, random_state=seed,
                        **study.best_params,)
    model.fit(X_train, y_train)
    
    return model, study


def price_suggestion(train_dataset):
    
    X= [x.model_dump(exclude= ("suggested_price", "summary", "price")) for x in train_dataset]
    dfX= pd.DataFrame(X)
    y = [x.suggested_price for x in train_dataset]
    
    for col in dfX.select_dtypes(include=["object"]).columns:
        dfX[col]= dfX[col].astype("category") 
    
    X_train, X_valid, y_train, y_valid = train_test_split(dfX, y, test_size=0.4, random_state=42)
    model, study= run_optimize(X_train, X_valid, y_train, y_valid)
    prediction= model.predict(dfX)
    
    return prediction


def market_tendency(train_dataset):
        
    