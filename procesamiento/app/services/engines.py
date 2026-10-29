"""Motores de conteo. El hibrido es opcional: si no carga, la API sigue con el clasico."""
import asyncio
from contador import count_colonies,write_result,save_image
from contador_hibrido import HybridCounter,write_hybrid_result

class EngineUnavailable(Exception):pass

class EngineService:
    def __init__(self,hybrid_factory=HybridCounter,use_hybrid=True):
        self.hybrid_factory=hybrid_factory;self.use_hybrid=use_hybrid
        self.model=None;self.error=None if use_hybrid else 'Desactivado con MOTOR=clasico'
        self.lock=None

    async def start(self):
        # The lock is created inside the server's event loop; it serializes GPU use between requests.
        self.lock=asyncio.Lock()
        if not self.use_hybrid:return
        try:self.model=await asyncio.to_thread(self.hybrid_factory)
        except Exception as exc:  # missing .venv-neural, weights or CUDA
            self.error=f'{type(exc).__name__}: {exc}'
            print('Motor hibrido no disponible, se usa el clasico. '+self.error,flush=True)

    def stop(self):self.model=None

    @property
    def engines(self):return ['hybrid','classic'] if self.model else ['classic']

    @property
    def device(self):return getattr(self.model,'hardware',None)

    def resolve(self,engine):
        if engine not in ('auto','hybrid','classic'):raise ValueError('Motor: auto, hybrid o classic')
        if engine=='auto':return self.engines[0]
        if engine=='hybrid' and not self.model:raise EngineUnavailable('Motor hibrido no disponible; usar classic')
        return engine

    async def analyze(self,bgr,engine,folder):
        """Cuenta, exporta los archivos del motor y guarda la foto original para la revision manual."""
        async with self.lock:
            fn=self.model.count if engine=='hybrid' else count_colonies
            result,debug=await asyncio.to_thread(fn,bgr)
            writer=write_hybrid_result if engine=='hybrid' else write_result
            await asyncio.to_thread(writer,result,debug,folder,'foto')
            await asyncio.to_thread(save_image,folder/'foto_original.jpg',bgr)
        return result
