# PWA de conteo de UFC (primera versión)

Interfaz React con el flujo básico: **inicio → foto de la placa → resultado con corrección manual**. Solo usa los endpoints validados de la API (`/health`, `/analyze`, `/results/{id}/…` y `/results/{id}/review`). Vite reenvía `/api` a `http://127.0.0.1:8000`; con `API_URL` se puede apuntar a otra instancia.

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

Abrir http://localhost:4173 en Chrome o Edge y usar **Instalar aplicación** en la barra de direcciones. El service worker solo guarda la interfaz; fotos y resultados siempre vienen de la API local.

## Pruebas

```powershell
npm test
```

## Pantallas

1. **Inicio:** escudo UNALM, estado del motor y últimos análisis de este dispositivo (guardados en el navegador; la API no tiene listado).
2. **Registro fotográfico:** capturar o elegir de galería, vista previa y motor (IA o clásico).
3. **Resultado del análisis:** conteo, colonias cerca del borde, corrección tocando la imagen (quitar o añadir) y **Guardar revisión**. La revisión se guarda aparte en `revision.json`; la predicción original no cambia.

Trazabilidad, diluciones, UFC y reporte PDF quedan para una siguiente versión. La API ya expone `/samples` y `/ufc` como endpoints en desarrollo, y las pantallas que los usaban están en el commit `14a6ace` de la rama `mvp-pwa`.
