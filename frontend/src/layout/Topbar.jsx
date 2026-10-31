import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Logo } from './Logo.jsx'
import { useProfile } from './prefs.js'

/** Top bar: menu button + brand on small screens, profile chip (display name from Settings) on the right. */
export function Topbar({ menuOpen, onMenuToggle }) {
  const name = useProfile()
  return (
    <header className="app-topbar">
      <button type="button" className="menu-btn" onClick={onMenuToggle} aria-expanded={menuOpen} aria-controls="app-sidebar" aria-label={menuOpen ? 'Close menu' : 'Open menu'}>
        {menuOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
      </button>
      <span className="topbar-brand"><Logo size={28} /> BrainScan AI</span>
      <Link to="/settings" className="profile-chip" aria-label={`Profile: ${name}. Open settings`}>
        <span className="avatar" aria-hidden="true">{name.charAt(0).toUpperCase()}</span>
        <span className="profile-name">{name}</span>
      </Link>
    </header>
  )
}
