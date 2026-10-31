import { Menu, X } from 'lucide-react'
import { Logo } from './Logo.jsx'

/** Minimal light top bar (used on smaller screens for mobile navigation). */
export function Topbar({ menuOpen, onMenuToggle }) {
  return (
    <header className="app-topbar">
      <button
        type="button"
        className="menu-btn"
        onClick={onMenuToggle}
        aria-expanded={menuOpen}
        aria-controls="app-sidebar"
        aria-label={menuOpen ? 'Close menu' : 'Open menu'}
      >
        {menuOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
      </button>
      <span className="topbar-brand">
        <Logo size={24} /> BrainScan
      </span>
    </header>
  )
}
