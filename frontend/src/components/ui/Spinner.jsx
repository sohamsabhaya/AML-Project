import './ui.css'

/** Spinner. Props: size (px, default 20), label (screen-reader text, default 'Loading'). */
export function Spinner({ size = 20, label = 'Loading' }) {
  return (
    <span className="spinner" style={{ width: size, height: size }} role="status">
      <span className="sr-only">{label}</span>
    </span>
  )
}
