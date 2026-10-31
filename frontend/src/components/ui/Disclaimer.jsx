import { Info } from 'lucide-react'
import { DISCLAIMER } from '../../lib/api.js'
import './ui.css'

/** Disclaimer. Props: className. Calm amber info banner showing the standard medical disclaimer text. */
export function Disclaimer({ className = '' }) {
  return (
    <aside className={`disclaimer ${className}`.trim()} role="note" aria-label="Medical disclaimer">
      <Info size={20} aria-hidden="true" />
      <p>{DISCLAIMER}</p>
    </aside>
  )
}
