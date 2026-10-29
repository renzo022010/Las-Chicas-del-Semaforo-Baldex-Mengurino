"""Revision humana de un analisis: centros en pixeles de la foto original."""
from pydantic import BaseModel,Field

class Point(BaseModel):
    x:float=Field(ge=0,allow_inf_nan=False)
    y:float=Field(ge=0,allow_inf_nan=False)

class Review(BaseModel):
    centers:list[Point]=Field(max_length=10000)
    note:str=Field(default='',max_length=2000)
