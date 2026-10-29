import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useHealth } from '../health.js'
import { Icon } from '../icons.jsx'
import { fmtDateTime, loadRecent } from '../recent.js'

export function EngineStatus() {
  const h = useHealth()
  if (h.status === 'checking') return <span className="pill">Conectando con la API…</span>
  if (h.status === 'offline') return <span className="pill pill-bad">Servidor apagado: inicia INICIAR.cmd</span>
  if (h.status === 'denied') return <span className="pill pill-bad">Sin acceso: abre el link o QR de INICIAR.cmd</span>
  const hybrid = h.engines?.includes('hybrid')
  return (
    <span className={'pill ' + (hybrid ? 'pill-good' : 'pill-warn')} title={h.neural_error || ''}>
      {hybrid ? `Motor IA · ${h.device}` : 'Motor clásico (OpenCV)'}
    </span>
  )
}

export default function Home() {
  const [recent] = useState(loadRecent)
  return (
    <div className="home">
      <section className="splash">
        <div className="splash-brand">
          <img src="/unalm-escudo-blanco.png" alt="Escudo de la UNALM" className="crest" />
          <div>
            <strong className="splash-unalm">UNALM</strong>
            <span>Universidad Nacional Agraria La Molina</span>
          </div>
        </div>
        <span className="gold-rule" />
        <p className="splash-lab">Facultad de Ciencias<br />Laboratorio de Microbiología</p>
        <div className="petri" aria-hidden="true" />
        <span className="gold-rule short" />
        <h1>Conteo de Unidades Formadoras de Colonias (UFC)</h1>
        <p className="splash-sub">Tecnología al servicio de la microbiología</p>
        <Link className="btn btn-gold btn-wide" to="/analizar">Comenzar <Icon name="chevron" size={20} /></Link>
        <EngineStatus />
      </section>

      {recent.length > 0 && (
        <section className="recent">
          <h2>Últimos análisis</h2>
          <ul>
            {recent.map((r) => (
              <li key={r.id}>
                <Link to={`/resultado/${r.id}`} className="recent-row">
                  <span className="recent-count">{r.reviewed ?? r.count}</span>
                  <span className="recent-main">
                    <strong>{r.reviewed != null ? 'colonias (revisado)' : 'colonias detectadas'}</strong>
                    <span className="muted small">{fmtDateTime(r.at)} · {r.engine === 'hybrid' ? 'IA' : 'Clásico'}</span>
                  </span>
                  <Icon name="chevron" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
