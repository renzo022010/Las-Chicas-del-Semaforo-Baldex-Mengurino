"""Comparacion reproducible de los 38 ejemplos; anotaciones solo despues de inferir."""
from pathlib import Path
import csv,json,hashlib,statistics,time
from PIL import Image,ImageOps,ImageDraw,ImageFont
from contador import read_image
from contador_hibrido import HybridCounter,write_hybrid_result
from evaluar import match_centers,summarize
ROOT=Path(__file__).resolve().parent

def main():
    split=json.loads((ROOT/'split.json').read_text(encoding='utf-8'))
    dataset=ROOT.parent/'Dataset/AGAR_representative'
    output=ROOT/'resultados/hibrido_v0_3';output.mkdir(parents=True,exist_ok=True)
    detector_hash=hashlib.sha256((ROOT/'contador_hibrido.py').read_bytes()).hexdigest()
    model=HybridCounter();rows=[]
    for group in ['evaluation','development']:
        for relative in split[group]:
            path=dataset/relative
            assert hashlib.sha256(path.read_bytes()).hexdigest()==split['image_hashes'][relative]
            print('Procesando '+relative,flush=True)
            result,debug=model.count(read_image(path))
            result['input_image']=str(path.resolve());write_hybrid_result(result,debug,output,path.stem)
            ann=json.loads(path.with_suffix('.json').read_text())
            reference=ann['colonies_number']
            assert reference>=0 and len(ann['labels'])==reference
            matched=match_centers(result['detections'],ann['labels'])
            base=json.loads((ROOT/f'resultados/{group}_v0_2_final/{path.stem}_resultado.json').read_text(encoding='utf-8'))
            row={'image':relative,'group':group,'reference':reference,'classic':base['count'],'predicted':result['count'],
                 'absolute_error':abs(result['count']-reference),'classic_error':abs(base['count']-reference),
                 'matched_centers':matched,'extra':result['count']-matched,'missed':reference-matched,
                 'seconds':result['processing_seconds'],'peak_gpu_mb':result['peak_gpu_allocated_mb']}
            rows.append(row)
            print(json.dumps(row),flush=True)
            # Write incrementally so a failed run retains completed evidence, without a final summary.
            with (output/'metricas.csv').open('w',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=row.keys());writer.writeheader();writer.writerows(rows)
    summary={'evaluation_status':'known_AGAR_images_possible_overlap_with_neural_training_not_independent_validation',
             'overall':summarize(rows),'groups':{g:summarize([r for r in rows if r['group']==g]) for g in ['evaluation','development']},
             'classic_mae':statistics.mean(r['classic_error'] for r in rows),'model_load_seconds':model.load_seconds,
             'hardware':model.hardware,'max_gpu_mb':max(r['peak_gpu_mb'] for r in rows),
             'improved':sum(r['absolute_error']<r['classic_error'] for r in rows),'worsened':sum(r['absolute_error']>r['classic_error'] for r in rows),
             'detector_sha256':detector_hash,
             'sources':json.loads((ROOT/'vendor/manifest.json').read_text())}
    (output/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
