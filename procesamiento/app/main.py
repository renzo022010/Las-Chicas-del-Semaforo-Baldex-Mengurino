"""Construccion de la API: servicios en app.state y un router por controlador."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from contador_hibrido import HybridCounter
from app.config import OUTPUT,SAMPLES_DB,hybrid_requested
from app.controllers import analysis,health,results,samples
from app.services.engines import EngineService
from app.services.results import ResultStore
from app.services.samples import SampleRepository

TAGS=[{'name':'Estado'},{'name':'Analisis'},{'name':'Resultados'},
      {'name':'Muestras (en desarrollo)','description':'Trazabilidad, diluciones y UFC. Aun no validado ni usado por la PWA.'}]

def create_app(output=OUTPUT,samples_db=SAMPLES_DB,hybrid_factory=HybridCounter,use_hybrid=None):
    engines=EngineService(hybrid_factory,hybrid_requested() if use_hybrid is None else use_hybrid)

    @asynccontextmanager
    async def lifespan(app):
        await engines.start()
        yield
        engines.stop()

    app=FastAPI(title='Conteo de colonias - MVP',version='0.4.0',lifespan=lifespan,openapi_tags=TAGS)
    app.state.engines=engines
    app.state.results=ResultStore(output)
    app.state.samples=SampleRepository(samples_db)
    for controller in (health,analysis,results,samples):app.include_router(controller.router)
    return app
