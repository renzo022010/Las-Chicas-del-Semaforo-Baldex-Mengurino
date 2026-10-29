import { jsPDF } from 'jspdf'
import { api } from './api.js'
import { dilutionLabel, fmtDateTime, sci } from './format.js'

const GREEN = [11, 74, 54]
const MUTED = [90, 100, 96]

// Reduce la foto para que el PDF no pese decenas de MB.
async function loadImage(url, maxSide = 900) {
  const res = await fetch(url)
  if (!res.ok) throw new Error('no se encontró la imagen de la placa')
  const bitmap = await createImageBitmap(await res.blob())
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  return { data: canvas.toDataURL('image/jpeg', 0.85), w: canvas.width, h: canvas.height }
}

// jsPDF no dibuja superindices Unicode: 10⁻³ se escribe 10^-3 en el PDF.
const plain = (s) => s.replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+/g, (m) => '^' + [...m].map((c) => '⁰¹²³⁴⁵⁶⁷⁸⁹'.indexOf(c) >= 0 ? '⁰¹²³⁴⁵⁶⁷⁸⁹'.indexOf(c) : '-').join(''))

export async function buildReport(sample, photos) {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  const W = 210, M = 18
  let y = 18
  const line = (h = 6) => { y += h; if (y > 275) { doc.addPage(); y = 20 } }
  const text = (s, x, opts = {}) => doc.text(plain(String(s)), x, y, opts)

  doc.setFont('helvetica', 'bold'); doc.setFontSize(13); doc.setTextColor(...GREEN)
  text('UNIVERSIDAD NACIONAL AGRARIA LA MOLINA', W / 2, { align: 'center' }); line(5.5)
  doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(...MUTED)
  text('Laboratorio de Microbiología', W / 2, { align: 'center' }); line(9)
  doc.setDrawColor(...GREEN); doc.setLineWidth(0.4); doc.line(M, y - 4, W - M, y - 4)
  doc.setFont('helvetica', 'bold'); doc.setFontSize(14); doc.setTextColor(20, 30, 26)
  text('REPORTE DE CONTEO DE UFC', W / 2, { align: 'center' }); line(10)

  const section = (title) => { doc.setFont('helvetica', 'bold'); doc.setFontSize(11); doc.setTextColor(...GREEN); text(title, M); line(6.5); doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(20, 30, 26) }
  const pair = (k, v) => { doc.setTextColor(...MUTED); text(k, M); doc.setTextColor(20, 30, 26); text(v || '—', M + 52); line(5.5) }

  section('Datos de la muestra')
  pair('Código de muestra:', sample.code)
  pair('Tipo de muestra:', sample.sample_type)
  if (sample.origin) pair('Procedencia:', sample.origin)
  pair('Fecha y hora de análisis:', fmtDateTime(sample.analyzed_at))
  pair('Responsable:', sample.responsible)
  line(3)

  section('Resultado final')
  const r = sample.result
  if (r) {
    doc.setFont('helvetica', 'bold'); doc.setFontSize(16)
    text(`${sci(r.value)} ${r.unit}`, M); line(7)
    doc.setFont('helvetica', 'normal'); doc.setFontSize(10)
    if (r.dilutions_used.length) pair('Dilución utilizada:', r.dilutions_used.map(dilutionLabel).join(', ') + (r.in_range ? '' : ' (estimado)'))
    pair('Rango contable:', `${sample.count_min} a ${sample.count_max} colonias por placa`)
    for (const w of r.warnings) { doc.setTextColor(150, 90, 0); doc.splitTextToSize(plain(w), W - 2 * M).forEach((l) => { doc.text(l, M, y); line(5) }) }
  } else { text('Sin conteos registrados.', M); line(6) }
  line(3)

  section('Diluciones y conteos')
  const cols = [M, M + 32, M + 70, M + 100, M + 130]
  doc.setTextColor(...MUTED);
  ['Dilución', 'Volumen (mL)', 'Placa A', 'Placa B', 'Promedio'].forEach((h, i) => doc.text(h, cols[i], y)); line(5.5)
  doc.setTextColor(20, 30, 26)
  for (const d of sample.dilutions) {
    const counts = [d.plate_a.count, d.plate_b.count].filter((c) => c != null)
    const mean = counts.length ? (counts.reduce((a, b) => a + b, 0) / counts.length).toFixed(1).replace('.', ',') : '—'
    ;[dilutionLabel(d.exponent), String(d.volume_ml).replace('.', ','), d.plate_a.count ?? '—', d.plate_b.count ?? '—', mean]
      .forEach((v, i) => doc.text(plain(String(v)), cols[i], y))
    line(5.5)
  }
  doc.setTextColor(...MUTED); doc.setFontSize(9)
  text(`Fórmula: UFC/${sample.unit} = (colonias promedio × 1/dilución) ÷ volumen sembrado`, M); line(8)

  if (photos.length) {
    section('Imágenes de placa')
    const size = 52, gap = 6
    let x = M
    for (const p of photos) {
      const img = await loadImage(api.fileUrl(p.id, 'foto_conteo.jpg'))
      const h = size * (img.h / img.w)
      if (y + h > 270) { doc.addPage(); y = 20; x = M }
      doc.addImage(img.data, 'JPEG', x, y, size, h)
      doc.setFontSize(8.5); doc.setTextColor(...MUTED)
      doc.text(plain(`${p.label} · ${p.count} colonias`), x, y + h + 4)
      x += size + gap
      if (x + size > W - M) { x = M; y += h + 10 }
    }
    if (x !== M) y += size + 10
  }

  section('Observaciones')
  doc.splitTextToSize(sample.notes || '—', W - 2 * M).forEach((l) => { doc.text(l, M, y); line(5) })

  doc.setFontSize(8); doc.setTextColor(...MUTED)
  doc.text('Conteo asistido por software experimental. Los resultados requieren revisión humana.', M, 287)
  doc.text(`Generado el ${fmtDateTime(new Date().toISOString())}`, W - M, 287, { align: 'right' })
  doc.save(`Reporte_${sample.code}.pdf`)
}
