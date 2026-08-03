
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings, VectorStoreIndex, StorageContext, Document
import data_type as data
from llama_index.core.ingestion import IngestionPipeline
import hashlib
import os

vector_db= os.getenv("VECTOR_DB")
Settings.embed_model= OpenAIEmbedding(model="text-embedding-3-small")
VectorStoreIndex.set_storage_context(storage_context=StorageContext.from_defaults
                                     (persist_dir=vector_db))
address_hashes= set()
city_hashes= set()
area_hashes= set()


def get_index():
    storage_context= StorageContext.from_defaults(persist_dir=vector_db)
    if os.path.exists(vector_db):
        return VectorStoreIndex.from_vector_store(storage_context=storage_context)
    else: return VectorStoreIndex([], storage_context=storage_context)

def ingest_real_estate(real_estate):
    address_hash= hashlib.sha256(real_estate.address.encode()).hexdigest()   
    if address_hash in address_hashes:
        print("Address already ingested")
        return
    address_hashes.add(address_hash)
    
    doc= Document(text=real_estate.address, metadata={
                "age": real_estate.age,
                "name": real_estate.name,
                "price": real_estate.price,
                "area": real_estate.area,
                "last_sale_price": real_estate.last_sale_price,
                "last_sale_date": real_estate.last_sale_date,
                "number_of_rooms": real_estate.number_of_rooms,
                "number_of_bathrooms": real_estate.number_of_bathrooms,
                "number_of_parking_spaces": real_estate.number_of_parking_spaces,
                "square_meter_price": real_estate.square_meter_price,
                "average_discount": real_estate.average_discount})
    
    index= get_index()
    index.insert(doc)
    return 
    
def ingest_city(city):
    city_hash= hashlib.sha256(city.name.encode()).hexdigest()    
    if city_hash in city_hashes:
        print("City already ingested")
        return
    city_hashes.add(city_hash)
    
    doc= Document(text=city.name, metadata={
                "population": city.population,
                "area": city.area,
                "average_price": city.average_price,
                "average_rooms": city.average_rooms,
                "average_bathrooms": city.average_bathrooms,
                "average_parking_spaces": city.average_parking_spaces,
                "available_estates": city.available_estates,
                "average_square_meter_price": city.average_square_meter_price,
                "average_discount": city.average_discount,
                "average_dom": city.average_dom})
    
    index= get_index()
    index.insert(doc)
    return 

def ingest_area(area):
    area_hash= hashlib.sha256(area.name.encode()).hexdigest()
    if area_hash in area_hashes:
        print("Area already ingested")
        return
        
    area_hashes.add(area_hash)
    doc= Document(text=area.name, metadata={
                "average_price": area.average_price,
                "average_rooms": area.average_rooms,
                "average_bathrooms": area.average_bathrooms,
                "average_parking_spaces": area.average_parking_spaces,
                "available_estates": area.available_estates,
                "average_square_meter_price": area.average_square_meter_price,
                "average_discount": area.average_discount,
                "average_dom": area.average_dom})
    
    index= get_index()
    index.insert(doc)
    return


def ingest(obj):
    if isinstance(obj, data.real_estate):
        ingest_real_estate(obj)

    elif isinstance(obj, data.city):
        ingest_city(obj)

    elif isinstance(obj, data.area):
        ingest_area(obj)