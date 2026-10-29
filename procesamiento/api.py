"""API local para la PWA. Iniciar con INICIAR_API.cmd; documentacion /docs.
MOTOR=clasico evita cargar el modelo neuronal; si no carga, la API sigue con el motor clasico."""
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio,io,json,os,uuid
from PIL import Image,ImageOps,UnidentifiedImageError
import numpy as np,cv2
from fastapi import FastAPI,UploadFile,File,HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from contador import count_colonies,write_result,save_image
from contador_hibrido import HybridCounter,write_hybrid_result
from muestras import router as samples_router
ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'resultados/api'
MAX_BYTES=20*1024*1024

@asynccontextmanager
async def lifespan(app):
    app.state.lock=asyncio.Lock()
    app.state.model=None;app.state.model_error=None
    if os.environ.get('MOTOR','hibrido').lower().startswith('clas'):
        app.state.model_error='Desactivado con MOTOR=clasico'
    else:
        try:app.state.model=await asyncio.to_thread(HybridCounter)
        except Exception as exc:  # missing .venv-neural, weights or CUDA: keep the classic engine available
            app.state.model_error=f'{type(exc).__name__}: {exc}'
            print('Motor hibrido no disponible, se usa el clasico. '+app.state.model_error,flush=True)
    yield
    app.state.model=None

app=FastAPI(title='Conteo de colonias - MVP',version='0.4.0',lifespan=lifespan)
app.include_router(samples_router)

@app.get('/health')
def health():
    model=getattr(app.state,'model',None)
    return {'ready':True,'engines':['hybrid','classic'] if model else ['classic'],'default_engine':'hybrid' if model else 'classic',
            'neural_model':'ColonyGroundedSAM2','device':getattr(model,'hardware',None),'neural_error':getattr(app.state,'model_error',None)}

@app.post('/analyze')
async def analyze(file:UploadFile=File(...),engine:str='auto'):
    if engine not in ('auto','hybrid','classic'):raise HTTPException(400,'Motor: auto, hybrid o classic')
    if engine=='auto':engine='hybrid' if app.state.model else 'classic'
    if engine=='hybrid' and not app.state.model:raise HTTPException(503,'Motor hibrido no disponible; usar classic')
    raw=await file.read(MAX_BYTES+1)
    await file.close()
    if len(raw)>MAX_BYTES:raise HTTPException(413,'Maximo 20 MB')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            w,h=image.size
            if min(w,h)<64 or w*h>60_000_000:raise ValueError('Dimensiones no permitidas')
            # Phone photos carry their rotation in EXIF; apply it so the photo and coordinates match what the user saw.
            bgr=cv2.cvtColor(np.asarray(ImageOps.exif_transpose(image).convert('RGB')),cv2.COLOR_RGB2BGR)
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError) as exc:
        raise HTTPException(400,'Fotografia no valida: '+str(exc)) from exc
    ident=uuid.uuid4().hex;folder=OUTPUT/ident
    async with app.state.lock:
        fn=app.state.model.count if engine=='hybrid' else count_colonies
        result,debug=await asyncio.to_thread(fn,bgr)
        writer=write_hybrid_result if engine=='hybrid' else write_result
        await asyncio.to_thread(writer,result,debug,folder,'foto')
        await asyncio.to_thread(save_image,folder/'foto_original.jpg',bgr)
    result['analysis_id']=ident
    result['engine']=engine
    result['annotated_url']=f'/results/{ident}/foto_conteo.jpg'
    result['original_url']=f'/results/{ident}/foto_original.jpg'
    result['json_url']=f'/results/{ident}/foto_resultado.json'
    return result

@app.get('/results/{analysis_id}/{name}')
def result_file(analysis_id:str,name:str):
    if len(analysis_id)!=32 or any(c not in '0123456789abcdef' for c in analysis_id):
        raise HTTPException(404,'No encontrado')
    if name not in ('foto_conteo.jpg','foto_original.jpg','foto_resultado.json','foto_segments.png','foto_instances.png','foto_roi.png','revision.json'):
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
