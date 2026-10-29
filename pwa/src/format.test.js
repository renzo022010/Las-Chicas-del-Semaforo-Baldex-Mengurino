import { describe, expect, it } from 'vitest'
import { dilutionLabel, sci } from './format.js'

describe('sci', () => {
  it('formats UFC values like the lab report', () => {
    expect(sci(28000)).toBe('2,8 × 10⁴')
    expect(sci(46000)).toBe('4,6 × 10⁴')
    expect(sci(99999)).toBe('1 × 10⁵')
    expect(sci(5)).toBe('5')
    expect(sci(0)).toBe('0')
    expect(sci(null)).toBe('—')
  })
  it('labels dilutions', () => {
    expect(dilutionLabel(3)).toBe('10⁻³')
  })
})
