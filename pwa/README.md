# PWA de conteo de UFC (primera versión)

Interfaz React con el flujo básico: **inicio → foto de la placa → resultado con corrección manual**. Solo usa los endpoints validados de la API (`/health`, `/analyze`, `/results/{id}/…` y `/results/{id}/review`).

Para **usar** la app no hace falta Node: `INICIAR.cmd` (raíz del repositorio) sirve la versión compilada de `procesamiento/web/`. Esta carpeta es solo para **modificar** la interfaz.

## Requisitos para desarrollar

- Node 22 y npm.
- La API corriendo: `procesamiento\INICIAR_API.cmd`. Usa el motor IA si `.venv-neural` existe; si no, arranca con el clásico.

## Desarrollo

```powershell
cd pwa
npm install
npm run dev
```

Abrir http://localhost:5173. Vite reenvía `/api` a `http://127.0.0.1:8000`; con `API_URL` se puede apuntar a otra instancia. Desde un celular en la misma red usar la IP que imprime Vite (por ejemplo `http://192.168.1.20:5173`). Por HTTP en red local la cámara funciona como subida de archivo, pero el navegador no ofrece instalar la PWA.

## Compilar

```powershell
npm run build
```

La build se escribe en `procesamiento/web/`. Después de cambiar la interfaz, compilar y versionar esa carpeta para que `INICIAR.cmd` sirva la versión nueva. `npm run preview` la abre en http://localhost:4173 para probarla como app instalable (**Instalar aplicación** en Chrome o Edge). El service worker solo guarda la interfaz; fotos y resultados siempre vienen de la API.

## Pruebas

```powershell
npm test
```

## Pantallas

1. **Inicio:** escudo UNALM, estado del motor y últimos análisis de este dispositivo (guardados en el navegador; la API no tiene listado).
2. **Registro fotográfico:** capturar o elegir de galería, vista previa y motor (IA o clásico).
3. **Resultado del análisis:** conteo, colonias cerca del borde, corrección tocando la imagen (quitar o añadir) y **Guardar revisión**. La revisión se guarda aparte en `revision.json`; la predicción original no cambia.

Trazabilidad, diluciones, UFC y reporte PDF quedan para una siguiente versión. La API ya expone `/samples` y `/ufc` como endpoints en desarrollo, y las pantallas que los usaban están en el commit `14a6ace` de la rama `mvp-pwa`.
