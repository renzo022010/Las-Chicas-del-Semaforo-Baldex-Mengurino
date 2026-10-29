import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { HealthContext, useApiHealth } from './health.js'
import { Icon } from './icons.jsx'
import Home from './pages/Home.jsx'
import Samples from './pages/Samples.jsx'
import Wizard from './pages/Wizard.jsx'

function Header() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const inner = pathname !== '/'
  return (
    <header className="appbar">
      {inner && (
        <button className="appbar-back" onClick={() => navigate(-1)} aria-label="Volver">
          <Icon name="back" />
        </button>
      )}
      <div className="brand">
        <span className="brand-mark" aria-hidden="true"><Icon name="dish" /></span>
        <div>
          <strong>UNALM</strong>
          <span>Laboratorio de Microbiología</span>
        </div>
      </div>
    </header>
  )
}

function BottomNav() {
  return (
    <nav className="bottomnav" aria-label="Secciones">
      <NavLink to="/" end><Icon name="home" /><span>Inicio</span></NavLink>
      <NavLink to="/muestras"><Icon name="flask" /><span>Muestras</span></NavLink>
      <NavLink to="/muestra/nueva/1"><Icon name="plus" /><span>Nueva</span></NavLink>
    </nav>
  )
}

export default function App() {
  const health = useApiHealth()
  return (
    <HealthContext.Provider value={health}>
      <div className="shell">
        <Header />
        <main className="content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/muestras" element={<Samples />} />
            <Route path="/muestra/:id/:step" element={<Wizard />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </main>
        <BottomNav />
      </div>
    </HealthContext.Provider>
  )
}
