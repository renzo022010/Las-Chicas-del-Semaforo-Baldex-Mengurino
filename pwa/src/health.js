import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api.js'

export const HealthContext = createContext({ status: 'checking' })
export const useHealth = () => useContext(HealthContext)

// Consulta /health cada 15 s para mostrar si la API local y el motor IA estan disponibles.
export function useApiHealth() {
  const [health, setHealth] = useState({ status: 'checking' })
  useEffect(() => {
    let alive = true
    const check = () => api.health()
      .then((h) => alive && setHealth({ status: 'ok', ...h }))
      .catch(() => alive && setHealth({ status: 'offline' }))
    check()
    const t = setInterval(check, 15000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  return health
}
