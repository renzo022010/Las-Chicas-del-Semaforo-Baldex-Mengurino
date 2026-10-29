import { useNavigate } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { useHealth } from '../health.js'
import { Icon } from '../icons.jsx'
import { saveRecent } from '../recent.js'

const fmtSize = (bytes) => (bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`)

export default function Analyze() {
  const navigate = useNavigate()
  const health = useHealth()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [engine, setEngine] = useState('auto')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const camRef = useRef(null)
  const galRef = useRef(null)
  const hybrid = health.engines?.includes('hybrid')
  const online = health.status === 'ok'

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  function pick(e) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    setError('')
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  async function analyze() {
    setBusy(true); setError('')
    try {
      const r = await api.analyze(file, engine)
      saveRecent({ id: r.analysis_id, count: r.count, engine: r.engine, at: new Date().toISOString() })
      navigate(`/resultado/${r.analysis_id}`)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="stack">
      <div>
        <h2 className="page-title">Registro fotográfico</h2>
        <p className="muted">Adjunta la imagen de la caja Petri analizada.</p>
      </div>

      <div className={'photo-frame' + (preview ? ' has-photo' : '')}>
        {preview ? <img src={preview} alt="Vista previa de la placa" /> : (
          <div className="photo-empty">
            <Icon name="dish" size={52} />
            <p>Foto desde arriba, con la placa completa, buena luz y fondo oscuro.</p>
          </div>
        )}
        {busy && <div className="photo-busy"><span className="spinner" /> Analizando la placa…</div>}
      </div>

      <div className="actions">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => camRef.current.click()}><Icon name="camera" size={20} /> Capturar</button>
        <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => galRef.current.click()}><Icon name="image" size={20} /> Galería</button>
      </div>
      <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={pick} />
      <input ref={galRef} type="file" accept="image/*" hidden onChange={pick} />

      {file && (
        <div className="file-card">
          <img src={preview} alt="" />
          <span><strong>{file.name}</strong><span className="muted small">{fmtSize(file.size)}</span></span>
        </div>
      )}

      {hybrid && (
        <div className="field">
          <span className="label">Motor de conteo</span>
          <div className="seg">
            <button type="button" aria-pressed={engine !== 'classic'} onClick={() => setEngine('auto')}>IA (más preciso)</button>
            <button type="button" aria-pressed={engine === 'classic'} onClick={() => setEngine('classic')}>Clásico</button>
          </div>
        </div>
      )}

      {!online && health.status !== 'checking' && <p className="alert">La API local está apagada. Inicia procesamiento/INICIAR_API.cmd.</p>}
      {error && <p className="alert" role="alert">{error}</p>}

      <button type="button" className="btn btn-primary btn-wide" disabled={!file || busy || !online} onClick={analyze}>
        {busy ? 'Analizando…' : 'Analizar placa'} <Icon name="chevron" size={20} />
      </button>
      <p className="muted small">La primera foto con IA tarda unos segundos más mientras el modelo se calienta.</p>
    </div>
  )
}
