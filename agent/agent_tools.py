from langchain_core.tools import tool
import googlemaps
import json
import menu.data_type as data




@tool
async def get_distance_matrix(origins: list[str], destinations: list[str],
                        mode: str):
    """Distance matrix"""
    return await json.json_dump(googlemaps.distance_matrix(origins=origins, 
                                      destinations=destinations, 
                                      mode=mode))

@tool
async def check_address(address: str, area: str):
    """Check address valid"""
    return await json.json_dump(googlemaps.addressvalidation(addressLines=address, 
                                        locality=area))

@tool 
async def nearest_road(adresses: list[str]):
    """Get nearest road up 100 addresses"""
    return await json.json_dump(googlemaps.nearest_roads(adresses= adresses))

@tool
async def locations_nearby(latitude_and_longitude: str, 
                     search_radius: int, 
                     kind: str):
        """Get type of locations near"""
        return await json.json_dump(googlemaps.places_nearby(location= latitude_and_longitude, 
                                        radius= search_radius, 
                                        keyword= kind,))
    
@tool
async def latitude_and_longitude(address: str):
    """Get latitude and longitude"""
    return await json.json_dump(googlemaps.geocode(address= address))

@tool
def price_suggestion:
    
    
@tool
def negotiation_helper:
    
    
@tool
def market_analysis:
    

@tool
def portfolio_analysis:
    

@tool
def property_analysis:
    


