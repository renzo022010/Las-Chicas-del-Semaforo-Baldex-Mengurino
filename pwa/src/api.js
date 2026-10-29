// Cliente de la API local. La PWA solo usa los endpoints validados: health, analyze, results y review.
const BASE = '/api'
const OFFLINE = 'No hay conexión con la API local. Inicia procesamiento/INICIAR_API.cmd y vuelve a intentar.'

async function req(path, opts = {}) {
  let res
  try {
    res = await fetch(BASE + path, opts)
  } catch {
    throw new Error(OFFLINE)
  }
  // Vite responde 502/504 cuando la API no esta levantada.
  if (res.status === 502 || res.status === 504) throw new Error(OFFLINE)
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
  fileUrl: (id, name) => `${BASE}/results/${id}/${name}`,
}
