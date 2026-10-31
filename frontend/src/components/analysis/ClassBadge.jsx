// ClassBadge - coloured pill for a predicted class.
// Props: cls ('glioma'|'meningioma'|'notumor'|'pituitary'), label? (defaults to display label), large? (boolean).
import './analysis.css'
import { CLASS_LABELS, CLASS_TONES } from '../../lib/classes.js'

export default function ClassBadge({ cls, label, large = false }) {
  const known = Boolean(CLASS_TONES[cls])
  const background = known ? `var(--cls-${cls}-bg)` : 'var(--color-surface-2)'
  const color = known ? `var(--cls-${cls}-text)` : 'var(--color-text)'
  return (
    <span className={`a-badge${large ? ' a-badge--lg' : ''}`} style={{ background, color }}>
      {label || CLASS_LABELS[cls] || cls}
    </span>
  )
}
