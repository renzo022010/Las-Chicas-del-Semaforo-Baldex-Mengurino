"""Inspecciona AGAR y fija una particion reproducible antes del desarrollo."""
from pathlib import Path
import argparse, collections, hashlib, json, random
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT.parent / 'Dataset' / 'AGAR_representative'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    output = ROOT / 'resultados'
    output.mkdir(exist_ok=True)
    rows, groups = [], collections.defaultdict(list)
    for path in sorted(dataset.rglob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        photo = path.with_suffix('.jpg')
        with Image.open(photo) as im:
            width, height = im.size
        labels = data.get('labels', [])
        reason = None
        if data['colonies_number'] < 0:
            reason = 'sin_conteo_numerico_valido'
        elif any(label['class'] == 'Contamination' for label in labels):
            reason = 'contaminacion_con_convencion_de_conteo_distinta'
        elif len(labels) != data['colonies_number']:
            reason = 'conteo_no_coincide_con_anotaciones'
        invalid = [l for l in labels if l['width'] <= 0 or l['height'] <= 0 or l['x'] < 0 or l['y'] < 0 or l['x']+l['width'] > width or l['y']+l['height'] > height]
        if invalid:
            reason = 'cajas_fuera_de_imagen'
        row = {'image': photo.relative_to(dataset).as_posix(), 'annotation': path.relative_to(dataset).as_posix(), 'id': data['sample_id'], 'group': path.parent.relative_to(dataset).as_posix(), 'width': width, 'height': height, 'reference_count': data['colonies_number'], 'boxes': len(labels), 'classes': dict(collections.Counter(l['class'] for l in labels)), 'special_reason': reason, 'sha256': hashlib.sha256(photo.read_bytes()).hexdigest()}
        rows.append(row)
        if not reason:
            groups[row['group']].append(row['image'])
    split_path = ROOT / 'split.json'
    if split_path.exists():
        split = json.loads(split_path.read_text(encoding='utf-8'))
        assert {r['image']:r['sha256'] for r in rows} == split['image_hashes'], 'El dataset ha cambiado: revisar particion.'
    else:
        rng = random.Random(20261027)
        # Fotografias vistas antes de esta particion: nunca se reservan para evaluacion.
        seen = {'5308', '734', '14684'}
        evaluation = []
        for group, items in sorted(groups.items()):
            candidates = [x for x in items if Path(x).stem not in seen]
            rng.shuffle(candidates)
            n = 3 if group.endswith(('bright', 'vague')) else 2
            evaluation.extend(candidates[:n])
        split = {'seed':20261027, 'note':'Muestra piloto. Se reserva evaluacion antes del ajuste; los casos especiales no forman parte de las metricas principales.', 'development': [r['image'] for r in rows if not r['special_reason'] and r['image'] not in evaluation], 'evaluation': sorted(evaluation), 'special': [r['image'] for r in rows if r['special_reason']], 'image_hashes': {r['image']:r['sha256'] for r in rows}}
        split_path.write_text(json.dumps(split, indent=2), encoding='utf-8')
    (output / 'inventario.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    dev = [r for r in rows if r['image'] in split['development']]
    for offset in range(0, len(dev), 8):
        sheet = Image.new('RGB', (1600, 940), '#e8edf2')
        draw = ImageDraw.Draw(sheet)
        for j, row in enumerate(dev[offset:offset+8]):
            im = Image.open(dataset / row['image']).convert('RGB')
            im = ImageOps.contain(im, (390, 410))
            x,y = j%4*400, j//4*470
            sheet.paste(im, (x+(400-im.width)//2,y+35))
            draw.text((x+8,y+8), f"{row['id']} | referencia: {row['reference_count']}",fill='black')
            draw.text((x+8,y+450), row['group'],fill='black')
        sheet.save(output / f'desarrollo-{offset//8+1}.jpg')
    print(json.dumps({'images':len(rows),'development':len(split['development']),'evaluation':len(split['evaluation']),'special':split['special'],'evaluation_files':split['evaluation']},indent=2))

if __name__ == '__main__':
    main()
