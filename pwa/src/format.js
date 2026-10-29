const SUP = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴', 5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' }

export const sup = (n) => String(n).split('').map((c) => SUP[c] ?? c).join('')

// 28000 -> "2,8 × 10⁴" (coma decimal, como en los reportes del laboratorio)
export function sci(value, digits = 2) {
  if (value == null || Number.isNaN(value)) return '—'
  if (value === 0) return '0'
  let exp = Math.floor(Math.log10(Math.abs(value)))
  let mant = Number((value / 10 ** exp).toPrecision(digits))
  if (Math.abs(mant) >= 10) { mant /= 10; exp += 1 }
  const m = String(mant).replace('.', ',')
  return exp === 0 ? m : `${m} × 10${sup(exp)}`
}

export const dilutionLabel = (exponent) => `10${sup(-exponent)}`

export function fmtDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export function nowLocalInput() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}
