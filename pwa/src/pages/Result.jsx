import { Link, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Icon } from '../icons.jsx'
import PlateReview, { pointsFromResult, pointsFromReview, reviewStats } from '../components/PlateReview.jsx'
import { updateRecent } from '../recent.js'

export default function Result() {
  const { id } = useParams()
  const [result, setResult] = useState(null)
  const [points, setPoints] = useState([])
  const [saved, setSaved] = useState(null) // revision guardada en la API
  const [edited, setEdited] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    setResult(null); setError(''); setEdited(false)
    Promise.all([api.result(id), api.savedReview(id)])
      .then(([r, review]) => {
        if (!alive) return
        setResult(r); setSaved(review)
        setPoints(review ? pointsFromReview(review, r) : pointsFromResult(r))
      })
      .catch((e) => alive && setError(e.message))
    return () => { alive = false }
  }, [id])

  async function saveReview() {
    setBusy(true); setError('')
    try {
      const record = await api.review(id, points.map(({ x, y }) => ({ x, y })), 'Revisado en la PWA')
      setSaved(record); setEdited(false)
      updateRecent(id, { reviewed: record.reviewed_count })
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  if (error && !result) return <div className="stack"><p className="alert">{error}</p><Link className="btn btn-ghost" to="/analizar">Analizar otra foto</Link></div>
  if (!result) return <p className="muted">Cargando resultado…</p>

  const stats = reviewStats(points, result.count)
  const engine = result.method?.includes('sam2') ? 'IA (híbrido)' : 'Clásico (OpenCV)'
  return (
    <div className="stack">
      <h2 className="page-title">Resultado del análisis</h2>

      <div className="result-grid">
        <PlateReview imageUrl={api.fileUrl(id, 'foto_original.jpg')} size={result.image_size} points={points}
          onChange={(p) => { setPoints(p); setEdited(true) }} />

        <aside className="count-card">
          <span className="label">Colonias detectadas</span>
          <strong className="big-count">{stats.total}</strong>
          <dl className="count-list">
            <div><dt><i className="dot-key dot-auto" /> Automático</dt><dd>{result.count}</dd></div>
            <div><dt><i className="dot-key dot-edge" /> Cerca del borde</dt><dd>{stats.edge}</dd></div>
            <div><dt><i className="dot-key dot-manual" /> Añadidas</dt><dd>{stats.added}</dd></div>
            <div><dt>Quitadas</dt><dd>{stats.removed}</dd></div>
            <div><dt>Motor</dt><dd>{engine}</dd></div>
            <div><dt>Tiempo</dt><dd>{result.processing_seconds} s</dd></div>
          </dl>
        </aside>
      </div>

      {saved && !edited && (
        <p className="ok-note"><Icon name="check" size={18} /> Revisión guardada: {saved.reviewed_count} colonias (automático: {saved.automatic_count}).</p>
      )}
      {(result.warnings || []).slice(0, 2).map((w) => <p key={w} className="warn small">{w}</p>)}
      {error && <p className="alert" role="alert">{error}</p>}

      <div className="actions">
        <Link className="btn btn-ghost" to="/analizar"><Icon name="camera" size={20} /> Nueva foto</Link>
        <button type="button" className="btn btn-primary" onClick={saveReview} disabled={busy || (!edited && saved)}>
          {busy ? 'Guardando…' : saved && !edited ? 'Revisión guardada' : 'Guardar revisión'}
        </button>
      </div>
      <a className="text-link small" href={api.fileUrl(id, 'foto_conteo.jpg')} target="_blank" rel="noreferrer">Ver imagen anotada por el motor</a>
    </div>
  )
}
