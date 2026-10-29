"""Acceso a los servicios creados en create_app; los tests construyen la app con sus propias rutas."""
from fastapi import Request
from app.services.engines import EngineService
from app.services.results import ResultStore
from app.services.samples import SampleRepository

def get_engines(request:Request)->EngineService:return request.app.state.engines
def get_results(request:Request)->ResultStore:return request.app.state.results
def get_samples(request:Request)->SampleRepository:return request.app.state.samples
