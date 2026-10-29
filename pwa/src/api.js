const BASE = '/api'

const FIELD_NAMES = {
  analyzed_at: 'Fecha y hora', sample_type: 'Tipo de muestra', responsible: 'Responsable',
  volume_ml: 'Volumen sembrado', count: 'Conteo', exponent: 'Dilución', count_min: 'Rango contable',
}

function describeError(status, body) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const d = detail[0]
    const field = [...(d.loc || [])].reverse().find((k) => FIELD_NAMES[k])
    return field ? `${FIELD_NAMES[field]}: revisa el valor ingresado.` : d.msg
  }
  return `La API respondió con error ${status}.`
}

async function req(path, opts = {}) {
  let res
  try {
    res = await fetch(BASE + path, opts)
  } catch {
    throw new Error('No hay conexión con la API local. Inicia procesamiento/INICIAR_API.cmd y vuelve a intentar.')
  }
  if (res.status === 502 || res.status === 504) {
    throw new Error('No hay conexión con la API local. Inicia procesamiento/INICIAR_API.cmd y vuelve a intentar.')
  }
  if (!res.ok) {
    let body = null
    try { body = await res.json() } catch { /* sin cuerpo JSON */ }
    throw new Error(describeError(res.status, body))
  }
  return res.status === 204 ? null : res.json()
}

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const SAMPLE_FIELDS = ['analyzed_at', 'sample_type', 'responsible', 'origin', 'notes', 'unit', 'count_min', 'count_max', 'dilutions']
export const sampleBody = (s) => Object.fromEntries(SAMPLE_FIELDS.map((k) => [k, s[k]]))

export const api = {
  health: () => req('/health'),
  samples: () => req('/samples'),
  sample: (id) => req(`/samples/${id}`),
  create: (s) => req('/samples', json('POST', sampleBody(s))),
  update: (id, s) => req(`/samples/${id}`, json('PUT', sampleBody(s))),
  remove: (id) => req(`/samples/${id}`, { method: 'DELETE' }),
  analyze: (file, engine = 'auto') => {
    const fd = new FormData()
    fd.append('file', file)
    return req(`/analyze?engine=${engine}`, { method: 'POST', body: fd })
  },
  review: (id, centers, note = '') => req(`/results/${id}/review`, json('POST', { centers, note })),
  result: (id) => req(`/results/${id}/foto_resultado.json`),
  savedReview: (id) => req(`/results/${id}/revision.json`).catch(() => null),
  fileUrl: (id, name) => `${BASE}/results/${id}/${name}`,
}
