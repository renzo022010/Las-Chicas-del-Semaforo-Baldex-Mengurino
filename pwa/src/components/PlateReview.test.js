import { describe, expect, it } from 'vitest'
import { pointsFromResult, pointsFromReview, reviewStats } from './PlateReview.jsx'

const result = {
  detections: [
    { x: 10, y: 10, radius: 4, near_edge: false },
    { x: 20, y: 20, radius: 6, near_edge: true },
    { x: 30, y: 30, radius: 8, near_edge: false },
  ],
}

describe('plate review', () => {
  it('marks colonies near the plate edge for review', () => {
    expect(pointsFromResult(result).map((p) => p.kind)).toEqual(['auto', 'edge', 'auto'])
  })

  it('counts added and removed colonies against the automatic count', () => {
    const points = pointsFromResult(result).slice(1)
    points.push({ x: 1, y: 1, r: 5, kind: 'manual' }, { x: 2, y: 2, r: 5, kind: 'manual' })
    expect(reviewStats(points, 3)).toEqual({ total: 4, edge: 1, added: 2, removed: 1 })
  })

  it('restores a saved review with the typical colony radius', () => {
    const points = pointsFromReview({ centers: [{ x: 5, y: 5 }] }, result)
    expect(points).toEqual([{ x: 5, y: 5, r: 6, kind: 'auto' }])
  })
})
