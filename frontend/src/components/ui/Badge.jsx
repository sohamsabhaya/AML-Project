import './ui.css'

const LABELS = { glioma: 'Glioma', meningioma: 'Meningioma', notumor: 'No Tumor', pituitary: 'Pituitary Tumor' }

/**
 * Badge
 * Props: kind 'glioma'|'meningioma'|'notumor'|'pituitary'|'neutral' (default neutral), className,
 * children (text; defaults to the class display label when kind is a tumor class).
 */
export function Badge({ kind = 'neutral', className = '', children }) {
  const k = LABELS[kind] ? kind : 'neutral'
  return <span className={`badge badge--${k} ${className}`.trim()}>{children ?? LABELS[k] ?? kind}</span>
}
