// Cliente de la API local. La PWA solo usa los endpoints validados: health, analyze, results y review.
const BASE = '/api'
const OFFLINE = 'No hay conexión con el servidor. Inícialo con INICIAR.cmd y vuelve a intentar.'
const KEY_STORE = 'ufc-clave'

export class AccessDenied extends Error {}

// El lanzador abre la app con ?clave=...: se guarda en este dispositivo y se quita de la barra de direcciones.
function readKey() {
  const url = new URL(window.location.href)
  const fromLink = url.searchParams.get('clave')
  if (fromLink) {
    try { localStorage.setItem(KEY_STORE, fromLink) } catch { /* almacenamiento bloqueado */ }
    url.searchParams.delete('clave')
    window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash)
    return fromLink
  }
  try { return localStorage.getItem(KEY_STORE) || '' } catch { return '' }
}
const key = readKey()

async function req(path, opts = {}) {
  let res
  try {
    res = await fetch(BASE + path, { ...opts, headers: { ...(opts.headers || {}), ...(key ? { 'X-Clave': key } : {}) } })
  } catch {
    throw new Error(OFFLINE)
  }
  // Vite responde 502/504 cuando la API no esta levantada.
  if (res.status === 502 || res.status === 504) throw new Error(OFFLINE)
  if (res.status === 401) throw new AccessDenied('Falta la clave de acceso. Abre el link completo (o el QR) que muestra INICIAR.cmd.')
  if (!res.ok) {
    let detail = null
    try { detail = (await res.json()).detail } catch { /* sin cuerpo JSON */ }
    throw new Error(typeof detail === 'string' ? detail : `La API respondió con error ${res.status}.`)
  }
  return res.json()
}

export const api = {
  health: () => req('/health'),
  analyze: (file, engine = 'auto') => {
    const fd = new FormData()
    fd.append('file', file)
    return req(`/analyze?engine=${engine}`, { method: 'POST', body: fd })
  },
  result: (id) => req(`/results/${id}/foto_resultado.json`),
  savedReview: (id) => req(`/results/${id}/revision.json`).catch(() => null),
  review: (id, centers, note = '') => req(`/results/${id}/review`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ centers, note }),
  }),
  // <img> no puede enviar encabezados: la clave va en la URL de la imagen.
  fileUrl: (id, name) => `${BASE}/results/${id}/${name}${key ? `?clave=${encodeURIComponent(key)}` : ''}`,
}
