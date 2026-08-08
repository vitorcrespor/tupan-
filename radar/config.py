from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings
import chromadb
import os

Settings.llm= OpenAI(
    model="gpt-4o-mini",
    system_prompt="Real estate AI. Structured valuation. Concise. Data-driven.")

Settings.embed_model= OpenAIEmbedding(
    model="text-embedding-3-small")

client= chromadb.PersistentClient(path=os.getenv("VECTOR_DB"))
collection= client.get_collection(name="properties")