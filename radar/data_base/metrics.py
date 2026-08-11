import numpy as np
import pandas as pd
import h3
import datetime 
import json
from scipy.special import expit, tanh
from collections import defaultdict

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



def portfolio_analysis_scores(portfolio):
    analysis= {}
    stag_dom, dom, prices, first_prices, h3_indexes, exclusiveness= [], [], [], [], [], []
    four_metrics, stag_dom_prices, listed_prices_= [], [], []
    
    sold_dom, sold_prices, sold_first_prices, sold_h3_indexes, sold_exclusiveness= [], [], [], [], [], []
    sold_four_metrics, sold_listed_prices_, sold_dates= [], [], [], []
    
    global_stag_dom, global_dom, global_prices, global_first_prices, global_h3_indexes, global_exclusiveness= [], [], [], [], [], []
    global_four_metrics, global_stag_dom_prices, global_listed_prices_= [], [], []
    
    for real_estate in portfolio.real_estates:
        dom.append(real_estate.dom)
        if dom> 90:
            stag_dom_prices.append(real_estate.re_price_metrics.price)
            stag_dom.append(real_estate.dom)
            
        prices.append(real_estate.re_price_metrics.price)
        
        if portfolio.real_estates.listed_prices.len()> 1:
            first_prices.append(real_estate.re_price_metrics.listed_prices[0])
        
        h3_indexes.append(real_estate.four_metric.location.h3_index)
        exclusiveness.append(real_estate.exclusive)
        four_metrics.append(real_estate.four_metric)
        listed_prices_.append(real_estate.re_price_metrics.listed_prices)

    for sold_estate in portfolio.sold_estates:
        sold_dom.append(sold_estate.dom)
        sold_prices.append(sold_estate.re_price_metrics.sold_price)
        sold_dates.append(sold_estate.sale_date)
        
        if sold_estate.sold_estates.listed_prices.len()> 1:
            sold_first_prices.append(sold_estate.sold_estates.listed_prices[0])
        
        sold_h3_indexes.append(sold_estate.four_metric.location.h3_index)
        sold_exclusiveness.append(sold_estate.exclusive)
        sold_four_metrics.append(sold_estate.four_metric)
        sold_listed_prices_.append(sold_estate.re_price_metrics.listed_prices)
        
    for estate in portfolio.estates:
        global_dom.append(estate.dom)
        if dom> 90:
            global_stag_dom_prices.append(estate.re_price_metrics.price)
            global_stag_dom.append(estate.dom)
            
        global_prices.append(estate.re_price_metrics.price)
        
        if estate.real_estates.listed_prices.len()> 1:
            global_first_prices.append(estate.real_estates.listed_prices[0])
        
        global_h3_indexes.append(estate.four_metric.location.h3_index)
        global_exclusiveness.append(estate.exclusive)
        global_four_metrics.append(estate.four_metric)
        global_listed_prices_.append(estate.re_price_metrics.listed_prices)
    
    lsp= []
    for i in range(len(sold_prices)):
        lsp.append(sold_prices[i]/sold_first_prices[i])
    lsp_= np.mean(lsp)
    analysis["lsp"]= lsp_
    
    mon_sales: int
    for estate in portfolio.sold_estates:
        if datetime.today() - portfolio.sold_estates.sold_date < datetime.timedelta(days=90):
            mon_sales += 1
        
    act_list= len(portfolio.real_estates)/mon_sales
    analysis["act_list"]= act_list
    
    analysis["dom"]= global_dom
    
    stag_cr= len(stag_dom)/len(global_dom)
    analysis["stag_cr"]= stag_cr
    
    exclusive_sales= 0
    for x in sold_exclusiveness:
        if x:
            exclusive_sales += 1
    exclusive_retention= len(exclusive_sales)/len(global_dom)
    analysis["exclusive_retention"]= exclusive_retention
    
    commissions= []
    for commission in portfolio.sold_estates.practiced_commission:
        commissions.append(commission)
    
    comm_mean= np.mean(commissions)
    commission_retention= comm_mean/portfolio.tgt_comission
    analysis["commission_retention"]= commission_retention
    
    income= sum(sold_prices)
    area= sum(portfolio.estates.real_estate_metrics.square_metrage)
    gci_per_sqm= income/area
    analysis["gci_per_sqm"]= gci_per_sqm
    
    #refresh rate
    analysis["hhi"]= calculate_portfolio_hhi(portfolio.real_estates)
    analysis["clustering_coefficient"]= calculate_h3_clustering_coefficient(portfolio.real_estates)
    
    analysis_= json.dump(analysis)
    return analysis_

import h3


def _get_path(obj, path: str):
    for p in (path or "").split("."):
        obj = getattr(obj, p, None) if obj else None
    return obj


def calculate_portfolio_hhi(
    real_estates, segment_attr: str = "kind", value_attr: str = None
) -> float:
    data = {}
    for re in real_estates:
        seg = _get_path(re, segment_attr)
        if seg is None:
            continue
        val = float(_get_path(re, value_attr) or 1.0) if value_attr else 1.0
        data[str(seg)] = data.get(str(seg), 0.0) + val

    tot = sum(data.values())
    return (
        float(sum(((v / tot) * 100) ** 2 for v in data.values()))
        if tot > 0
        else 0.0
    )


def calculate_h3_clustering_coefficient(real_estates) -> float:
    cells = {
        _get_path(re, "four_metric.location.h3_index")
        or getattr(re, "h3_index", None)
        for re in real_estates
    } - {None}

    if len(cells) <= 1:
        return 0.0

    contacts = sum(len(set(h3.grid_ring(c, 1)) & cells) for c in cells)
    return float(contacts / (6 * len(cells)))


def calculate_market_heat(real_estates, portfolio, decay_lambda: float = 0.5):
    sales_t2= 0
    for sold_estate in reversed(portfolio.sold_estates):
        days_ago= (datetime.today()-sold_estate.sale_date).days
        if days_ago <= 60:
            sales_t2+= 1
        else:
            break
    
    sales_t12_t14 = 0
    for sold_estate in reversed(portfolio.sold_estates):
        days_ago= (datetime.today()-sold_estate.sale_date).days
        if days_ago > 425:
            break 
        if 365 <= days_ago <= 425:
            sales_t12_t14 += 1
            
    denom= sales_t12_t14 if sales_t12_t14 > 0 else 1.0
    gamma= (sales_t2 - sales_t12_t14) / denom
    growth_mult= 1.0 + np.tanh(gamma)
    
    G= np.array(expit([re.predictions.expected_growth for re in real_estates]))
    G= growth_mult*G
    
    records= []
    re_by_cell= defaultdict(list)
    for re in real_estates:
        cell_id= re.location.h3_index
        if cell_id:
            re_by_cell[cell_id].append(re)
            loc_score= getattr(getattr(re, "four_metric", None), "location_", 1.0)
            raw_growth= getattr(getattr(re, "predictions", None),
                        "expected_normalized_growth", 0.0)
            records.append({"h3_index": cell_id, "location_score": loc_score,
                            "growth": raw_growth})

    dfProperties= pd.DataFrame(records)
    if dfProperties.empty:
        return dfProperties

    cell_score= dfProperties.groupby("h3_index")["location_score"].sum()
    d1, d2= np.exp(-decay_lambda*1), np.exp(-decay_lambda*2)
    scores= {}
        
    for cell in cell_score.index:
        r1= [c for c in h3.grid_ring(cell, 1) if c in cell_score.index]
        r2= [c for c in h3.grid_ring(cell, 2) if c in cell_score.index]

        imp_r1= cell_score.loc[r1].sum()*d1 if r1 else 0.0
        imp_r2= cell_score.loc[r2].sum()*d2 if r2 else 0.0

        l= float(np.log1p(imp_r1+imp_r2))
        scores[cell]= l
        
        for re in re_by_cell.get(cell, []):
            g= expit(re.predictions.expected_growth)
            lev_score= l*g*growth_mult
            re.leverage= lev_score

    aligned_cells= cell_score.index
    L_vec= expit(np.array([scores[c] for c in aligned_cells]))
    G_vec= G.reindex(aligned_cells)
    market_heat= np.dot(L_vec, G_vec)

    return market_heat, pd.DataFrame({
        "h3_index": aligned_cells,
        "spatial_heat_L": L_vec,
        "momentum_growth_G": G_vec,
        "cell_market_heat": L_vec * G_vec,
    })
    
    
