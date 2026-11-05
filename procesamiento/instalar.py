"""Instala el motor clásico o híbrido en un entorno local separado (Python 3.12). No necesita Git."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,time,urllib.request,zipfile
ROOT=Path(__file__).resolve().parent
REPOS={
    'GroundingDINO':'IDEA-Research/GroundingDINO',
    'sam2':'facebookresearch/sam2',
    'ColonyGroundedSAM2':'WFSRDataScience/ColonyGroundedSAM2',
}
ARCHIVE='https://github.com/{slug}/archive/{commit}.zip'
SKIP_DIRS=('demo','notebooks')  # not needed to run the models, and the deepest paths in sam2
COMMIT_FILE='.commit'
IN_PROGRESS='instalacion-en-curso'  # lanzador.py ignores an environment that still has this mark

def run(*args,**kwargs):
    subprocess.run([str(a) for a in args],check=True,**kwargs)

def vendored_commit(path):
    """Commit de un repositorio en vendor/: su marca, o .git/HEAD en instalaciones antiguas hechas con Git."""
    for mark in (path/COMMIT_FILE,path/'.git/HEAD'):
        if mark.is_file():return mark.read_text(encoding='utf-8').strip()
    return None

def when_unlocked(action,seconds=180):
    """Reintenta mientras otro proceso retiene un archivo: el antivirus revisa cada descarga nueva en Windows."""
    limit=time.monotonic()+seconds
    while True:
        try:return action()
        except PermissionError:
            if time.monotonic()>limit:raise
            time.sleep(1)

def fetch_repo(name,slug,commit,vendor=None):
    """Deja en vendor/ el commit fijado, descargado como ZIP de GitHub. La marca del commit se escribe al final:
    una carpeta sin marca quedo a medias y se reemplaza."""
    vendor=vendor or ROOT/'vendor'
    path=vendor/name
    actual=vendored_commit(path)
    if actual==commit:return
    if actual:raise RuntimeError(f'{name}: commit distinto al fijado; revisar antes de reemplazar.')
    if path.exists():when_unlocked(lambda:shutil.rmtree(path))
    vendor.mkdir(parents=True,exist_ok=True)
    print('Descargando '+name,flush=True)
    archive=vendor/f'.{name}.zip'
    urllib.request.urlretrieve(ARCHIVE.format(slug=slug,commit=commit),archive)
    with zipfile.ZipFile(archive) as bundle:
        # git archive stores the commit id as the ZIP comment.
        if bundle.comment.decode('ascii','replace')!=commit:
            raise RuntimeError(f'{name}: el ZIP descargado no corresponde al commit fijado.')
        for member in bundle.infolist():
            # Drop the top folder <repo>-<commit>: 40 extra characters can exceed the Windows path limit.
            member.filename=member.filename.partition('/')[2]
            if member.filename and member.filename.split('/')[0] not in SKIP_DIRS:bundle.extract(member,path)
    (path/COMMIT_FILE).write_text(commit,encoding='utf-8')
    try:when_unlocked(archive.unlink,seconds=30)
    except PermissionError:pass  # a leftover ZIP is harmless; the next install overwrites it

def install_requirements(python,requirements):
    # uv handles deep paths without LongPathsEnabled; pip fails there when the project folder has a long name.
    uv=os.environ.get('UV_EXE') or shutil.which('uv')
    if not uv:
        run(python,'-m','pip','install','-r',requirements)
        return
    # Packages without wheels (antlr4, iopath) build inside the cache: it needs a short path, not the project folder.
    cache=Path(tempfile.gettempdir())/'ufc-uv'
    run(uv,'pip','install','--python',python,'--cache-dir',cache,'--index-strategy','unsafe-best-match','-r',requirements)
    shutil.rmtree(cache,ignore_errors=True)

def place_cpp_runtime(env):
    """Copia el runtime de Visual C++ (paquete msvc-runtime, DLL firmadas por Microsoft) junto a PyTorch.
    Un Windows limpio no lo trae e instalarlo en el sistema exige permisos de administrador."""
    lib=env/'Lib/site-packages/torch/lib'
    for dll in env.glob('msvcp140*.dll'):when_unlocked(lambda:shutil.copy2(dll,lib))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motor',choices=['clasico','hibrido'],default='clasico')
    parser.add_argument('--device',choices=['auto','cpu','cuda'],default='auto')
    args=parser.parse_args()
    if sys.version_info[:2]!=(3,12):
        parser.error('Usar Python 3.12, versión con la que se verificaron las dependencias fijadas.')
    neural=args.motor=='hibrido'
    device=args.device
    if device=='auto':
        exe=shutil.which('nvidia-smi')
        device='cuda' if exe and subprocess.run([exe,'-L'],capture_output=True).returncode==0 else 'cpu'
    env=ROOT/('.venv-neural' if neural else '.venv')
    python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():run(sys.executable,'-m','venv',env)
    requirements=ROOT/('requirements-neural.txt' if neural else 'requirements.txt')
    if neural and device=='cpu':requirements=ROOT/'requirements-neural-cpu.txt'
    ready=env/'instalacion-completa.json'
    ready.unlink(missing_ok=True)
    (env/IN_PROGRESS).touch()
    install_requirements(python,requirements)
    if neural:
        place_cpp_runtime(env)
        commits=json.loads((ROOT/'referencias/repositorios.json').read_text(encoding='utf-8'))
        for name,slug in REPOS.items():fetch_repo(name,slug,commits[name])
        run(python,ROOT/'preparar_compatibilidad_neural.py')
        setup_env=os.environ.copy();setup_env['SAM2_BUILD_CUDA']='0'
        run(python,'-m','pip','install','--no-build-isolation','-e',ROOT/'vendor/sam2',env=setup_env)
        run(python,ROOT/'descargar_modelos.py')
        for record in json.loads((ROOT/'referencias/modelos.json').read_text(encoding='utf-8')):
            with (ROOT/'modelos'/record['file']).open('rb') as handle:
                digest=hashlib.file_digest(handle,'sha256').hexdigest()
            if digest!=record['sha256']:raise RuntimeError('Hash inesperado: '+record['file'])
    run(python,'-m','pip','check')
    ready.write_text(json.dumps({'device':device if neural else None}),encoding='utf-8')
    (env/IN_PROGRESS).unlink()
    print('Instalación completada. Consultar README.md para procesar una foto o iniciar la API.')
if __name__=='__main__':main()
