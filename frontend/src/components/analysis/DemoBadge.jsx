// DemoBadge - "Demo data" pill, rendered only when `show` is true.
// Props: show (boolean).
import './analysis.css'

export default function DemoBadge({ show }) {
  if (!show) return null
  return (
    <span className="a-badge a-badge--demo" title="The backend is not reachable, so sample data is shown.">
      Demo data
    </span>
  )
}
