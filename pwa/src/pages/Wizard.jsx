import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { useHealth } from '../health.js'
import { Icon } from '../icons.jsx'
import { dilutionLabel, fmtDateTime, nowLocalInput, sci } from '../format.js'
import PlateReview, { pointsFromResult } from '../components/PlateReview.jsx'


const SAMPLE_TYPES = ['Suelo', 'Rizósfera', 'Tejido vegetal', 'Agua', 'Alimento', 'Inóculo / cultivo', 'Otro']
const STEP_NAMES = ['Trazabilidad', 'Diluciones y conteo', 'Imagen de placa', 'Reporte']
const PLATES = [['plate_a', 'A'], ['plate_b', 'B']]

function readPref(key, fallback) {
  try { return localStorage.getItem(key) || fallback } catch { return fallback }
}
function writePref(key, value) {
  try { localStorage.setItem(key, value) } catch { /* almacenamiento bloqueado */ }
}

function newSample() {
  return {
    analyzed_at: nowLocalInput(), sample_type: 'Suelo', responsible: readPref('ufc-responsable', ''),
    origin: '', notes: '', unit: 'g', count_min: 30, count_max: 300,
    dilutions: [1, 2, 3].map((exponent) => ({ exponent, volume_ml: 0.1, plate_a: { count: null }, plate_b: { count: null } })),
  }
}

function Stepper({ current, onGo, enabled }) {
  return (
    <ol className="stepper">
      {STEP_NAMES.map((name, i) => (
        <li key={name} className={i + 1 === current ? 'is-current' : i + 1 < current ? 'is-done' : ''}>
          <button type="button" onClick={() => onGo(i + 1)} disabled={!enabled}>
            <span className="stepper-num">{i + 1}</span>
            <span className="stepper-name">{name}</span>
          </button>
        </li>
      ))}
    </ol>
  )
}

export default function Wizard() {
  const { id, step } = useParams()
  const navigate = useNavigate()
  const isNew = id === 'nueva'
  const n = Math.min(4, Math.max(1, Number(step) || 1))
  const [sample, setSample] = useState(null)
  const [error, setError] = useState('')
  const [saveState, setSaveState] = useState('idle')
  const latest = useRef(null)
  const timer = useRef()
  const chain = useRef(Promise.resolve())

  useEffect(() => {
    setError('')
    if (isNew) { const s = newSample(); latest.current = s; setSample(s); return }
    setSample(null)
    api.sample(id).then((s) => { latest.current = s; setSample(s) }).catch((e) => setError(e.message))
  }, [id, isNew])

  // Guarda la ultima version; las escrituras van en fila para no pisarse.
  const persist = useCallback(() => {
    clearTimeout(timer.current)
    const s = latest.current
    if (!s?.id) return chain.current
    setSaveState('saving')
    chain.current = chain.current
      .then(() => api.update(s.id, latest.current))
      .then((saved) => {
        latest.current = { ...latest.current, result: saved.result, updated_at: saved.updated_at }
        setSample(latest.current)
        setSaveState('saved'); setError('')
      })
      .catch((e) => { setSaveState('error'); setError(e.message) })
    return chain.current
  }, [])

  useEffect(() => () => { clearTimeout(timer.current); if (latest.current?.id) persist() }, [persist])

  const change = useCallback((patch, { now = false } = {}) => {
    latest.current = { ...latest.current, ...patch }
    setSample(latest.current)
    if (latest.current.id) {
      clearTimeout(timer.current)
      timer.current = setTimeout(persist, now ? 0 : 600)
    }
  }, [persist])

  const goTo = async (target) => {
    if (isNew) return
    await persist()
    navigate(`/muestra/${id}/${target}`)
  }

  if (isNew && n !== 1) return <Navigate to="/muestra/nueva/1" replace />
  if (error && !sample) return <div className="stack"><p className="alert">{error}</p></div>
  if (!sample) return <p className="muted">Cargando muestra…</p>

  const props = { sample, change, goTo, setError, persist }
  return (
    <div className="stack wizard">
      <Stepper current={n} onGo={goTo} enabled={!isNew} />
      <div className="save-line small">
        {sample.code && <strong>{sample.code}</strong>}
        <span className="muted">
          {saveState === 'saving' ? 'Guardando…' : saveState === 'saved' ? 'Guardado' : saveState === 'error' ? 'No se guardó' : ''}
        </span>
      </div>
      {error && <p className="alert" role="alert">{error}</p>}
      {n === 1 && <StepTrace {...props} isNew={isNew} onCreated={(s) => { latest.current = s; navigate(`/muestra/${s.id}/2`, { replace: true }) }} />}
      {n === 2 && <StepDilutions {...props} />}
      {n === 3 && <StepPhoto {...props} />}
      {n === 4 && <StepReport {...props} />}
    </div>
  )
}

function StepHeader({ n, title, text, icon }) {
  return (
    <div className="step-head">
      <span className="step-head-icon"><Icon name={icon} size={26} /></span>
      <div><h2>{n}. {title}</h2><p className="muted">{text}</p></div>
    </div>
  )
}

function StepTrace({ sample, change, goTo, isNew, onCreated, setError }) {
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => change({ [k]: e.target.value })

  async function next(e) {
    e.preventDefault()
    if (!sample.responsible.trim()) { setError('Indica el responsable del análisis.'); return }
    writePref('ufc-responsable', sample.responsible.trim())
    if (!isNew) { goTo(2); return }
    setBusy(true)
    try { onCreated(await api.create(sample)) } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <form className="card stack" onSubmit={next}>
      <StepHeader n={1} title="Registro de trazabilidad" icon="doc"
        text="Datos de la muestra para su trazabilidad durante todo el proceso." />
      <div className="field">
        <label htmlFor="code">Código de muestra</label>
        <input id="code" value={sample.code || 'Se asigna al guardar'} readOnly className="readonly" />
      </div>
      <div className="field">
        <label htmlFor="analyzed_at">Fecha y hora de análisis</label>
        <input id="analyzed_at" type="datetime-local" required value={String(sample.analyzed_at).slice(0, 16)} onChange={set('analyzed_at')} />
      </div>
      <div className="field">
        <label htmlFor="sample_type">Tipo de muestra</label>
        <select id="sample_type" value={sample.sample_type}
          onChange={(e) => change({ sample_type: e.target.value, unit: ['Suelo', 'Rizósfera', 'Tejido vegetal', 'Alimento'].includes(e.target.value) ? 'g' : 'mL' })}>
          {SAMPLE_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      <div className="field">
        <label htmlFor="origin">Cultivo, parcela o procedencia <span className="muted">(opcional)</span></label>
        <input id="origin" maxLength={120} value={sample.origin} onChange={set('origin')} placeholder="ej. Arándano, parcela 3" />
      </div>
      <div className="field">
        <label htmlFor="responsible">Responsable del análisis</label>
        <input id="responsible" required maxLength={80} value={sample.responsible} onChange={set('responsible')} placeholder="Nombre y apellido" />
      </div>
      <p className="note"><Icon name="flask" size={18} /> La información registrada queda vinculada a las fotos, el conteo y el reporte de la muestra.</p>
      <div className="actions">
        <button className="btn btn-primary btn-wide" disabled={busy}>{busy ? 'Guardando…' : 'Siguiente'} <Icon name="chevron" size={18} /></button>
      </div>
    </form>
  )
}

function ResultCard({ result, unit, saving }) {
  if (!result) return <div className="result-card is-empty"><Icon name="calc" size={28} /><p>Ingresa los conteos de al menos una placa para calcular UFC/{unit}.</p></div>
  return (
    <div className={'result-card' + (saving ? ' is-stale' : '')}>
      <Icon name="calc" size={30} />
      <div className="result-main">
        <span className="label">Resultado final</span>
        <strong className="result-value">{sci(result.value)} <small>{result.unit}</small></strong>
        {result.dilutions_used.length > 0 && (
          <span className={'pill ' + (result.in_range ? 'pill-good' : 'pill-warn')}>
            Dilución {result.dilutions_used.map(dilutionLabel).join(' y ')}{result.in_range ? '' : ' · estimado'}
          </span>
        )}
        {result.warnings.map((w) => <p key={w} className="warn small">{w}</p>)}
        <p className="muted small">Fórmula: UFC/{unit} = (colonias promedio × 1/dilución) ÷ volumen sembrado (mL)</p>
      </div>
    </div>
  )
}

function StepDilutions({ sample, change, goTo, persist }) {
  const navigate = useNavigate()
  const rows = sample.dilutions
  const setRow = (i, patch) => change({ dilutions: rows.map((d, j) => (j === i ? { ...d, ...patch } : d)) })
  const setCount = (i, key, value) => {
    const count = value === '' ? null : Math.max(0, Math.floor(Number(value)))
    setRow(i, { [key]: { ...rows[i][key], count: Number.isFinite(count) ? count : null } })
  }
  const addRow = () => {
    const last = rows[rows.length - 1]
    change({ dilutions: [...rows, { exponent: last ? Math.min(12, last.exponent + 1) : 1, volume_ml: last?.volume_ml ?? 0.1, plate_a: { count: null }, plate_b: { count: null } }] })
  }
  const photo = async (i, key) => { await persist(); navigate(`/muestra/${sample.id}/3?d=${i}&p=${key}`) }

  return (
    <div className="card stack">
      <StepHeader n={2} title="Diluciones y conteo de UFC" icon="calc"
        text="Registra las diluciones, el volumen sembrado y las colonias contadas. Usa la cámara para contar con la foto." />
      <div className="table-wrap">
        <table className="dil-table">
          <thead>
            <tr><th>Dilución</th><th>Volumen<br />(mL)</th><th>Placa A</th><th>Placa B</th><th><span className="sr-only">Acciones</span></th></tr>
          </thead>
          <tbody>
            {rows.map((d, i) => (
              <tr key={i}>
                <td>
                  <select aria-label="Dilución" value={d.exponent} onChange={(e) => setRow(i, { exponent: Number(e.target.value) })}>
                    {Array.from({ length: 10 }, (_, k) => <option key={k} value={k}>{dilutionLabel(k)}</option>)}
                  </select>
                </td>
                <td><input aria-label="Volumen sembrado en mL" type="number" inputMode="decimal" min="0.001" max="10" step="0.01" value={d.volume_ml}
                  onChange={(e) => setRow(i, { volume_ml: Number(e.target.value) || 0 })} /></td>
                {PLATES.map(([key, label]) => (
                  <td key={key}>
                    <div className="plate-cell">
                      <input aria-label={`Colonias placa ${label}`} type="number" inputMode="numeric" min="0" step="1" value={d[key].count ?? ''}
                        onChange={(e) => setCount(i, key, e.target.value)} />
                      <button type="button" className={'icon-btn' + (d[key].analysis_id ? ' has-photo' : '')} onClick={() => photo(i, key)}
                        aria-label={`Contar placa ${label} con foto`} title={d[key].analysis_id ? 'Tiene foto vinculada' : 'Contar con foto'}>
                        <Icon name="camera" size={16} />
                      </button>
                    </div>
                  </td>
                ))}
                <td><button type="button" className="icon-btn" onClick={() => change({ dilutions: rows.filter((_, j) => j !== i) })} aria-label="Quitar dilución"><Icon name="trash" size={18} /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button type="button" className="btn btn-ghost" onClick={addRow} disabled={rows.length >= 12}>Añadir dilución</button>

      <div className="row-wrap">
        <div className="field compact">
          <label htmlFor="count_min">Rango contable</label>
          <div className="range-inputs">
            <input id="count_min" type="number" min="0" value={sample.count_min} onChange={(e) => change({ count_min: Number(e.target.value) })} />
            <span>a</span>
            <input aria-label="Máximo del rango contable" type="number" min="1" value={sample.count_max} onChange={(e) => change({ count_max: Number(e.target.value) })} />
            <span>colonias</span>
          </div>
        </div>
        <div className="field compact">
          <span className="label">Expresar en</span>
          <div className="seg">
            {['g', 'mL'].map((u) => <button key={u} type="button" aria-pressed={sample.unit === u} onClick={() => change({ unit: u })}>UFC/{u}</button>)}
          </div>
        </div>
      </div>

      <ResultCard result={sample.result} unit={sample.unit} />
      <div className="actions">
        <button type="button" className="btn btn-ghost" onClick={() => goTo(1)}>Anterior</button>
        <button type="button" className="btn btn-primary" onClick={() => goTo(3)}>Siguiente <Icon name="chevron" size={18} /></button>
      </div>
    </div>
  )
}

function StepPhoto({ sample, change, goTo, setError, persist }) {
  const health = useHealth()
  const [params] = useSearchParams()
  const rows = sample.dilutions
  const firstEmpty = () => {
    for (let i = 0; i < rows.length; i++) for (const [k] of PLATES) if (rows[i][k].count == null) return `${i}:${k}`
    return rows.length ? '0:plate_a' : ''
  }
  const [target, setTarget] = useState(params.get('d') != null ? `${params.get('d')}:${params.get('p')}` : firstEmpty())
  const [engine, setEngine] = useState('auto')
  const [busy, setBusy] = useState(false)
  const [analysis, setAnalysis] = useState(null) // { result, points, edited }
  const camRef = useRef(null)
  const galRef = useRef(null)
  const hybrid = health.engines?.includes('hybrid')

  const [ti, tk] = target.split(':')
  const row = rows[Number(ti)]
  const targetLabel = row ? `${dilutionLabel(row.exponent)} · Placa ${tk === 'plate_a' ? 'A' : 'B'}` : ''

  async function onFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setBusy(true); setError(''); setAnalysis(null)
    try {
      const result = await api.analyze(file, engine)
      setAnalysis({ result, points: pointsFromResult(result), edited: false })
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function openLinked(analysisId, key) {
    setBusy(true); setError('')
    try {
      const [result, review] = await Promise.all([api.result(analysisId), api.savedReview(analysisId)])
      result.analysis_id = analysisId
      const points = review ? review.centers.map((c) => ({ ...c, r: 0, kind: 'auto' })) : pointsFromResult(result)
      setTarget(key); setAnalysis({ result, points, edited: false, reviewed: !!review })
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function accept() {
    if (!row) return
    const { result, points, edited } = analysis
    setBusy(true)
    try {
      if (edited) await api.review(result.analysis_id, points.map(({ x, y }) => ({ x, y })), 'Revisado en la PWA')
      const dilutions = rows.map((d, j) => (j === Number(ti) ? { ...d, [tk]: { count: points.length, analysis_id: result.analysis_id } } : d))
      change({ dilutions }, { now: true })
      await persist()
      setAnalysis(null)
      goTo(2)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  const linked = rows.flatMap((d, i) => PLATES.filter(([k]) => d[k].analysis_id).map(([k, l]) => ({ key: `${i}:${k}`, id: d[k].analysis_id, count: d[k].count, label: `${dilutionLabel(d.exponent)} · Placa ${l}` })))

  if (analysis) {
    const { result, points } = analysis
    const auto = result.detections?.length ?? 0
    const url = api.fileUrl(result.analysis_id, 'foto_original.jpg')
    return (
      <div className="card stack">
        <div className="analysis-head">
          <div>
            <span className="label">Colonias marcadas</span>
            <strong className="big-count">{points.length}</strong>
          </div>
          <dl className="mini-stats">
            <div><dt>Automático</dt><dd>{auto}</dd></div>
            <div><dt>Motor</dt><dd>{result.method?.includes('sam2') ? 'IA (híbrido)' : 'Clásico'}</dd></div>
            <div><dt>Destino</dt><dd>{targetLabel}</dd></div>
          </dl>
        </div>
        <PlateReview imageUrl={url} size={result.image_size} points={points}
          onChange={(p) => setAnalysis((a) => ({ ...a, points: p, edited: true }))} />
        {(result.warnings || []).slice(0, 2).map((w) => <p key={w} className="warn small">{w}</p>)}
        <div className="actions">
          <button type="button" className="btn btn-ghost" onClick={() => setAnalysis(null)} disabled={busy}>Descartar</button>
          <button type="button" className="btn btn-primary" onClick={accept} disabled={busy || !row}>
            {busy ? 'Guardando…' : `Usar ${points.length} en ${targetLabel}`}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="card stack">
      <StepHeader n={3} title="Registro fotográfico" icon="camera" text="Toma o carga la foto de la caja Petri. El conteo automático se revisa antes de usarlo." />
      {!rows.length ? <p className="alert">Primero añade al menos una dilución en el paso 2.</p> : (
        <>
          <div className="field">
            <label htmlFor="target">Placa que vas a fotografiar</label>
            <select id="target" value={target} onChange={(e) => setTarget(e.target.value)}>
              {rows.flatMap((d, i) => PLATES.map(([k, l]) => (
                <option key={`${i}:${k}`} value={`${i}:${k}`}>
                  {dilutionLabel(d.exponent)} · Placa {l}{d[k].count != null ? ` (${d[k].count} colonias)` : ''}
                </option>
              )))}
            </select>
          </div>
          {hybrid && (
            <div className="field">
              <span className="label">Motor de conteo</span>
              <div className="seg">
                <button type="button" aria-pressed={engine !== 'classic'} onClick={() => setEngine('auto')}>IA (más preciso)</button>
                <button type="button" aria-pressed={engine === 'classic'} onClick={() => setEngine('classic')}>Clásico</button>
              </div>
            </div>
          )}
          <div className="photo-drop">
            {busy ? <p><span className="spinner" /> Analizando la placa… la primera foto con IA puede tardar unos segundos.</p> : (
              <>
                <Icon name="dish" size={44} />
                <p className="muted small">Foto desde arriba, placa completa, buena luz y fondo oscuro.</p>
              </>
            )}
          </div>
          <div className="actions">
            <button type="button" className="btn btn-primary" disabled={busy || health.status !== 'ok'} onClick={() => camRef.current.click()}><Icon name="camera" size={18} /> Capturar</button>
            <button type="button" className="btn btn-ghost" disabled={busy || health.status !== 'ok'} onClick={() => galRef.current.click()}><Icon name="image" size={18} /> Galería</button>
          </div>
          <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={onFile} />
          <input ref={galRef} type="file" accept="image/*" hidden onChange={onFile} />
        </>
      )}
      {linked.length > 0 && (
        <div className="stack-sm">
          <span className="label">Fotos vinculadas</span>
          {linked.map((l) => (
            <button type="button" key={l.key} className="linked" onClick={() => openLinked(l.id, l.key)} disabled={busy}>
              <img src={api.fileUrl(l.id, 'foto_conteo.jpg')} alt="" />
              <span><strong>{l.label}</strong><span className="muted small">{l.count} colonias · tocar para revisar</span></span>
              <Icon name="chevron" />
            </button>
          ))}
        </div>
      )}
      <div className="actions">
        <button type="button" className="btn btn-ghost" onClick={() => goTo(2)}>Anterior</button>
        <button type="button" className="btn btn-primary" onClick={() => goTo(4)}>Siguiente <Icon name="chevron" size={18} /></button>
      </div>
    </div>
  )
}

function StepReport({ sample, change, goTo, setError }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const r = sample.result
  const photos = sample.dilutions.flatMap((d) => PLATES.filter(([k]) => d[k].analysis_id).map(([k, l]) => ({ id: d[k].analysis_id, label: `${dilutionLabel(d.exponent)} · Placa ${l}`, count: d[k].count })))

  async function pdf() {
    setBusy(true); setError('')
    try { const { buildReport } = await import('../report.js'); await buildReport(sample, photos) } catch (err) { setError('No se pudo generar el PDF: ' + err.message) } finally { setBusy(false) }
  }
  async function remove() {
    try { await api.remove(sample.id); navigate('/muestras', { replace: true }) } catch (err) { setError(err.message) }
  }

  return (
    <div className="card stack">
      <StepHeader n={4} title="Generar y exportar reporte" icon="pdf" text="Revisa la información antes de generar el PDF." />
      <section className="summary">
        <h3>Resumen de la muestra</h3>
        <dl>
          <div><dt>Código de muestra</dt><dd>{sample.code}</dd></div>
          <div><dt>Tipo de muestra</dt><dd>{sample.sample_type}</dd></div>
          {sample.origin && <div><dt>Procedencia</dt><dd>{sample.origin}</dd></div>}
          <div><dt>Fecha y hora</dt><dd>{fmtDateTime(sample.analyzed_at)}</dd></div>
          <div><dt>Responsable</dt><dd>{sample.responsible}</dd></div>
        </dl>
      </section>
      <ResultCard result={r} unit={sample.unit} />
      {photos.length > 0 && (
        <section className="summary">
          <h3>Imágenes de placa</h3>
          <div className="thumbs">
            {photos.map((p) => (
              <figure key={p.id}>
                <img src={api.fileUrl(p.id, 'foto_conteo.jpg')} alt={`Placa ${p.label}`} />
                <figcaption className="small">{p.label} · {p.count}</figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}
      <div className="field">
        <label htmlFor="notes">Observaciones</label>
        <textarea id="notes" rows={3} maxLength={2000} value={sample.notes} onChange={(e) => change({ notes: e.target.value })} placeholder="Medio de cultivo, condiciones de incubación, morfología observada…" />
      </div>
      <button type="button" className="btn btn-primary btn-wide" onClick={pdf} disabled={busy}>
        <Icon name="pdf" size={20} /> {busy ? 'Generando…' : 'Generar y exportar reporte PDF'}
      </button>
      <div className="actions">
        <button type="button" className="btn btn-ghost" onClick={() => goTo(3)}>Anterior</button>
        {confirming ? (
          <span className="confirm small">¿Eliminar {sample.code}?
            <button type="button" className="btn btn-danger btn-small" onClick={remove}>Eliminar</button>
            <button type="button" className="btn btn-ghost btn-small" onClick={() => setConfirming(false)}>Cancelar</button>
          </span>
        ) : <button type="button" className="btn btn-text-danger" onClick={() => setConfirming(true)}>Eliminar muestra</button>}
      </div>
    </div>
  )
}
