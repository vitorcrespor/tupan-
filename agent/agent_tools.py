from langchain_core.tools import tool

@tool
def get_pipeline(query: str):
    """Access the pipeline data, being it for a specific pipeline or for all pipelines.
   Use it to aquire knowledge of the current state of sales"""
    return retrieve_get_pipeline(query)

@tool
def get_real_state_db(query: str):
    """Access the real-time database for real state open to offer."""  
    return retrieve_get_real_state_db(query)

@tool
def get_analytics(query: str):
    """Access the analytics data."""
    return retrieve_get_analytics(query)

@tool
def get_client_data(query: str):
    """Access the statistics data."""
    return retrieve_get_client_data(query)