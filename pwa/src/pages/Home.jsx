import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useHealth } from '../health.js'
import { Icon } from '../icons.jsx'
import { fmtDateTime, sci } from '../format.js'

export const STEPS = [
  { n: 1, title: 'Registro de trazabilidad', text: 'Datos de la muestra para su análisis.', icon: 'doc', tone: 'green' },
  { n: 2, title: 'Diluciones y conteo de UFC', text: 'Diluciones, volumen sembrado y colonias contadas.', icon: 'calc', tone: 'gold' },
  { n: 3, title: 'Registro fotográfico', text: 'Foto de la placa y conteo asistido.', icon: 'camera', tone: 'blue' },
  { n: 4, title: 'Generar y exportar reporte', text: 'Revisa la información y genera el PDF.', icon: 'pdf', tone: 'purple' },
]

export function EngineStatus() {
  const h = useHealth()
  if (h.status === 'checking') return <span className="pill">Conectando con la API…</span>
  if (h.status === 'offline') return <span className="pill pill-bad">API local apagada</span>
  const hybrid = h.engines?.includes('hybrid')
  return (
    <span className={'pill ' + (hybrid ? 'pill-good' : 'pill-warn')} title={h.neural_error || h.device || ''}>
      {hybrid ? `Motor IA activo · ${h.device}` : 'Motor clásico (OpenCV)'}
    </span>
  )
}

export default function Home() {
  const [last, setLast] = useState(null)
  useEffect(() => { api.samples().then((s) => setLast(s[0] || null)).catch(() => setLast(null)) }, [])
  const stepLink = (n) => (n === 1 || !last ? '/muestra/nueva/1' : `/muestra/${last.id}/${n}`)

  return (
    <div className="stack">
      <section className="hero">
        <div className="hero-text">
          <span className="hero-rule" />
          <p className="hero-kicker">Conteo de</p>
          <h1>Unidades Formadoras de Colonias (UFC)</h1>
          <p className="hero-sub">Tecnología al servicio de la microbiología</p>
          <Link className="btn btn-gold" to="/muestra/nueva/1">Nueva muestra <Icon name="chevron" size={18} /></Link>
        </div>
        <div className="petri" aria-hidden="true" />
      </section>

      <div className="row-between">
        <h2 className="section-title"><Icon name="flask" /> Flujo de trabajo</h2>
        <EngineStatus />
      </div>
      <p className="muted">Sigue los pasos para registrar, analizar y obtener el resultado final.</p>

      <div className="steps">
        {STEPS.map((s) => (
          <Link key={s.n} to={stepLink(s.n)} className={`step-card tone-${s.tone}`}>
            <span className="step-num">{s.n}</span>
            <span className="step-icon"><Icon name={s.icon} size={28} /></span>
            <span className="step-body"><strong>{s.title}</strong><span>{s.text}</span></span>
            <Icon name="chevron" />
          </Link>
        ))}
      </div>

      {last && (
        <Link to={`/muestra/${last.id}/4`} className="last-card">
          <div>
            <span className="label">Última muestra analizada</span>
            <strong>{last.code}</strong>
          </div>
          <div>
            <span className="label">Fecha de análisis</span>
            <span>{fmtDateTime(last.analyzed_at)}</span>
          </div>
          <span className={'pill ' + (last.result ? 'pill-good' : '')}>
            {last.result ? `${sci(last.result.value)} ${last.result.unit}` : 'Sin conteo'}
          </span>
        </Link>
      )}
    </div>
  )
}
