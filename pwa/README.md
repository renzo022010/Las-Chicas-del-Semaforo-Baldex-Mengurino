# PWA de conteo de UFC (MVP local)

Interfaz React para el flujo del laboratorio: **trazabilidad → diluciones y conteo → foto de placa → reporte PDF**. Habla con la API de `procesamiento/` a través de `/api` (Vite reenvía las llamadas a `http://127.0.0.1:8000`).

## Requisitos

- Node 22 y npm.
- La API corriendo: `procesamiento\INICIAR_API.cmd`. Usa el motor IA si `.venv-neural` existe; si no, arranca con el clásico.

## Desarrollo

```powershell
cd pwa
npm install
npm run dev
```

Abrir http://localhost:5173. Desde un celular en la misma red usar la IP que imprime Vite (por ejemplo `http://192.168.1.20:5173`). Por HTTP en red local la cámara funciona como subida de archivo, pero el navegador no ofrece instalar la PWA.

## Probar como PWA instalable

```powershell
npm run build
npm run preview
```

Abrir http://localhost:4173 en Chrome o Edge y usar **Instalar aplicación** en la barra de direcciones. Las fotos y resultados siempre vienen de la API local; el service worker solo guarda la interfaz.

## Pruebas

```powershell
npm test
```

## Qué hace cada paso

1. **Trazabilidad:** código automático `M-00001`, fecha y hora, tipo de muestra, procedencia y responsable.
2. **Diluciones y conteo:** tabla de diluciones con placas A y B. La API calcula UFC/g o UFC/mL con las diluciones cuyo promedio cae en el rango contable (30–300 por defecto, editable). Se guarda solo.
3. **Foto de placa:** captura o galería, conteo con IA o clásico, y corrección tocando la imagen (quitar o añadir colonias). La corrección se guarda aparte en `revision.json`; la predicción original no se modifica.
4. **Reporte:** resumen, imágenes de placa, observaciones y PDF.
