// DisclaimerNote - the medical disclaimer in a calm info box. No props.
import { Info } from 'lucide-react'
import './analysis.css'
import { DISCLAIMER } from '../../lib/classes.js'

export default function DisclaimerNote() {
  return (
    <p className="a-disclaimer" role="note">
      <Info size={18} aria-hidden="true" />
      <span>{DISCLAIMER}</span>
    </p>
  )
}
