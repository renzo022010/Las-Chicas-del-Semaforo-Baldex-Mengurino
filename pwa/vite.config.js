import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// La PWA llama a /api/*; Vite lo reenvia a la API local de FastAPI (procesamiento/INICIAR_API.cmd).
// API_URL permite apuntar a otra instancia, por ejemplo una API de prueba en otro puerto.
const proxy = {
  '/api': { target: process.env.API_URL || 'http://127.0.0.1:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') },
}

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['unalm-escudo-blanco.png', 'icon-192.png'],
      manifest: {
        name: 'Conteo de UFC',
        short_name: 'Conteo UFC',
        description: 'Conteo de colonias en placas Petri asistido por imagen.',
        lang: 'es',
        theme_color: '#0b4a36',
        background_color: '#0b4a36',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      // Las fotos y resultados dependen de la API local: nunca se sirven desde la cache.
      workbox: { navigateFallbackDenylist: [/^\/api/, /^\/docs/, /^\/redoc/, /^\/openapi\.json/] },
    }),
  ],
  // La build va directo a procesamiento/web: el servidor de Python la sirve sin necesitar Node.
  build: { outDir: '../procesamiento/web', emptyOutDir: true },
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
})
