"""Lanzador todo en uno: prepara dependencias, inicia el servidor (PWA + API en un puerto) y abre la app.
Se ejecuta desde INICIAR.cmd con el Python portable de runtime/. Uso:
  INICIAR.cmd                 esta PC y celulares en el mismo wifi
  INICIAR.cmd compartir       ademas, link HTTPS publico (tunel de Cloudflare) para instalar la app en celulares
Opciones: --instalar-ia, --puerto N, --nueva-clave, --sin-navegador
"""
from pathlib import Path
import argparse,hashlib,json,os,re,secrets,shutil,socket,subprocess,sys,threading,time,urllib.request,webbrowser
from instalar import when_unlocked

ROOT=Path(__file__).resolve().parent.parent
PROC=ROOT/'procesamiento'
RT=ROOT/'runtime'
WIN=os.name=='nt'
EXTRA=['qrcode==8.0']  # QR en consola para abrir la app desde el celular
CLOUDFLARED_URL='https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
LOCAL=urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never route localhost through a system proxy

def say(msg=''):print(msg,flush=True)

def venv_python(env):return env/('Scripts/python.exe' if WIN else 'bin/python')

def download(url,dest):
    tmp=dest.with_suffix(dest.suffix+'.part')
    urllib.request.urlretrieve(url,tmp)
    when_unlocked(lambda:tmp.replace(dest))

def ensure_server_deps():
    """Instala el motor clasico y el servidor en el Python portable; se repite solo si cambia requirements.txt."""
    req=PROC/'requirements.txt'
    stamp=RT/'dependencias.sha256'
    want=hashlib.sha256(req.read_bytes()+' '.join(EXTRA).encode()).hexdigest()
    if stamp.is_file() and stamp.read_text()==want:return
    say('Instalando el motor clasico y el servidor (solo la primera vez, ~1 minuto)...')
    uv=os.environ.get('UV_EXE') or shutil.which('uv')
    cmd=[uv,'pip','install','--python',sys.executable] if uv else [sys.executable,'-m','pip','install']
    subprocess.run([*cmd,'-r',str(req),*EXTRA],check=True)
    stamp.write_text(want)

def trust_bundled_certificates():
    """Un Windows recien instalado trae pocos certificados raiz y Python solo ve esos: las descargas de modelos
    fallarian con CERTIFICATE_VERIFY_FAILED. Se suma certifi, heredado por instalar.py y descargar_modelos.py."""
    try:import certifi
    except ImportError:return
    os.environ.setdefault('SSL_CERT_FILE',certifi.where())

def has_nvidia_gpu():
    exe=shutil.which('nvidia-smi')
    return bool(exe) and subprocess.run([exe,'-L'],capture_output=True).returncode==0

def neural_python():
    env=PROC/'.venv-neural'
    py=venv_python(env)
    # instalar.py leaves this mark until it finishes: a half-installed environment must not be used.
    if (env/'instalacion-en-curso').exists():return None
    return py if py.is_file() and (PROC/'modelos/manifest.json').is_file() else None

def maybe_install_neural(force,device="auto"):
    """Ofrece el motor IA para CPU o GPU; la respuesta 'no' se recuerda. Si falla, la app abre con el clasico."""
    if neural_python() and not force:return
    prefs_file=RT/'preferencias.json'
    prefs=json.loads(prefs_file.read_text(encoding='utf-8')) if prefs_file.is_file() else {}
    def remember_no():
        prefs['instalar_ia']='no';prefs_file.write_text(json.dumps(prefs),encoding='utf-8')
    if not force:
        if prefs.get('instalar_ia')=='no':return
        if has_nvidia_gpu():
            say('\nSe detecto una GPU NVIDIA. El motor IA es mucho mas preciso que el clasico y tarda segundos por foto.')
        else:
            say('\nEsta PC no tiene GPU NVIDIA. El motor clasico (liviano) ya esta listo y responde en segundos.')
            say('Opcional: el motor IA es mas preciso, pero en el procesador cada foto puede tardar de 30 s a varios minutos.')
        say('El motor IA descarga varios GB. Se puede instalar despues con: INICIAR.cmd --instalar-ia')
        try:answer=input('Instalar el motor IA ahora? [s/N]: ').strip().lower()
        except EOFError:answer=''
        if answer not in ('s','si','sí','y','yes'):
            remember_no()
            return
    say('Instalando el motor IA...')
    try:subprocess.run([sys.executable,str(PROC/'instalar.py'),'--motor','hibrido','--device',device],cwd=PROC,check=True)
    except subprocess.CalledProcessError:
        say('\nNo se pudo instalar el motor IA (ver el mensaje anterior). La app se abre con el motor clasico.')
        say('Para reintentar: INICIAR.cmd --instalar-ia')
        remember_no()

def access_key(renew):
    path=RT/'clave.txt'
    if path.is_file() and not renew:return path.read_text(encoding='utf-8').strip()
    key=secrets.token_urlsafe(9)
    path.write_text(key,encoding='utf-8')
    return key

def free_port(start):
    for port in range(start,start+20):
        with socket.socket() as s:
            try:s.bind(('0.0.0.0',port));return port
            except OSError:continue
    raise SystemExit(f'No hay puertos libres entre {start} y {start+19}.')

def lan_ip():
    # Connecting a UDP socket sends nothing; it only asks the OS which interface would be used.
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        try:s.connect(('192.0.2.1',80));return s.getsockname()[0]
        except OSError:return None

class ServerFailed(Exception):pass

def wait_ready(port,key,server,timeout=240):
    req=urllib.request.Request(f'http://127.0.0.1:{port}/api/health',headers={'X-Clave':key})
    start=time.time()
    while time.time()-start<timeout:
        if server.poll() is not None:raise ServerFailed('El servidor se cerro al iniciar. Revisa el mensaje anterior.')
        try:
            with LOCAL.open(req,timeout=3) as r:return json.load(r)
        except OSError:time.sleep(1)
    raise ServerFailed('El servidor no respondio a tiempo.')

def start_server(python,port,env):
    return subprocess.Popen([str(python),'-X','utf8','-m','uvicorn','api:app','--host','0.0.0.0','--port',str(port),
                             '--log-level','warning'],cwd=PROC,env=env)

def stop(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:proc.wait(10)
        except subprocess.TimeoutExpired:proc.kill()

def start_tunnel(port):
    exe=shutil.which('cloudflared')
    if not exe:
        exe=RT/('cloudflared.exe' if WIN else 'cloudflared')
        if not exe.is_file():
            if not WIN:raise SystemExit('Instala cloudflared para compartir por internet: https://github.com/cloudflare/cloudflared')
            say('Descargando cloudflared (tunel HTTPS de Cloudflare, solo la primera vez)...')
            download(CLOUDFLARED_URL,exe)
    log=open(RT/'tunel.log','w',encoding='utf-8')
    proc=subprocess.Popen([str(exe),'tunnel','--no-autoupdate','--url',f'http://127.0.0.1:{port}'],
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    found=threading.Event();box={}
    def pump():
        for line in proc.stdout:
            log.write(line);log.flush()
            m=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
            if m and not found.is_set():box['url']=m.group(0);found.set()
    threading.Thread(target=pump,daemon=True).start()
    if not found.wait(60):
        proc.terminate()
        raise SystemExit('No se pudo abrir el tunel. Revisa runtime/tunel.log.')
    return proc,box['url']

def show_qr(url):
    try:import qrcode
    except ImportError:return
    qr=qrcode.QRCode(border=2);qr.add_data(url);qr.make(fit=True)
    qr.print_ascii(invert=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('modo',nargs='?',choices=['local','compartir'],default='local')
    parser.add_argument('--instalar-ia',action='store_true',help='instalar o reparar el motor IA (varios GB, CPU o NVIDIA)')
    parser.add_argument('--device',choices=['auto','cpu','cuda'],default='auto',help='dispositivo del motor IA')
    parser.add_argument('--puerto',type=int,default=8000)
    parser.add_argument('--nueva-clave',action='store_true',help='invalida los links compartidos antes')
    parser.add_argument('--sin-navegador',action='store_true')
    args=parser.parse_args()
    RT.mkdir(exist_ok=True)

    ensure_server_deps()
    trust_bundled_certificates()
    maybe_install_neural(args.instalar_ia,args.device)
    if not (PROC/'web/index.html').is_file():
        raise SystemExit('Falta la PWA compilada en procesamiento/web. Ejecuta "npm run build" dentro de pwa/.')

    neural=neural_python()
    python=neural or Path(sys.executable)
    key=access_key(args.nueva_clave)
    port=free_port(args.puerto)
    if port!=args.puerto:say(f'El puerto {args.puerto} esta ocupado; se usa el {port}.')

    env=dict(os.environ,CLAVE_ACCESO=key,PYTHONUTF8='1')
    env['IA_DEVICE']=args.device
    if not neural:env['MOTOR']='clasico'
    if neural and args.device=='cpu':say('IA en CPU: el analisis puede tardar varios minutos; espera a que termine.')
    say('\nIniciando el servidor'+(' y cargando el modelo IA (puede tardar varios minutos)...' if neural else '...'))
    server=start_server(python,port,env)
    tunnel=None
    try:
        try:health=wait_ready(port,key,server,timeout=900)
        except ServerFailed as exc:
            if not neural:raise SystemExit(str(exc)) from None
            # A broken neural environment must not block the app: the classic engine has its own Python.
            say(f'{exc}\nEl motor IA no pudo iniciar; se abre con el motor clasico.')
            stop(server)
            env['MOTOR']='clasico'
            server=start_server(sys.executable,port,env)
            try:health=wait_ready(port,key,server)
            except ServerFailed as again:raise SystemExit(str(again)) from None
        local=f'http://localhost:{port}/?clave={key}'
        ip=lan_ip();lan=f'http://{ip}:{port}/?clave={key}' if ip else None
        public=None
        if args.modo=='compartir':tunnel,public=start_tunnel(port);public=f'{public}/?clave={key}'

        engine=f"IA ({health.get('device')})" if 'hybrid' in health['engines'] else 'clasico (OpenCV)'
        say('\n'+'='*64)
        say(f'  Conteo de UFC listo · motor {engine}')
        say('='*64)
        say(f'  En esta PC:          {local}')
        if lan:say(f'  Celular (mismo wifi): {lan}')
        if public:say(f'  Link HTTPS publico:   {public}')
        say('\n  Escanea con el celular:'+(' (link HTTPS, permite instalar la app)' if public else ''))
        show_qr(public or lan or local)
        if public:say('  El link publico puede tardar unos segundos en responder la primera vez.')
        elif WIN:say('  Si Windows pregunta por el firewall, permite "redes privadas" para que entren los celulares.')
        say('  No compartas la clave del link fuera del grupo. Para cerrar: Ctrl+C o cierra esta ventana.\n')
        if not args.sin_navegador:webbrowser.open(local)
        code=server.wait()
        # Nothing stops the server except Ctrl+C, handled below: it crashed, and the window must stay open to read why.
        if code:raise SystemExit(f'El servidor se cerro inesperadamente (codigo {code}). Revisa el mensaje anterior.')
    except KeyboardInterrupt:
        say('\nCerrando...')
    finally:
        stop(tunnel);stop(server)

if __name__=='__main__':main()
