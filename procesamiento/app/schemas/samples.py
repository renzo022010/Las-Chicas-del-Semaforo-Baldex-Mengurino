"""En desarrollo: trazabilidad de muestras y diluciones para el calculo de UFC. La PWA aun no lo usa."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel,Field,model_validator

class Plate(BaseModel):
    count:int|None=Field(default=None,ge=0,le=100000)
    analysis_id:str|None=Field(default=None,pattern='^[0-9a-f]{32}$')

class Dilution(BaseModel):
    exponent:int=Field(ge=0,le=12)  # 10^-exponent
    volume_ml:float=Field(gt=0,le=10,allow_inf_nan=False)
    plate_a:Plate=Plate()
    plate_b:Plate=Plate()

class UfcInput(BaseModel):
    dilutions:list[Dilution]=Field(default_factory=list,max_length=12)
    unit:Literal['mL','g']='mL'
    count_min:int=Field(default=30,ge=0,le=10000)
    count_max:int=Field(default=300,ge=1,le=100000)
    @model_validator(mode='after')
    def check_range(self):
        if self.count_min>=self.count_max:raise ValueError('El rango contable minimo debe ser menor que el maximo')
        return self

class SampleIn(UfcInput):
    analyzed_at:datetime
    sample_type:str=Field(min_length=1,max_length=40)
    responsible:str=Field(min_length=1,max_length=80)
    origin:str=Field(default='',max_length=120)  # cultivo, parcela o procedencia
    notes:str=Field(default='',max_length=2000)
