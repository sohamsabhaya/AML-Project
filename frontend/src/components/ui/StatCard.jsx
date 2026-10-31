import './ui.css'

/** StatCard. Props: icon (lucide component), label (string), value (node), hint (string, optional), loading (bool). */
export function StatCard({ icon: Icon, label, value, hint, loading = false }) {
  return (
    <div className="card stat">
      {Icon && <span className="stat__icon"><Icon size={22} aria-hidden="true" /></span>}
      <div className="stat__text">
        <span className="stat__label">{label}</span>
        {loading ? <span className="skeleton" style={{ height: 28, width: 80 }} /> : <span className="stat__value">{value}</span>}
        {hint && <span className="muted stat__hint">{hint}</span>}
      </div>
    </div>
  )
}
