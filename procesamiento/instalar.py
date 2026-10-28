"""Instala el motor clásico o híbrido en un entorno local separado (Python 3.12)."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
URLS={
    'GroundingDINO':'https://github.com/IDEA-Research/GroundingDINO.git',
    'sam2':'https://github.com/facebookresearch/sam2.git',
    'ColonyGroundedSAM2':'https://github.com/WFSRDataScience/ColonyGroundedSAM2.git',
}
def run(*args,**kwargs):
    subprocess.run([str(a) for a in args],check=True,**kwargs)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motor',choices=['clasico','hibrido'],default='clasico')
    args=parser.parse_args()
    if sys.version_info[:2]!=(3,12):
        parser.error('Usar Python 3.12, versión con la que se verificaron las dependencias fijadas.')
    neural=args.motor=='hibrido'
    env=ROOT/('.venv-neural' if neural else '.venv')
    python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():run(sys.executable,'-m','venv',env)
    requirements=ROOT/('requirements-neural.txt' if neural else 'requirements.txt')
    run(python,'-m','pip','install','-r',requirements)
    if neural:
        commits=json.loads((ROOT/'referencias/repositorios.json').read_text(encoding='utf-8'))
        for name,url in URLS.items():
            path=ROOT/'vendor'/name
            if path.exists():
                actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
                if actual!=commits[name]:raise RuntimeError(f'{name}: commit distinto al fijado; revisar antes de reemplazar.')
            else:
                path.mkdir(parents=True)
                run('git','init',path)
                run('git','-C',path,'remote','add','origin',url)
                run('git','-C',path,'fetch','--depth','1','origin',commits[name])
                run('git','-C',path,'checkout','--detach','FETCH_HEAD')
        run(python,ROOT/'preparar_compatibilidad_neural.py')
        setup_env=os.environ.copy();setup_env['SAM2_BUILD_CUDA']='0'
        run(python,'-m','pip','install','--no-build-isolation','-e',ROOT/'vendor/sam2',env=setup_env)
        run(python,ROOT/'descargar_modelos.py')
        for record in json.loads((ROOT/'referencias/modelos.json').read_text(encoding='utf-8')):
            with (ROOT/'modelos'/record['file']).open('rb') as handle:
                digest=hashlib.file_digest(handle,'sha256').hexdigest()
            if digest!=record['sha256']:raise RuntimeError('Hash inesperado: '+record['file'])
    run(python,'-m','pip','check')
    print('Instalación completada. Consultar README.md para procesar una foto o iniciar la API.')
if __name__=='__main__':main()
