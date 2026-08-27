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

# A new local installation has a valid but empty persistent directory.  Create
# the existing properties collection on first use so read-only API calls can
# return an empty result instead of treating that state as an outage.  Do not
# silently fall back to Chroma's implicit working-directory store: that makes
# data appear to disappear between the API and maintenance scripts.
VECTOR_DB = (os.getenv("VECTOR_DB") or "").strip()
if not VECTOR_DB:
    raise RuntimeError("VECTOR_DB must be configured for the persistent property store.")

client= chromadb.PersistentClient(path=VECTOR_DB)
collection= client.get_or_create_collection(name="properties")
