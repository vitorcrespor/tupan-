from dotenv import load_dotenv
import os
import chromadb

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.extractors import TitleExtractor, QuestionsAnsweredExtractor
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

import hashlib
from pathlib import Path


load_dotenv()
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR")
DOC_PATH = os.getenv("DOC_PATH")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")

_retriever= None
_embed_model= None

def get_vector_hash(collection) -> set[str]:
    data= collection.get(include=["metadatas", []])
    data_hashes= set()
    
    for metadata in data.get("metadatas"):
        if metadata and metadata.get("file_hash"):
            data_hashes.add(metadata.get("file_hash"))
    return data_hashes

def file_hash(path: str) -> str:
    h= hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)

    return h.hexdigest()

def get_embed_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model= HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)

    return _embed_model


def get_vector_store():
    chroma_client= chromadb.PersistentClient(path=VECTOR_DB_DIR)
    collection= chroma_client.get_or_create_collection(name="vector_db")
    vector_store= ChromaVectorStore(chroma_collection=collection)

    return vector_store, collection

def new_documents(collection) -> list:
    new_documents= []
    old_hashes= get_vector_hash(collection)
    for file in Path(DOC_PATH).rglob("*"):
        if file.is_file():
            resolved_path= str(file.resolve())
            current_hash= file_hash(resolved_path)
            if current_hash not in old_hashes:
                docs= SimpleDirectoryReader(input_files=[resolved_path]).load_data()
                for doc in docs:
                    doc.metadata["source_path"]= resolved_path
                    doc.metadata["file_hash"]= current_hash
                new_documents.extend([doc])
    return new_documents

def ingest_documents(vector_store, documents):
    if DOC_PATH is None:
        raise ValueError("DOC_PATH is not set in .env")

    llm= Ollama(model="llama3.2:3b")
    embed_model= get_embed_model()
    Settings.llm= llm
    Settings.embed_model= embed_model
    
    if not documents:
        documents= SimpleDirectoryReader(input_dir=DOC_PATH).load_data()

    for document in documents:
        document.text_template= ("metadata:\n{metadata}\n----\ncontent:\n{content}")
        if "page_label" not in document.excluded_embed_metadata_keys:
            document.excluded_embed_metadata_keys.append("page_label")

    text_splitter= SentenceSplitter(chunk_size=1024,chunk_overlap=128)
    title_extractor= TitleExtractor(llm=llm,nodes=3)
    qa_extractor= QuestionsAnsweredExtractor(llm=llm,questions=3)
    pipeline= IngestionPipeline(transformations=[text_splitter,
                                                title_extractor,qa_extractor])
    nodes= pipeline.run(documents=documents,show_progress=True)
    storage_context= StorageContext.from_defaults(vector_store=vector_store)
    index= VectorStoreIndex(nodes,
                             storage_context=storage_context,
                             embed_model=embed_model)

    return index


def get_retriever(k: int):
    global _retriever
    if _retriever is not None:
        return _retriever

    embed_model= get_embed_model()
    llm= Ollama(model="llama3.2:3b")
    Settings.embed_model= embed_model
    Settings.llm= llm
    vector_store, collection= get_vector_store()
    k= min(k, collection.count())

    ingest_docs= new_documents(collection)
    if ingest_docs:
        print("Ingesting documents...")
        index= ingest_documents(vector_store, ingest_docs)
    else:
        print("Vector DB search...")
        index= VectorStoreIndex.from_vector_store(vector_store=vector_store,
                                                   embed_model=embed_model)
    
    retriever= index.as_retriever(similarity_top_k=k)

    return retriever


def retrieve_from_documents(query: str, documents: list, k: int):
    if not documents:  return []
    
    embed_model= get_embed_model()
    llm= Ollama(model="llama3.2:3b")
    Settings.embed_model= embed_model
    Settings.llm= llm
    
    index= VectorStoreIndex.from_documents(documents=documents, 
                                           show_progress=True)
    retriever= index.as_retriever(similarity_top_k=k)
    nodes= retriever.retrieve(query)

    return nodes
    

    

    