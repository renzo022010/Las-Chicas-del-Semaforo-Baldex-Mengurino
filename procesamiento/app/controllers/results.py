from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse
from app.dependencies import get_results
from app.schemas.results import Review
from app.services.results import ResultNotFound,ResultStore
router=APIRouter(prefix='/results',tags=['Resultados'])

@router.get('/{analysis_id}/{name}')
def result_file(analysis_id:str,name:str,results:ResultStore=Depends(get_results)):
    try:return FileResponse(results.path(analysis_id,name))
    except ResultNotFound:raise HTTPException(404,'No encontrado') from None

@router.post('/{analysis_id}/review')
def review(analysis_id:str,data:Review,results:ResultStore=Depends(get_results)):
    try:return results.save_review(analysis_id,data)
    except ResultNotFound:raise HTTPException(404,'No encontrado') from None
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
