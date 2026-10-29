import { useMemo, useRef, useState } from 'react'
import { Icon } from '../icons.jsx'

// Puntos en pixeles de la foto original (mismo sistema que devuelve la API).
export function pointsFromResult(result) {
  return (result.detections || []).map((d) => ({ x: d.x, y: d.y, r: d.radius || 0, kind: d.near_edge ? 'edge' : 'auto' }))
}

export default function PlateReview({ imageUrl, size, points, onChange }) {
  const svgRef = useRef(null)
  const [zoom, setZoom] = useState(1)
  const [history, setHistory] = useState([])
  const { width: W, height: H } = size
  const minR = Math.max(W, H) * 0.006
  const typicalR = useMemo(() => {
    const radii = points.map((p) => p.r).filter(Boolean).sort((a, b) => a - b)
    return radii.length ? radii[Math.floor(radii.length / 2)] : minR * 2
  }, [points, minR])

  const commit = (next) => { setHistory((h) => [...h.slice(-49), points]); onChange(next) }

  function handleClick(e) {
    const rect = svgRef.current.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * W
    const y = ((e.clientY - rect.top) / rect.height) * H
    let hit = -1, best = Infinity
    points.forEach((p, i) => {
      const d = Math.hypot(p.x - x, p.y - y)
      if (d < Math.max(p.r * 1.3, minR * 2.5) && d < best) { best = d; hit = i }
    })
    if (hit >= 0) commit(points.filter((_, i) => i !== hit))
    else if (x >= 0 && y >= 0 && x < W && y < H) commit([...points, { x, y, r: typicalR, kind: 'manual' }])
  }

  function undo() {
    if (!history.length) return
    onChange(history[history.length - 1])
    setHistory((h) => h.slice(0, -1))
  }

  const stroke = Math.max(W, H) * 0.0025
  return (
    <div className="review">
      <div className="review-tools">
        <span className="muted small">Toca un punto para quitarlo. Toca un espacio vacío para añadir una colonia.</span>
        <div className="seg">
          {[1, 2, 3].map((z) => (
            <button key={z} type="button" aria-pressed={zoom === z} onClick={() => setZoom(z)}>{z}×</button>
          ))}
          <button type="button" onClick={undo} disabled={!history.length} aria-label="Deshacer"><Icon name="undo" size={18} /></button>
        </div>
      </div>
      <div className="review-scroll">
        <div className="review-canvas" style={{ width: `${zoom * 100}%` }}>
          <img src={imageUrl} alt="Placa analizada" draggable="false" />
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} onClick={handleClick} role="img" aria-label={`${points.length} colonias marcadas`}>
            {points.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r={Math.max(p.r, minR)} className={`dot dot-${p.kind}`} strokeWidth={stroke} />
            ))}
          </svg>
        </div>
      </div>
      <div className="legend small">
        <span><i className="dot-key dot-auto" /> Detectada</span>
        <span><i className="dot-key dot-edge" /> Cerca del borde (revisar)</span>
        <span><i className="dot-key dot-manual" /> Añadida a mano</span>
      </div>
    </div>
  )
}
