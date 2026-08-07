from langchain_core.tools import tool
import numpy as np
import agent.analytics as analytics


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
def property_analysis:
    


