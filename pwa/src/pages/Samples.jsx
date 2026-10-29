import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Icon } from '../icons.jsx'
import { fmtDateTime, sci } from '../format.js'

export default function Samples() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.samples().then(setRows).catch((e) => setError(e.message)) }, [])

  return (
    <div className="stack">
      <div className="row-between">
        <h2 className="page-title">Muestras</h2>
        <Link className="btn btn-primary btn-small" to="/muestra/nueva/1">Nueva</Link>
      </div>
      {error && <p className="alert">{error}</p>}
      {rows === null && !error && <p className="muted">Cargando…</p>}
      {rows?.length === 0 && (
        <div className="empty">
          <p>Aún no hay muestras registradas.</p>
          <Link className="btn btn-primary" to="/muestra/nueva/1">Registrar la primera</Link>
        </div>
      )}
      <ul className="sample-list">
        {rows?.map((s) => (
          <li key={s.id}>
            <Link to={`/muestra/${s.id}/4`} className="sample-row">
              <div className="sample-main">
                <strong>{s.code}</strong>
                <span>{s.sample_type}{s.origin ? ` · ${s.origin}` : ''} · {s.responsible}</span>
                <span className="muted small">{fmtDateTime(s.analyzed_at)}</span>
              </div>
              <span className={'pill ' + (s.result ? (s.result.in_range ? 'pill-good' : 'pill-warn') : '')}>
                {s.result ? `${sci(s.result.value)} ${s.result.unit}` : 'Sin conteo'}
              </span>
              <Icon name="chevron" />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
