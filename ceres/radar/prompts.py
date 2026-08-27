SYSTEM_PROMPT = """You are Ceres, a real-estate market intelligence assistant.
Use the available domain tools when a response requires deterministic property,
portfolio, valuation, or market analysis. Do not invent numerical evidence.
State when the configured data or model is unavailable."""


def build_summary_prompt(input_data):
    attrs= {k: v for k, v in vars(input_data).items() if v is not None}
    return {
        "task": "summarize_property",
        "input": attrs}
                        
def normalize_address(address): 
    return {
        "task": "normalize address to street/number/city",
        "input": address}

def build_where(filters: dict):
    conditions= []
    for attr, value in filters.items():
        if isinstance(value, tuple):
            conditions.append({
                attr: {
                    "$gte": value[0],
                    "$lte": value[1]
                }})

        elif isinstance(value, str):
            conditions.append({
                attr: {
                    "$eq": value
                }})

    return {"$and": conditions}
