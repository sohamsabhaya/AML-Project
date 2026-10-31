import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ScanSearch, History, Settings, BarChart3 } from 'lucide-react'
import { Logo } from './Logo.jsx'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/analyze', label: 'New Analysis', icon: ScanSearch },
  { to: '/history', label: 'History', icon: History },
  { to: '/insights', label: 'Insights', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
]

/** Navy sidebar. On narrow screens it slides in; `open` and `onNavigate` are controlled by Layout. */
export function Sidebar({ open, onNavigate }) {
  return (
    <aside id="app-sidebar" className={`app-sidebar${open ? ' is-open' : ''}`}>
      <div className="brand">
        <Logo />
        <span>BrainScan AI</span>
      </div>
      <nav aria-label="Main navigation">
        <ul className="nav-list">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink to={to} end={end} className="nav-link" onClick={onNavigate}>
                <Icon size={19} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <p className="sidebar-note">Educational use only</p>
    </aside>
  )
}
