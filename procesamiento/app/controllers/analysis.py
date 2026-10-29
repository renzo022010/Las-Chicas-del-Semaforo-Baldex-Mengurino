from fastapi import APIRouter,Depends,File,HTTPException,UploadFile
from app.config import MAX_BYTES
from app.dependencies import get_engines,get_results
from app.services.engines import EngineService,EngineUnavailable
from app.services.images import InvalidPhoto,decode_photo
from app.services.results import ResultStore
router=APIRouter(tags=['Analisis'])

@router.post('/analyze')
async def analyze(file:UploadFile=File(...),engine:str='auto',
                  engines:EngineService=Depends(get_engines),results:ResultStore=Depends(get_results)):
    try:engine=engines.resolve(engine)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    except EngineUnavailable as exc:raise HTTPException(503,str(exc)) from exc
    raw=await file.read(MAX_BYTES+1)
    await file.close()
    if len(raw)>MAX_BYTES:raise HTTPException(413,'Maximo 20 MB')
    try:bgr=decode_photo(raw)
    except InvalidPhoto as exc:raise HTTPException(400,'Fotografia no valida: '+str(exc)) from exc
    ident,folder=results.new_folder()
    result=await engines.analyze(bgr,engine,folder)
    result['analysis_id']=ident
    result['engine']=engine
    result['annotated_url']=f'/results/{ident}/foto_conteo.jpg'
    result['original_url']=f'/results/{ident}/foto_original.jpg'
    result['json_url']=f'/results/{ident}/foto_resultado.json'
    return result
