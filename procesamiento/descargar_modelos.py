from pathlib import Path
from urllib.request import urlretrieve
import hashlib,json
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parent
sources={
 'colony_gd.pth':'https://huggingface.co/DataScienceWFSR/ColonyGroundedSAM2/resolve/main/checkpoints/colony_gd.pth',
 'sam2_hiera_large.pt':'https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_large.pt'
}
for name in ['config.json','tokenizer_config.json','tokenizer.json','vocab.txt','model.safetensors']:
    sources['bert-base-uncased/'+name]='https://huggingface.co/google-bert/bert-base-uncased/resolve/main/'+name

def download(item):
    name,url=item
    dst=root/'modelos'/name
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():
        print('Descargando '+name,flush=True)
        tmp=dst.with_suffix('.part')
        urlretrieve(url,tmp)
        tmp.replace(dst)
    digest=hashlib.file_digest(dst.open('rb'),'sha256').hexdigest()
    print(name+' listo: '+str(dst.stat().st_size)+' bytes',flush=True)
    return {'file':name,'url':url,'bytes':dst.stat().st_size,'sha256':digest}
if __name__=='__main__':
    (root/'modelos').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        manifest=list(pool.map(download,sources.items()))
    (root/'modelos/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
