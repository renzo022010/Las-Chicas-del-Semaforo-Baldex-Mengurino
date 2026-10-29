// Ultimos analisis de este dispositivo. La API no tiene un listado, asi que se recuerdan localmente.
const KEY = 'ufc-recientes'
const MAX = 8

export function loadRecent() {
  try { return JSON.parse(localStorage.getItem(KEY)) || [] } catch { return [] }
}

export function saveRecent(entry) {
  const list = [entry, ...loadRecent().filter((r) => r.id !== entry.id)].slice(0, MAX)
  try { localStorage.setItem(KEY, JSON.stringify(list)) } catch { /* almacenamiento bloqueado */ }
  return list
}

export function updateRecent(id, patch) {
  const current = loadRecent().find((r) => r.id === id)
  if (current) saveRecent({ ...current, ...patch })
}

export function fmtDateTime(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}
