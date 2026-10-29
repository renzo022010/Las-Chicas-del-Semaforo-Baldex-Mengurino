import { Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { HealthContext, useApiHealth } from './health.js'
import { Icon } from './icons.jsx'
import Home from './pages/Home.jsx'
import Analyze from './pages/Analyze.jsx'
import Result from './pages/Result.jsx'

function Header() {
  const navigate = useNavigate()
  return (
    <header className="appbar">
      {/* Sin historial previo (enlace abierto directo) se vuelve al inicio en vez de salir de la app. */}
      <button className="appbar-back" onClick={() => (window.history.state?.idx > 0 ? navigate(-1) : navigate('/'))} aria-label="Volver"><Icon name="back" /></button>
      <img src="/unalm-escudo-blanco.png" alt="" className="appbar-crest" />
      <div className="appbar-text">
        <strong>UNALM</strong>
        <span>Laboratorio de Microbiología</span>
      </div>
    </header>
  )
}

export default function App() {
  const health = useApiHealth()
  const { pathname } = useLocation()
  const home = pathname === '/'
  return (
    <HealthContext.Provider value={health}>
      <div className={'shell' + (home ? ' is-home' : '')}>
        {!home && <Header />}
        <main className="content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analizar" element={<Analyze />} />
            <Route path="/resultado/:id" element={<Result />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </main>
      </div>
    </HealthContext.Provider>
  )
}
