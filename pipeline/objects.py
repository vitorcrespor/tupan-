from abc import abstractmethod

class pipeline_stage:
    params= {'stage_name': str, 
             'previous_stage': str|None}
    
    def __init__(self, params: dict):
        self.params= params
        
    @abstractmethod
    def run(self, data: dict, observations: str):

class to_be_prospected(pipeline_stage):
    data= {'area': str, 'cargo': str}
    def run(self, data, observations: str):

class prospected(pipeline_stage):
    
class cold_leads(pipeline_stage):
    
class interested_leads(pipeline_stage):
    
class transit_leads(pipeline_stage):

class bin_leads(pipeline_stage):
    
class lost(bin_leads):
    
class sold(bin_leads):
    
    