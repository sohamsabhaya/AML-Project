// ConfidenceMeter - labelled horizontal meter with a percentage.
// Props: value (0..1), low? (boolean, switches to the warning colour).
import './analysis.css'
import { formatPercent } from '../../lib/format.js'

export default function ConfidenceMeter({ value, low = false }) {
  const percent = Math.round(value * 100)
  return (
    <div>
      <div className="a-meter__head">
        <span id="confidence-label">Confidence</span>
        <span className="a-meter__value">{formatPercent(value)}</span>
      </div>
      <div
        className="a-meter__track"
        role="meter"
        aria-labelledby="confidence-label"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${percent} percent`}
      >
        <div className={`a-meter__fill${low ? ' a-meter__fill--low' : ''}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}
