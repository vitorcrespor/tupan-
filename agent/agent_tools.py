from langchain_core.tools import tool
import googlemaps
import json
import requests
import pandas as pd

@tool
def get_distance_matrix(origins: list[str], destinations: list[str],
                        mode: str):
    """Distance matrix"""
    return json.json_dump(googlemaps.distance_matrix(origins=origins, 
                                      destinations=destinations, 
                                      mode=mode))

@tool
def check_address(address: str, area: str):
    """Check address valid"""
    return json.json_dump(googlemaps.addressvalidation(addressLines=address, 
                                        locality=area))

@tool 
def nearest_road(adresses: list[str]):
    """Get nearest road up 100 addresses"""
    return json.json_dump(googlemaps.nearest_roads(adresses= adresses))

@tool
def locations_nearby(latitude_and_longitude: str, 
                     search_radius: int, 
                     kind: str):
        """Get type of locations near"""
        return json.json_dump(googlemaps.places_nearby(location= latitude_and_longitude, 
                                        radius= search_radius, 
                                        keyword= kind,))
    
@tool
def latitude_and_longitude(address: str):
    """Get latitude and longitude"""
    return json.json_dump(googlemaps.geocode(address= address))

@tool
def ipca_brasil(periodo: int, ):
    url= f"https://servicodados.ibge.gov.br/api/v3/agregados/7060/periodos/-{periodo}/variaveis/63?localidades=N1[all]"
    data= requests.get(url).json()
    values = data[0]['resultados'][0]['series'][0]['serie']

    df= pd.DataFrame(list(values.items()), columns=["periodo", "ipca"])
    df["ipca"]= pd.to_numeric(df["ipca"])
    return json.json_dump(df)

@tool 
def ipca_sao_paulo(periodo: int):
    url= f"https://servicodados.ibge.gov.br/api/v3/agregados/6586/periodos/202601|202602|202603|202604|202605|202606/variaveis/93279328|9329|9330|9331|9332|9333|9334|9335?localidades=N3[35]"