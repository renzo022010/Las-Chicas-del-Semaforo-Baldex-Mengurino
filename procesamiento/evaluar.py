"""Comparacion en imagenes conocidas: las anotaciones solo se leen DESPUES de la inferencia."""
from pathlib import Path
import argparse, csv, hashlib, json, statistics, sys
from dataclasses import asdict
from PIL import Image,ImageOps,ImageDraw
from contador import Config,count_colonies,read_image,write_result

ROOT=Path(__file__).resolve().parent

def match_centers(detections, boxes):
    adjacency=[]
    for d in detections:
        adjacency.append([i for i,b in enumerate(boxes) if b['x']<=d['x']<=b['x']+b['width'] and b['y']<=d['y']<=b['y']+b['height']])
    assigned={}
    def visit(pred,seen):
        for gt in adjacency[pred]:
            if gt in seen: continue
            seen.add(gt)
            if gt not in assigned or visit(assigned[gt],seen):
                assigned[gt]=pred
                return True
        return False
    return sum(visit(i,set()) for i in range(len(detections)))


def summarize(rows):
    n=len(rows)
    matched=sum(r['matched_centers'] for r in rows)
    predicted=sum(r['predicted'] for r in rows)
    reference=sum(r['reference'] for r in rows)
    return {'n':n,'mae_colonies':round(statistics.mean(r['absolute_error'] for r in rows),3),
        'bias_colonies':round(statistics.mean(r['predicted']-r['reference'] for r in rows),3),
        'median_absolute_error':statistics.median(r['absolute_error'] for r in rows),
        'within_10_percent_or_2_colonies':sum(r['absolute_error']<=max(2,.10*r['reference']) for r in rows),
        'seconds_mean':round(statistics.mean(r['seconds'] for r in rows),3),
        'center_in_box_precision':round(matched/predicted,4) if predicted else None,
        'center_in_box_recall':round(matched/reference,4) if reference else None,
        'localization_note':'Correspondencia uno a uno: centro predicho dentro de caja AGAR. No equivale a mAP/IoU.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,default=ROOT.parent/'Dataset'/'AGAR_representative')
    p.add_argument('--split',choices=['development','evaluation'],default='development')
    p.add_argument('--sensitivity',type=float,default=1.0)
    p.add_argument('--min-area',type=float,default=25)
    p.add_argument('--margin',type=float,default=Config().border_margin)
    p.add_argument('--no-split',action='store_true')
    p.add_argument('--split-prominence',type=float,default=Config().split_prominence)
    p.add_argument('--tag',default='baseline')
    p.add_argument('--no-images',action='store_true')
    args=p.parse_args()
    if Path(args.tag).name != args.tag or args.tag in {'.','..'}:
        p.error('tag debe ser un nombre simple, sin directorios.')
    split=json.loads((ROOT/'split.json').read_text(encoding='utf-8'))
    cfg=Config(sensitivity=args.sensitivity,min_area=args.min_area,border_margin=args.margin,split_touching=not args.no_split,split_prominence=args.split_prominence)
    output=ROOT/'resultados'/f'{args.split}_{args.tag}'
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for relative in split[args.split]:
        image_path=args.dataset/relative
        actual=hashlib.sha256(image_path.read_bytes()).hexdigest()
        if actual!=split['image_hashes'][relative]:
            raise ValueError(f'Imagen modificada: {relative}')
        result,debug=count_colonies(read_image(image_path),cfg)
        # Ground truth never enters the detector.
        ann=json.loads(image_path.with_suffix('.json').read_text())
        reference=ann['colonies_number']
        if reference<0 or len(ann['labels'])!=reference:
            raise ValueError(f'Referencia no comparable: {relative}')
        matched=match_centers(result['detections'],ann['labels'])
        row={'image':relative,'group':Path(relative).parent.as_posix(),'reference':reference,'predicted':result['count'],
             'absolute_error':abs(result['count']-reference),'seconds':result['processing_seconds'],'matched_centers':matched,
             'false_positive_centers':result['count']-matched,'missed_reference_centers':reference-matched,
             'polarity':result['polarity_used'],'roi_method':result['roi']['method'],'threshold':round(result['threshold'],2)}
        rows.append(row)
        if not args.no_images:
            result['input_image']=str(image_path.resolve())
            write_result(result,debug,output,image_path.stem)
        print(f"{image_path.stem}: referencia={reference:3} pred={result['count']:3} error={row['absolute_error']:3} matched={matched:3} {row['polarity']} ROI={row['roi_method']}",flush=True)
    with (output/'metricas.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={'evaluation_status':'comparison_on_previously_seen_images_not_independent_validation','split':args.split,'tag':args.tag,'config':asdict(cfg),'detector_sha256':hashlib.sha256((ROOT/'contador.py').read_bytes()).hexdigest(),
        'overall':summarize(rows),'groups':{g:summarize([r for r in rows if r['group']==g]) for g in sorted(set(r['group'] for r in rows))}}
    (output/'resumen.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    if not args.no_images:
        for offset in range(0,len(rows),8):
            sheet=Image.new('RGB',(1600,940),'#e8edf2');draw=ImageDraw.Draw(sheet)
            for j,row in enumerate(rows[offset:offset+8]):
                stem=Path(row['image']).stem
                im=Image.open(output/f'{stem}_conteo.jpg');im=ImageOps.contain(im,(390,410))
                x,y=j%4*400,j//4*470
                sheet.paste(im,(x+(400-im.width)//2,y+35))
                draw.text((x+8,y+8),f"{stem} | ref {row['reference']} | pred {row['predicted']} | error {row['absolute_error']}",fill='black')
                draw.text((x+8,y+450),row['group'],fill='black')
            sheet.save(output/f'comparacion-{offset//8+1}.jpg')
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
