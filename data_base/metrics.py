import numpy as np
import pandas as pd
import h3
from train.xg_class import tendency_prediction, price_suggestion
from typing import Any

def calculate_location(real_estates, decay_lambda: float = 0.5) -> pd.DataFrame:
    records= []
    for re in real_estates:
        loc= getattr(getattr(re, "four_metric", None), "location", None)
        h3_idx= getattr(loc, "h3_index", None)
        impact= getattr(re, "impact_score", 1.0)
        if h3_idx:
            records.append({"h3_index": h3_idx, "impact_score": impact})

    dfProperties= pd.DataFrame(records)
    if dfProperties.empty:
        return dfProperties

    cell_impact= dfProperties.groupby("h3_index")["impact_score"].sum()
    d1, d2= np.exp(-decay_lambda*1), np.exp(-decay_lambda*2)
    surrounding_scores= {}

    for cell in cell_impact.index:
        r1= [c for c in h3.grid_ring(cell, 1) if c in cell_impact.index]
        r2= [c for c in h3.grid_ring(cell, 2) if c in cell_impact.index]

        imp_r1= cell_impact.loc[r1].sum()*d1 if r1 else 0.0
        imp_r2= cell_impact.loc[r2].sum()*d2 if r2 else 0.0

        surrounding_scores[cell]= float(np.log1p(imp_r1+imp_r2))

    df_weighted= pd.DataFrame(
        list(surrounding_scores.items()), columns=["h3_index", "raw_impact"])
    min_v, max_v= (
        df_weighted["raw_impact"].min(),
        df_weighted["raw_impact"].max(),)

    if max_v> min_v:
        df_weighted["normalized_score"]= (
            5.0*(df_weighted["raw_impact"]-min_v)/(max_v-min_v))
    else:
        df_weighted["normalized_score"]= 0.0

    score_map= df_weighted.set_index("h3_index")["normalized_score"].to_dict()
    
    for re in real_estates:
        loc= getattr(getattr(re, "four_metric", None), "location", None)
        h3_idx= getattr(loc, "h3_index", None)
        if hasattr(re, "four_metric") and re.four_metric and h3_idx:
            re.four_metric.location_= score_map.get(h3_idx, 0.0)

    return dfProperties.merge(df_weighted, on="h3_index", how="left")



def portfolio_analysis_scores(real_estates):
    analysis= [tuple(Any, Any)]
    for real_estate in real_estates:
        analysis.append(tendency_prediction(real_estate), price_suggestion(real_estate))
    
    dfAnalysis= pd.DataFrame(analysis)
    