class real_estate:
    def __init__(self, name, age, address, price, area, 
                 last_sale_price, last_sale_date, number_of_rooms, 
                 number_of_bathrooms, number_of_parking_spaces, square_meter_price):
        suggested_price: float 
        self.nam: str= name
        self.age: int= age
        self.address: str= address
        self.price: float= price
        self.area: float= area
        
        self.last_sale_price: float= last_sale_price
        self.last_sale_date: str= last_sale_date
        
        self.number_of_rooms: tuple[int, int]= number_of_rooms
        self.number_of_bathrooms: int= number_of_bathrooms
        self.number_of_parking_spaces: int= number_of_parking_spaces
        self.square_meter_price: float= square_meter_price


class city:
    def __init__(self, name, population, area, 
                 average_price, average_area, average_discount,
                 average_rooms, average_bathrooms, average_dom, 
                 average_parking_spaces, available_estates, average_square_meter_price):
        self.average_dom: float= average_dom
        self.average_discount: float= average_discount
        self.name: str= name
        self.population: int= population
        self.area: float= area
        
        self.average_price: float= average_price
        self.average_area: float= average_area
        
        self.average_rooms: float= average_rooms
        self.average_bathrooms: float= average_bathrooms
        self.average_parking_spaces: float= average_parking_spaces
        
        self.available_estates: list= available_estates
        self.average_square_meter_price: float= average_square_meter_price
        
        
class area:
    def __init__(self, name, average_price, 
                 average_rooms, average_bathrooms, 
                 average_parking_spaces, available_estates, 
                 average_square_meter_price, average_discount, average_dom):
        self.average_dom: float= average_dom
        self.average_discount: float= average_discount
        self.name: str= name
        
        self.average_price: float= average_price
        
        self.average_rooms: float= average_rooms
        self.average_bathrooms: float= average_bathrooms
        self.average_parking_spaces: float= average_parking_spaces
        
        self.available_estates: list= available_estates
        self.average_square_meter_price: float= average_square_meter_price