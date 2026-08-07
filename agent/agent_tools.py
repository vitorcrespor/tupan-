from langchain_core.tools import tool
import googlemaps
import json
import menu.data_type as data
import agent.analytics as analytics


@tool
def price_suggestion(real_estate):
    """Suggests price for property"""
    return analytics.price_suggestion(real_estate)
    
@tool
def negotiation_helper:
    
    
@tool
def market_analysis:
    """Analyzes market tendencies"""
    

@tool
def portfolio_analysis:
    

@tool
def property_analysis:
    


