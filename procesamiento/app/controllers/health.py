from fastapi import APIRouter,Depends
from app.dependencies import get_engines
from app.services.engines import EngineService
router=APIRouter(tags=['Estado'])

@router.get('/health')
def health(engines:EngineService=Depends(get_engines)):
    return {'ready':True,'engines':engines.engines,'default_engine':engines.engines[0],
            'neural_model':'ColonyGroundedSAM2','device':engines.device,'neural_error':engines.error}
