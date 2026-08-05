class real_estate:
    def __init__(self):
        #location h3
        self.suggested_price: float= None
        self.summary: str= None #after add image influence
        self.age: int= None
        self.address: str= None
        self.price: float= None
        self.area: float= None
        self.city: str= None
        
        self.last_sale_price: float= None
        self.last_sale_date: str= None
        
        self.number_of_rooms: int= None
        self.number_of_bathrooms: int= None
        self.number_of_parking_spaces: int= None
        self.square_meter_price: float= None


class city:
    def __init__(self):
        self.average_dom: float= None
        self.average_discount: float= None
        self.name: str= None
        self.population: int= None
        self.area: float= None
        
        self.average_price: float= None
        self.average_area: float= None
        
        self.average_rooms: float= None
        self.average_bathrooms: float= None
        self.average_parking_spaces: float= None
        
        self.available_estates: list= None
        self.average_square_meter_price: float= None
        
        
class area:
    def __init__(self):
        self.average_dom: float= None
        self.average_discount: float= None
        self.name: str= None
        
        self.average_price: float= None
        
        self.average_rooms: float= None
        self.average_bathrooms: float= None
        self.average_parking_spaces: float= None
        
        self.available_estates: list= None
        self.average_square_meter_price: float= None