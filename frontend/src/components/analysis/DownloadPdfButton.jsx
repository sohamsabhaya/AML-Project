// DownloadPdfButton - link to the backend PDF report (or the printable report in demo mode).
// Props: id (analysis id), demo (boolean), small? (boolean).
import { Link } from 'react-router-dom'
import { Download } from 'lucide-react'
import './analysis.css'
import { reportUrl } from '../../lib/api.js'

export default function DownloadPdfButton({ id, demo, small = false }) {
  const className = `a-btn a-btn--primary${small ? ' a-btn--small' : ''}`
  const content = (
    <>
      <Download size={18} aria-hidden="true" /> Download PDF
    </>
  )
  return demo ? (
    <Link to={reportUrl(id)} className={className}>
      {content}
    </Link>
  ) : (
    <a href={reportUrl(id)} className={className} download>
      {content}
    </a>
  )
}
