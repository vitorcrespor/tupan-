from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings, VectorStoreIndex
import data_type as data
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core import Document
import hashlib

Settings.embed_model= OpenAIEmbedding(model="text-embedding-3-small")
address_hashes= set()
city_hashes= set()
area_hashes= set()

def ingest(real_estate):
    address_hash= hashlib.sha256(real_estate.address.encode()).hexdigest()   
    if address_hash in address_hashes:
        print("Address already ingested")
        return
    address_hashes.add(address_hash)
    
    doc= Document(text=real_estate.address, metadata={
                "age": real_estate.age,
                "address": real_estate.name,
                "price": real_estate.price,
                "area": real_estate.area,
                "last_sale_price": real_estate.last_sale_price,
                "last_sale_date": real_estate.last_sale_date,
                "number_of_rooms": real_estate.number_of_rooms,
                "number_of_bathrooms": real_estate.number_of_bathrooms,
                "number_of_parking_spaces": real_estate.number_of_parking_spaces,
                "square_meter_price": real_estate.square_meter_price,
                "average_discount": real_estate.average_discount})
    
    index= VectorStoreIndex.from_documents(documents=[doc])
    return 
    
def ingest(city_panorama):
    city_hash= hashlib.sha256(city_panorama.name.encode()).hexdigest()    
    if city_hash in city_hashes:
        print("City already ingested")
        return
    city_hashes.add(city_hash)
    
    doc= Document(text=city_panorama.name, metadata={
                "population": city_panorama.population,
                "area": city_panorama.area,
                "average_price": city_panorama.average_price,
                "average_rooms": city_panorama.average_rooms,
                "average_bathrooms": city_panorama.average_bathrooms,
                "average_parking_spaces": city_panorama.average_parking_spaces,
                "available_estates": city_panorama.available_estates,
                "average_square_meter_price": city_panorama.average_square_meter_price,
                "average_discount": city_panorama.average_discount,
                "average_dom": city_panorama.average_dom})
    
    index= VectorStoreIndex.from_documents(documents=[doc])
    return 

def ingest(area_panorama):
    area_hash= hashlib.sha256(area_panorama.name.encode()).hexdigest()
    if area_hash in area_hashes:
        print("Area already ingested")
        return
        
    area_hashes.add(area_hash)
    doc= Document(text=area_panorama.name, metadata={
                "average_price": area_panorama.average_price,
                "average_rooms": area_panorama.average_rooms,
                "average_bathrooms": area_panorama.average_bathrooms,
                "average_parking_spaces": area_panorama.average_parking_spaces,
                "available_estates": area_panorama.available_estates,
                "average_square_meter_price": area_panorama.average_square_meter_price,
                "average_discount": area_panorama.average_discount,
                "average_dom": area_panorama.average_dom})
    
    index= VectorStoreIndex.from_documents(documents=[doc])
    return
