# Las Chicas del Semáforo — MVP de conteo de colonias

Aplicación experimental para un proyecto de Agronomía. Incluye dos motores de conteo y una API local para conectar una futura PWA:

- **Clásico:** OpenCV, contraste LAB, delimitación de placa y separación watershed.
- **Híbrido:** OpenCV delimita la placa; Grounding DINO con pesos ColonyGroundedSAM2 detecta colonias; SAM2 obtiene sus máscaras; se filtran duplicados y regiones fuera de la placa.
- **API:** subida de fotos, consulta de resultados y registro de correcciones humanas separado de la predicción original.

El modelo neuronal ya está integrado. No se entrenó una nueva red en este proyecto. La PWA está en `pwa/` y su versión compilada en `procesamiento/web/`.

## Inicio rápido (todo en uno, Windows)

Doble clic en **`INICIAR.cmd`** (raíz del repositorio). No hace falta tener Python ni Node instalados:

1. La primera vez descarga [uv](https://github.com/astral-sh/uv) y un Python 3.12 portable en `runtime/`, e instala el motor clásico (~1 minuto).
2. Si hay GPU NVIDIA, ofrece instalar el motor IA (~5 GB). Si ya existe `procesamiento/.venv-neural`, lo usa directamente.
3. Inicia un solo servidor con la app y la API, abre el navegador y muestra en la consola el link y un QR para celulares conectados al mismo wifi.

Para usar e instalar la app desde celulares fuera de la red local, doble clic en **`COMPARTIR.cmd`**: además abre un link HTTPS público temporal con [Cloudflare Tunnel](https://github.com/cloudflare/cloudflared) (se descarga a `runtime/` la primera vez; el link cambia en cada inicio). La PC debe quedar encendida mientras se use.

Cada link incluye una clave de acceso (`?clave=...`) guardada en `runtime/clave.txt`; sin ella la API responde 401. Para invalidar los links ya compartidos: `INICIAR.cmd --nueva-clave`. Otras opciones: `--instalar-ia`, `--puerto N`, `--sin-navegador`. Todo lo descargado vive en `runtime/` (ignorado por Git); borrar esa carpeta deja el repositorio como recién clonado.

## Instalación manual

Entorno probado: **Windows, Python 3.12, NVIDIA RTX 5060 de 8 GB**, PyTorch con CUDA 12.8. Instalar Python 3.12 y Git antes de empezar. El motor clásico no necesita GPU.

```powershell
git clone https://github.com/renzo022010/Las-Chicas-del-Semaforo-Baldex-Mengurino.git
cd Las-Chicas-del-Semaforo-Baldex-Mengurino\procesamiento
```

Instalar el motor clásico:

```powershell
py -3.12 instalar.py --motor clasico
```

Instalar el híbrido y descargar los pesos oficiales:

```powershell
py -3.12 instalar.py --motor hibrido
```

La instalación híbrida descarga varios GB. Crea `.venv-neural`, clona versiones fijadas de los repositorios de los modelos, descarga sus pesos y verifica los hashes registrados. Usa la implementación PyTorch de atención deformable para evitar compilar extensiones CUDA en Windows. SAM2 se instala sin su extensión opcional de limpieza de máscaras. No modifica el entorno clásico `.venv`.

## Procesar una fotografía

Dentro de `procesamiento`:

```powershell
.\.venv\Scripts\python.exe contador.py 'C:\ruta\foto.jpg'
.\.venv-neural\Scripts\python.exe contador_hibrido.py 'C:\ruta\foto.jpg'
```

También se puede arrastrar una foto sobre `PROCESAR_FOTO.cmd` o `PROCESAR_HIBRIDO.cmd`. El doble clic sin foto intenta abrir un ejemplo AGAR que no se distribuye en este repositorio; utilizar una foto propia o agregar el dataset.

Salidas: imagen anotada, JSON con conteo y detecciones, máscara de placa, mapa de instancias y regiones coloreadas. El híbrido guarda sus archivos en `procesamiento/resultados/hibrido_individual`.

Para corregir el límite automático, usar `--roi X Y RADIO` en píxeles de la imagen original. El parámetro `--box-threshold 0.25` controla la admisión de candidatos neuronales. Los scores no son probabilidades calibradas y todos los conteos requieren revisión.

## API local

Ejecutar `procesamiento/INICIAR_API.cmd` o, dentro de esa carpeta:

```powershell
.\.venv-neural\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Abrir [la documentación interactiva](http://127.0.0.1:8000/docs) después del mensaje `Application startup complete`.

Endpoints validados (los que usa la PWA):

- `GET /health`: estado del motor.
- `POST /analyze?engine=hybrid`: subir una fotografía en el campo multipart `file`.
- `POST /analyze?engine=classic`: comparar con el procesamiento clásico.
- `GET /results/{analysis_id}/foto_conteo.jpg`: consultar la imagen anotada (`foto_original.jpg` es la foto sin marcas).
- `POST /results/{analysis_id}/review`: guardar centros corregidos manualmente sin sobrescribir el resultado automático.

En desarrollo, sin validar y no usados por la PWA todavía:

- `GET/POST /samples`, `GET/PUT/DELETE /samples/{id}`: registro de muestras (trazabilidad y diluciones) en `resultados/muestras.db`.
- `POST /ufc`: calcular UFC/mL o UFC/g a partir de diluciones, volumen sembrado y conteos de placa.

`POST /analyze` usa `engine=auto` por defecto: híbrido si el modelo cargó, clásico si no. Si `.venv-neural` no existe o el modelo falla al cargar, la API arranca igual con el motor clásico (`GET /health` indica el motivo en `neural_error`). La interfaz PWA está en [`pwa/`](pwa/README.md).

Organización del código (`procesamiento/app/`):

```text
api.py                 punto de entrada (uvicorn api:app)
lanzador.py            usado por INICIAR.cmd: dependencias, servidor, navegador, QR y túnel
app/main.py            create_app(): crea los servicios y registra los controladores
app/config.py          rutas, límites y CLAVE_ACCESO
app/web.py             PWA compilada en el mismo puerto, prefijo /api y clave de acceso
app/controllers/       una ruta HTTP por archivo: health, analysis, results, samples
app/services/          lógica sin HTTP: engines (motores y GPU), images, results, samples, ufc
app/schemas/           validación Pydantic de entradas
web/                   PWA compilada (npm run build en pwa/); se versiona para no requerir Node
```

Si existe `web/`, `INICIAR_API.cmd` también sirve la app en http://127.0.0.1:8000 (solo esta PC, sin clave).

Los controladores solo traducen peticiones y errores; los motores de conteo (`contador.py`, `contador_hibrido.py`) no cambian.

Ejemplo de revisión, con coordenadas de la foto original:

```json
{"centers":[{"x":120,"y":230},{"x":360,"y":420}],"note":"Revisado manualmente"}
```

La API conserva los modelos en memoria y serializa el procesamiento para compartir la GPU. Las fotos se procesan localmente; no se envían a un servicio externo. Este servidor está preparado para una demo local, no como despliegue público.

## Resultados de la demo

Comparación en 38 fotos AGAR conocidas:

| Medida | Clásico v0.2 | Híbrido v0.3 |
|---|---:|---:|
| Error absoluto medio (colonias/foto) | 9,45 | 1,97 |
| Conteo en placa 5271 (referencia 43) | 41 | 42 |

Mejoraron 31 fotos, empeoraron 2 y 5 conservaron el mismo error. En 5271, el híbrido obtuvo 42 coincidencias, ninguna detección adicional y una omisión según el emparejamiento centro/caja. Tiempo medio híbrido: 1,51 s por foto con el modelo cargado, excluyendo lectura y exportación; carga inicial de esa ejecución: 13,25 s.

**No es una validación independiente:** los pesos publicados se ajustaron con AGAR, por lo que puede existir solapamiento con entrenamiento. Se necesitan fotografías propias nuevas y revisión de sus anotaciones para medir generalización. La correspondencia centro/caja no equivale a mAP ni mide exactitud de las máscaras.

[Resumen](procesamiento/resultados/RESUMEN_HIBRIDO.md) · [Métricas por foto](procesamiento/resultados/hibrido_v0_3/metricas.csv) · [Configuración y resumen](procesamiento/resultados/hibrido_v0_3/resumen.json).

## Dataset y reproducción

Las fotos y anotaciones AGAR **no están incluidas**. Para reproducir la comparación exacta, disponer de la misma muestra y colocarla en:

```text
Dataset/AGAR_representative/
  higher-resolution/bright/
  higher-resolution/dark/
  higher-resolution/vague/
  lower-resolution/
```

Cada foto necesita su JSON correspondiente. `procesamiento/split.json` registra los nombres y hashes de la muestra utilizada. La partición conserva nombres históricos `development`/`evaluation`, pero ambos grupos ya son conocidos. La referencia `colonies_number` se lee después de inferir y nunca entra en el detector.

Dentro de `procesamiento`, tras instalar ambos motores:

```powershell
.\.venv\Scripts\python.exe evaluar.py --split development --tag v0_2_final
.\.venv\Scripts\python.exe evaluar.py --split evaluation --tag v0_2_final
.\.venv-neural\Scripts\python.exe evaluar_hibrido.py
.\.venv\Scripts\python.exe generar_informe_hibrido.py
```

El informe HTML se genera localmente con las imágenes anotadas. Los resúmenes y CSV de la ejecución original están versionados; las fotos, las máscaras, las subidas a la API, los pesos y los entornos Python están excluidos de Git.

## Pruebas

```powershell
cd procesamiento
.\.venv-neural\Scripts\python.exe -m unittest test_hibrido test_procesamiento test_muestras test_servidor -v
```

Se verificaron 24 pruebas funcionales y una subida HTTP real con el modelo neuronal. Las pruebas sintéticas y de contrato API no sustituyen la evaluación biológica. La PWA tiene sus propias pruebas: `npm test` dentro de `pwa/`.

## Modelos, fuentes y atribución

- [ColonyGroundedSAM2 — código oficial](https://github.com/WFSRDataScience/ColonyGroundedSAM2) y [pesos](https://huggingface.co/DataScienceWFSR/ColonyGroundedSAM2).
- [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO).
- [SAM2](https://github.com/facebookresearch/sam2).
- [BERT base uncased](https://huggingface.co/google-bert/bert-base-uncased).
- Korporaal et al., *Colony Grounded SAM2: Zero-shot detection and segmentation of bacterial colonies using foundation models*, 2026. [Artículo](https://arxiv.org/html/2603.13393v1).

Los hashes de los pesos y commits de los repositorios se guardan en `procesamiento/referencias`. Los repositorios de terceros se descargan con sus licencias; no se redistribuyen aquí sus pesos ni su código. Consultar las condiciones originales antes de redistribuir modelos o datasets.
