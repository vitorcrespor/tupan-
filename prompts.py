def build_summary_prompt(input_data):
    attrs= {k: v for k, v in vars(input_data).items() if v is not None}
    return {
        "task": "summarize_property",
        "input": attrs}
                        
def normalize_address(address): 
    return {
        "task": "normalize address to street/number/city",
        "input": address}

def build_where(filters: dict[str, tuple[float, float]]):
    return {
        "$and": [
            {
                attr: {
                    "$gte": interval[0],
                    "$lte": interval[1]
                }
            }for attr, interval in filters.items()]}