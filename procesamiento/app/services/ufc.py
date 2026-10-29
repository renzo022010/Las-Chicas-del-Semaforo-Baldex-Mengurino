"""En desarrollo: calculo de UFC/mL o UFC/g a partir de diluciones y conteos de placa."""
from app.schemas.samples import UfcInput

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
