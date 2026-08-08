from langchain_core.tools import tool
import numpy as np
import train.analytics as analytics
from train.xg_class import prediction


@tool
def price_suggestion(real_estate):
    """Suggests price for property"""
    return np.expm1(analytics.price_suggestion(real_estate))
    
@tool
def negotiation_helper:
    
    
@tool
#melhorar os dados: % de certeza, previsão de tempo
def market_analysis:
    """Analyzes market tendencies"""
    

@tool
def portfolio_analysis:
    

@tool
def property_analysis(real_estate):
    return prediction(real_estate), np.expm1(analytics.price_suggestion(real_estate))
    


