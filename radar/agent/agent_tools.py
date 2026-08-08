from langchain_core.tools import tool
import numpy as np
import train.analytics as analytics
from train.xg_class import tendency_prediction
import pandas as pd

@tool
def price_suggestion(real_estate):
    """Suggests price for property"""
    return np.expm1(analytics.price_suggestion(real_estate))
    
@tool
def negotiation_helper(query):
    
    return
    
@tool
def portfolio_analysis(real_estates):
    """Analyzes portfolio"""
    
    return 

def market_analysis(market):
    """Analyzes market"""
    
    return 
        
    
@tool
def property_analysis(real_estate):
    """Analyzes property price tendencies"""
    return tendency_prediction(real_estate), np.expm1(analytics.price_suggestion(real_estate))
    


