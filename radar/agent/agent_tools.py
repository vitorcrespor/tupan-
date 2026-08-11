from langchain_core.tools import tool
import numpy as np
import train.analytics as analytics
from train.xg_class import tendency_prediction
from radar.data_base.metrics import portfolio_analysis_scores, calculate_market_heat

@tool
def price_suggestion(real_estate):
    """Suggests price for property"""
    return np.expm1(analytics.price_suggestion(real_estate))
    
@tool
def negotiation_helper(query):
    
    return
    
    
@tool
def portfolio_analysis(portfolio):
    """Analyzes portfolio"""
    return portfolio_analysis_scores(portfolio)


def market_analysis(portfolio):
    """Analyzes market"""
    return calculate_market_heat(portfolio.real_estates, portfolio)
        
    
@tool
def property_analysis(real_estate):
    """Analyzes property price tendencies"""
    return tendency_prediction(real_estate), np.expm1(analytics.price_suggestion(real_estate))
    


