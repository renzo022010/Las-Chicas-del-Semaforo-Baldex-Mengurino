"""Registro de muestras (trazabilidad, diluciones y UFC) para la PWA. SQLite local, sin servicios externos."""
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Literal
import json,sqlite3,threading
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field,model_validator
ROOT=Path(__file__).resolve().parent
DB=ROOT/'resultados/muestras.db'
_lock=threading.Lock()
router=APIRouter()

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

def calcular_ufc(data:UfcInput):
    """UFC por mL o g = promedio de placas x 10^exponente / volumen sembrado.
    Usa las diluciones cuyo promedio cae en el rango contable; si ninguna cae, estima con la mas cercana."""
    rows=[]
    for d in data.dilutions:
        counts=[p.count for p in (d.plate_a,d.plate_b) if p.count is not None]
        if not counts:continue
        mean=sum(counts)/len(counts)
        rows.append({'exponent':d.exponent,'volume_ml':d.volume_ml,'mean':mean,'plates':len(counts),
                     'per_unit':mean*10**d.exponent/d.volume_ml})
    if not rows:return None
    warnings=[]
    lo,hi=data.count_min,data.count_max
    valid=[r for r in rows if lo<=r['mean']<=hi]
    if valid:
        used=valid
    elif all(r['mean']==0 for r in rows):
        low=min(rows,key=lambda r:r['exponent'])
        limit=10**low['exponent']/low['volume_ml']
        return {'value':0,'unit':'UFC/'+data.unit,'in_range':False,'dilutions_used':[],'rows':rows,
                'detection_limit':limit,'warnings':[f'Sin colonias en ninguna placa: reportar como < {limit:.3g} UFC/{data.unit}.']}
    else:
        nonzero=[r for r in rows if r['mean']>0] or rows
        used=[min(nonzero,key=lambda r:lo-r['mean'] if r['mean']<lo else r['mean']-hi)]
        warnings.append(f'Ninguna dilucion tiene un promedio entre {lo} y {hi} colonias: el resultado es una estimacion.')
    if any(r['plates']<2 for r in used):warnings.append('Alguna dilucion usada tiene una sola placa contada.')
    value=sum(r['per_unit'] for r in used)/len(used)
    return {'value':value,'unit':'UFC/'+data.unit,'in_range':bool(valid),'dilutions_used':[r['exponent'] for r in used],
            'rows':rows,'warnings':warnings}

@contextmanager
def connect():
    # One connection per request, serialized: a local demo has few concurrent writers.
    with _lock:
        DB.parent.mkdir(parents=True,exist_ok=True)
        con=sqlite3.connect(DB)
        try:
            con.execute('create table if not exists samples(id integer primary key,code text unique not null,data text not null,'
                        'created_at text not null,updated_at text not null)')
            yield con
            con.commit()
        finally:con.close()

def record(row):
    ident,code,data,created,updated=row
    body=json.loads(data)
    return {'id':ident,'code':code,**body,'result':calcular_ufc(UfcInput(**body)),'created_at':created,'updated_at':updated}

def fetch(con,ident):
    row=con.execute('select id,code,data,created_at,updated_at from samples where id=?',(ident,)).fetchone()
    if row is None:raise HTTPException(404,'Muestra no encontrada')
    return row

@router.post('/ufc')
def ufc(data:UfcInput):
    return calcular_ufc(data)

@router.get('/samples')
def list_samples():
    with connect() as con:
        rows=con.execute('select id,code,data,created_at,updated_at from samples order by id desc').fetchall()
    out=[]
    for row in rows:
        r=record(row)
        out.append({k:r[k] for k in ('id','code','analyzed_at','sample_type','responsible','origin','updated_at')}|
                   {'result':r['result'] and {k:r['result'][k] for k in ('value','unit','in_range')}})
    return out

@router.post('/samples',status_code=201)
def create_sample(data:SampleIn):
    now=datetime.now().isoformat(timespec='seconds')
    with connect() as con:
        last=con.execute('select max(id) from samples').fetchone()[0] or 0
        code=f'M-{last+1:05d}'
        cur=con.execute('insert into samples(code,data,created_at,updated_at) values(?,?,?,?)',
                        (code,data.model_dump_json(),now,now))
        return record(fetch(con,cur.lastrowid))

@router.get('/samples/{ident}')
def get_sample(ident:int):
    with connect() as con:return record(fetch(con,ident))

@router.put('/samples/{ident}')
def update_sample(ident:int,data:SampleIn):
    now=datetime.now().isoformat(timespec='seconds')
    with connect() as con:
        fetch(con,ident)
        con.execute('update samples set data=?,updated_at=? where id=?',(data.model_dump_json(),now,ident))
        return record(fetch(con,ident))

@router.delete('/samples/{ident}',status_code=204)
def delete_sample(ident:int):
    with connect() as con:
        fetch(con,ident)
        con.execute('delete from samples where id=?',(ident,))
