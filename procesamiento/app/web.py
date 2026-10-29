"""Servir la PWA y la API desde un mismo servidor: un solo puerto y un solo link para PC y celulares."""
import json,secrets
from urllib.parse import parse_qs
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

# Rutas de la API (sin el prefijo /api). Todo lo demas son archivos de la PWA.
API_PREFIXES=('/health','/analyze','/results','/samples','/ufc','/docs','/redoc','/openapi.json')

class SPAStaticFiles(StaticFiles):
    """Archivos de la PWA; una ruta desconocida (/resultado/abc) devuelve index.html para que la resuelva React."""
    async def get_response(self,path,scope):
        try:return await super().get_response(path,scope)
        except HTTPException as exc:
            if exc.status_code!=404:raise
            return await super().get_response('index.html',scope)

class ApiGateway:
    """La PWA llama a /api/...: se quita el prefijo para usar las mismas rutas que /docs y los tests.
    Con clave, toda ruta de la API exige el encabezado X-Clave o ?clave= (las imagenes no pueden enviar encabezados)."""
    def __init__(self,app,key=None):
        self.app=app;self.key=key

    async def __call__(self,scope,receive,send):
        if scope['type']=='http':
            path=scope['path']
            if path=='/api' or path.startswith('/api/'):
                path=path[4:] or '/'
                scope=dict(scope,path=path,raw_path=path.encode())
            if self.key and path.startswith(API_PREFIXES) and not self._authorized(scope):
                body=json.dumps({'detail':'Clave de acceso invalida o ausente'}).encode()
                await send({'type':'http.response.start','status':401,
                            'headers':[(b'content-type',b'application/json'),(b'content-length',str(len(body)).encode())]})
                await send({'type':'http.response.body','body':body})
                return
        await self.app(scope,receive,send)

    def _authorized(self,scope):
        headers=dict(scope.get('headers') or [])
        supplied=headers.get(b'x-clave',b'').decode('latin-1')
        if not supplied:
            supplied=parse_qs(scope.get('query_string',b'').decode('latin-1')).get('clave',[''])[0]
        return secrets.compare_digest(supplied.encode(),self.key.encode())
