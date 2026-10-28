"""Informe comparativo clasico/hibrido sobre datos AGAR conocidos."""
from pathlib import Path
import csv,json,html,hashlib,shutil
from PIL import Image,ImageOps,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'resultados'
def main():
    folder=OUT/'hibrido_v0_3'
    info=json.loads((folder/'resumen.json').read_text(encoding='utf-8'))
    assert info['detector_sha256']==hashlib.sha256((ROOT/'contador_hibrido.py').read_bytes()).hexdigest()
    rows=list(csv.DictReader((folder/'metricas.csv').open(encoding='utf-8-sig')))
    assert len(rows)==38
    example=next(r for r in rows if Path(r['image']).stem=='5271')
    canvas=Image.new('RGB',(1400,1000),'#edf4f0');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',27)
    title=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',34)
    draw.text((26,16),'Conteo de colonias | Placa 5271 | Referencia: 43',font=title,fill='#183e34')
    for i,(path,label) in enumerate([(OUT/'evaluation_v0_2_final/5271_conteo.jpg','Procesamiento clasico: '+example['classic']),(folder/'5271_conteo.jpg','Motor hibrido: '+example['predicted'])]):
        im=ImageOps.contain(Image.open(path),(660,800))
        x=24+i*700;draw.text((x,72),label,font=font,fill='#183e34')
        canvas.paste(im,(x+(660-im.width)//2,116))
    draw.text((26,935),f"Hibrido: {example['matched_centers']} coincidencias, {example['extra']} extras, {example['missed']} omisiones.",font=font,fill='#183e34')
    canvas.save(OUT/'comparacion_hibrida_5271.jpg',quality=92)
    overall=info['overall'];same=len(rows)-info['improved']-info['worsened']
    table=''
    for r in rows:
        stem=Path(r['image']).stem
        table+=f'<tr><td><a href="hibrido_v0_3/{stem}_conteo.jpg">{html.escape(r["image"])}</a></td><td>{r["reference"]}</td><td>{r["classic"]}</td><td>{r["predicted"]}</td><td>{r["classic_error"]} → {r["absolute_error"]}</td><td>{r["matched_centers"]}</td><td>{r["extra"]}</td><td>{r["missed"]}</td><td>{r["seconds"]}</td></tr>'
    summary=f'''# Resultado del motor híbrido v0.3

- 38 imágenes AGAR conocidas, con posible solapamiento con el entrenamiento del modelo. No es una validación independiente.
- Error absoluto medio del clásico: {info['classic_mae']:.2f} colonias/foto. Híbrido: {overall['mae_colonies']:.2f}.
- Mejoran {info['improved']}, empeoran {info['worsened']}, mantienen error {same}.
- Coincidencias uno a uno centro/caja: precisión {overall['center_in_box_precision']:.4f}, recuperación {overall['center_in_box_recall']:.4f}. No son mAP/IoU ni precisión validada en fotos propias.
- Tiempo medio: {overall['seconds_mean']:.2f} s/foto; carga del modelo en esta ejecución: {info['model_load_seconds']:.2f} s.
- GPU: {info['hardware']}; máximo de memoria asignada por PyTorch: {info['max_gpu_mb']:.1f} MB. No incluye toda la memoria del proceso/contexto CUDA o del escritorio.
- Placa 5271: clásico {example['classic']}, híbrido {example['predicted']}, referencia {example['reference']}; {example['matched_centers']} coincidencias, {example['extra']} extras y {example['missed']} omisiones.

No se entrenó ni ajustó una red con estas fotos durante esta integración. Los pesos de los autores sí se ajustaron con AGAR. El modelo puede seguir omitiendo colonias juntas, pequeñas o periféricas; revisar cada resultado. Se conserva el motor clásico y la predicción automática original al guardar correcciones humanas.

SHA256 del motor: {info['detector_sha256']}
'''
    (OUT/'RESUMEN_HIBRIDO.md').write_text(summary,encoding='utf-8')
    doc=f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MVP · Conteo híbrido</title><style>body{{font:17px/1.6 system-ui;color:#193e33;background:#edf4f0;margin:0}}main{{max-width:1320px;padding:30px;margin:auto}}h1{{font-size:40px;line-height:1.2}}h2{{margin-top:36px}}.notice{{background:#fff0d0;padding:18px;border-radius:10px}}.hero{{width:100%;height:auto}}.cards{{display:flex;gap:18px;flex-wrap:wrap}}.card{{background:white;border-radius:12px;padding:20px;flex:1;min-width:170px}}.value{{font-size:34px;font-weight:700}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:9px;text-align:left;border-bottom:1px solid #cbd9d0}}th{{background:#dbe9e0}}.scroll{{overflow:auto}}a{{color:#00664e}}code{{overflow-wrap:anywhere}}@media(max-width:700px){{main{{padding:16px}}}}</style><main><p>AGRONOMÍA · TECNOLOGÍAS · DEMO LOCAL</p><h1>Motor híbrido de conteo de colonias</h1><p>OpenCV delimita la placa. Grounding DINO detecta colonias con los pesos especializados de ColonyGroundedSAM2. SAM2 genera sus contornos. Los filtros eliminan duplicados y candidatos fuera de la placa.</p><p class="notice">Comparación en 38 fotos AGAR ya conocidas. El detector publicado se ajustó con AGAR: puede haber solapamiento con entrenamiento. Estos resultados no demuestran generalización a fotos del laboratorio.</p>
<div class="cards"><div class="card">Error medio clásico<div class="value">{info['classic_mae']:.2f}</div>colonias por foto</div><div class="card">Error medio híbrido<div class="value">{overall['mae_colonies']:.2f}</div>colonias por foto</div><div class="card">Tiempo medio híbrido<div class="value">{overall['seconds_mean']:.2f} s</div>sin carga inicial del modelo</div></div>
<h2>Tu ejemplo, con los dos motores</h2><img class="hero" src="comparacion_hibrida_5271.jpg" alt="Comparación de la placa 5271"><p>Verde: contorno candidato interior. Naranja: candidato cercano al borde. Azul: área evaluada. Los colores no representan confianza estadística. La referencia proviene del JSON de AGAR; no se utiliza para generar detecciones.</p>
<h2>Cómo probarlo</h2><p>Ejecutar <a href="../PROCESAR_HIBRIDO.cmd">PROCESAR_HIBRIDO.cmd</a> para el ejemplo o arrastrar otra foto sobre ese archivo. Se guardan imagen anotada, JSON y máscaras. <a href="../README_HIBRIDO.md">Instrucciones completas</a>.</p><p>Para la API, ejecutar <a href="../INICIAR_API.cmd">INICIAR_API.cmd</a> y abrir <a href="http://127.0.0.1:8000/docs">la documentación interactiva local</a>. Permite subir fotografías. La API también admite guardar centros corregidos manualmente, conservando el resultado automático.</p>
<h2>Comparación completa</h2><p>Mejoran {info['improved']} fotos, empeoran {info['worsened']} y {same} conservan el mismo error de conteo. Se emparejan centros predichos con cajas de referencia uno a uno; esto no evalúa la exactitud de las máscaras. Un conteo cercano puede ocultar detecciones adicionales y omisiones.</p><div class="scroll"><table><thead><tr><th>Foto / resultado</th><th>Ref.</th><th>Clásico</th><th>Híbrido</th><th>Error</th><th>Coinc.</th><th>Extras</th><th>Omitidas</th><th>Segundos</th></tr></thead><tbody>{table}</tbody></table></div>
<h2>Ejecución y trazabilidad</h2><p>{html.escape(info['hardware'])}. Carga inicial: {info['model_load_seconds']:.2f} s en esta ejecución. La API mantiene modelos en memoria entre peticiones; el comando individual los carga cada vez. Pico de memoria asignada por PyTorch: {info['max_gpu_mb']:.1f} MB, sin incluir todo el contexto CUDA o el escritorio.</p><p>Entorno neuronal separado, pesos locales y configuración común para todas las fotos. Las referencias se leen después de inferir. Quedan guardados los hashes de pesos, versiones de dependencias, commits de terceros y parámetros.</p><p><a href="RESUMEN_HIBRIDO.md">Resumen</a> · <a href="hibrido_v0_3/metricas.csv">Métricas CSV</a> · <a href="hibrido_v0_3/resumen.json">Resumen JSON</a> · <a href="INFORME_v0_2.html">Informe clásico anterior</a></p><p>SHA256 del motor: <code>{info['detector_sha256']}</code></p></main></html>'''
    (OUT/'INFORME_HIBRIDO.html').write_text(doc,encoding='utf-8')
    shutil.copy2(OUT/'INFORME_HIBRIDO.html',OUT/'INFORME.html')
    print(summary)
if __name__=='__main__':main()
