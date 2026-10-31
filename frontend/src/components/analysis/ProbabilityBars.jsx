// ProbabilityBars - one horizontal bar per class, highest highlighted.
// Props: probabilities ({glioma, meningioma, notumor, pituitary} each 0..1), predicted (class key of the top class).
import './analysis.css'
import { CLASS_LABELS, CLASS_ORDER } from '../../lib/classes.js'
import { formatPercent } from '../../lib/format.js'

export default function ProbabilityBars({ probabilities, predicted }) {
  const rows = CLASS_ORDER.map((cls) => ({ cls, value: probabilities?.[cls] ?? 0 })).sort((a, b) => b.value - a.value)
  return (
    <ul className="a-bars" aria-label="Probability for each class">
      {rows.map(({ cls, value }) => (
        <li key={cls} data-top={cls === predicted}>
          <div className="a-bars__head">
            <span>{CLASS_LABELS[cls]}</span>
            <span>{formatPercent(value)}</span>
          </div>
          <div className="a-bars__track" aria-hidden="true">
            <div className="a-bars__fill" style={{ width: `${value * 100}%`, background: `var(--cls-${cls}-bar)` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}
