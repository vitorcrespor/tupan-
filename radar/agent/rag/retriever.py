from llama_index.core import Settings, config
import json

def retriever_database(query: str, where: json):
    results= config.collection.query(
        query_texts=[query],
        n_results=5,
        where=where)
    return results
