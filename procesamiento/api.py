"""API local para la futura PWA. Iniciar con INICIAR_API.cmd; documentacion /docs."""
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio,io,json,uuid
from PIL import Image,UnidentifiedImageError
import numpy as np,cv2
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from contador import count_colonies,write_result
from contador_hibrido import HybridCounter,write_hybrid_result
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'resultados/api'
MAX_BYTES=20*1024*1024

@asynccontextmanager
async def lifespan(app):
    app.state.lock=asyncio.Lock()
    app.state.model=await asyncio.to_thread(HybridCounter)
    yield
    del app.state.model

app=FastAPI(title='Conteo de colonias - MVP',version='0.3.0',lifespan=lifespan)

@app.get('/health')
def health():
    model=getattr(app.state,'model',None)
    return {'ready':model is not None,'neural_model':'ColonyGroundedSAM2','device':model.hardware if model else None}

@app.post('/analyze')
async def analyze(file:UploadFile=File(...),engine:str='hybrid'):
    if engine not in ('hybrid','classic'):raise HTTPException(400,'Motor: hybrid o classic')
    raw=await file.read(MAX_BYTES+1)
    await file.close()
    if len(raw)>MAX_BYTES:raise HTTPException(413,'Maximo 20 MB')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            w,h=image.size
            if min(w,h)<64 or w*h>60_000_000:raise ValueError('Dimensiones no permitidas')
            bgr=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2BGR)
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError) as exc:
        raise HTTPException(400,'Fotografia no valida: '+str(exc)) from exc
    ident=uuid.uuid4().hex;folder=OUTPUT/ident
    async with app.state.lock:
        fn=app.state.model.count if engine=='hybrid' else count_colonies
        result,debug=await asyncio.to_thread(fn,bgr)
        writer=write_hybrid_result if engine=='hybrid' else write_result
        await asyncio.to_thread(writer,result,debug,folder,'foto')
    result['analysis_id']=ident
    result['annotated_url']=f'/results/{ident}/foto_conteo.jpg'
    result['json_url']=f'/results/{ident}/foto_resultado.json'
    return result

@app.get('/results/{analysis_id}/{name}')
def result_file(analysis_id:str,name:str):
    if len(analysis_id)!=32 or any(c not in '0123456789abcdef' for c in analysis_id):
        raise HTTPException(404,'No encontrado')
    if name not in ('foto_conteo.jpg','foto_resultado.json','foto_segments.png','foto_instances.png','foto_roi.png','revision.json'):
        raise HTTPException(404,'No encontrado')
    path=OUTPUT/analysis_id/name
    if not path.is_file():raise HTTPException(404,'No encontrado')
    return FileResponse(path)

class Point(BaseModel):
    x:float=Field(ge=0,allow_inf_nan=False)
    y:float=Field(ge=0,allow_inf_nan=False)
class Review(BaseModel):
    centers:list[Point]=Field(max_length=10000)
    note:str=Field(default='',max_length=2000)

@app.post('/results/{analysis_id}/review')
def review(analysis_id:str,data:Review):
    # Keep the automatic result immutable and store explicit human corrections separately.
    result_file(analysis_id,'foto_resultado.json')
    path=OUTPUT/analysis_id
    original=json.loads((path/'foto_resultado.json').read_text(encoding='utf-8'))
    w=original['image_size']['width'];h=original['image_size']['height']
    if any(p.x>=w or p.y>=h for p in data.centers):raise HTTPException(400,'Centro fuera de imagen')
    record={'automatic_count':original['count'],'reviewed_count':len(data.centers),**data.model_dump(),
            'review_type':'human_submitted_centers_not_model_prediction'}
    (path/'revision.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    return record
