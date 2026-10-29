"""Construccion de la API: servicios en app.state y un router por controlador."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from contador_hibrido import HybridCounter
from app.config import OUTPUT,SAMPLES_DB,hybrid_requested
from app.controllers import analysis,health,results,samples
from app.services.engines import EngineService
from app.services.results import ResultStore
from app.services.samples import SampleRepository
from app.web import ApiGateway,SPAStaticFiles

TAGS=[{'name':'Estado'},{'name':'Analisis'},{'name':'Resultados'},
      {'name':'Muestras (en desarrollo)','description':'Trazabilidad, diluciones y UFC. Aun no validado ni usado por la PWA.'}]

def create_app(output=OUTPUT,samples_db=SAMPLES_DB,hybrid_factory=HybridCounter,use_hybrid=None,web_dir=None,access_key=None):
    """web_dir sirve la PWA compilada en el mismo puerto; access_key exige una clave en cada ruta de la API."""
    engines=EngineService(hybrid_factory,hybrid_requested() if use_hybrid is None else use_hybrid)

    @asynccontextmanager
    async def lifespan(app):
        await engines.start()
        yield
        engines.stop()

    app=FastAPI(title='Conteo de colonias - MVP',version='0.5.0',lifespan=lifespan,openapi_tags=TAGS)
    app.state.engines=engines
    app.state.results=ResultStore(output)
    app.state.samples=SampleRepository(samples_db)
    for controller in (health,analysis,results,samples):app.include_router(controller.router)
    app.add_middleware(ApiGateway,key=access_key)
    if web_dir and (Path(web_dir)/'index.html').is_file():
        # Mounted last: API routes and /docs match first, everything else is the PWA.
        app.mount('/',SPAStaticFiles(directory=web_dir,html=True),name='pwa')
    return app
