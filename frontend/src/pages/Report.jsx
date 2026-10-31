// Report page: printable A4-style report for /report/:id. Use "Print / Save as PDF" or the backend PDF link.
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Printer } from 'lucide-react'
import '../components/analysis/analysis.css'
import ClassBadge from '../components/analysis/ClassBadge.jsx'
import DemoBadge from '../components/analysis/DemoBadge.jsx'
import DownloadPdfButton from '../components/analysis/DownloadPdfButton.jsx'
import { getAnalysis } from '../lib/api.js'
import { CLASS_LABELS, CLASS_ORDER, DISCLAIMER, LIMITATIONS } from '../lib/classes.js'
import { formatDate, formatPercent } from '../lib/format.js'
import { useDemoMode } from '../lib/useDemoMode.js'

export default function Report() {
  const { id } = useParams()
  const demo = useDemoMode()
  const [state, setState] = useState({ status: 'loading', analysis: null, error: '' })
  const [heatmapBroken, setHeatmapBroken] = useState(false)

  useEffect(() => {
    let active = true
    setState({ status: 'loading', analysis: null, error: '' })
    setHeatmapBroken(false)
    getAnalysis(id)
      .then((analysis) => active && setState({ status: analysis ? 'ready' : 'missing', analysis, error: '' }))
      .catch((err) => active && setState({ status: 'error', analysis: null, error: err.message }))
    return () => {
      active = false
    }
  }, [id])

  const { status, analysis, error } = state

  if (status !== 'ready') {
    return (
      <div className="a-page">
        <div className="a-card a-empty" role={status === 'loading' ? 'status' : 'alert'}>
          <h2>{status === 'loading' ? 'Loading report...' : status === 'missing' ? 'Report not found' : 'Could not load report'}</h2>
          {status === 'missing' && <p>There is no analysis with ID {id}.</p>}
          {status === 'error' && <p>{error}</p>}
          {status !== 'loading' && <Link to="/history" className="a-btn">Back to history</Link>}
        </div>
      </div>
    )
  }

  const showHeatmap = Boolean(analysis.heatmap_url) && !heatmapBroken

  return (
    <div className="a-page">
      <div className="a-report-actions a-no-print">
        <Link to={`/results/${analysis.id}`} className="a-btn"><ArrowLeft size={18} aria-hidden="true" /> Back to results</Link>
        <div className="a-row">
          <DemoBadge show={demo} />
          <button type="button" className="a-btn" onClick={() => window.print()}>
            <Printer size={18} aria-hidden="true" /> Print / Save as PDF
          </button>
          <DownloadPdfButton id={analysis.id} demo={demo} />
        </div>
      </div>

      <article className="a-sheet" aria-label="Analysis report">
        <header className="a-sheet__head">
          <div>
            <div className="a-sheet__brand">BrainScan AI</div>
            <h1>Brain MRI Analysis Report</h1>
          </div>
          <dl className="a-meta">
            <dt>Analysis ID</dt><dd><code>{analysis.id}</code></dd>
            <dt>Date</dt><dd>{formatDate(analysis.created_at)}</dd>
            <dt>Model</dt><dd>{analysis.model_version}</dd>
            <dt>File</dt><dd>{analysis.filename}</dd>
          </dl>
        </header>

        <section>
          <h2>Images</h2>
          <div className="a-sheet__images">
            <figure>
              <img src={analysis.image_url} alt={`Uploaded MRI ${analysis.filename}`} />
              <figcaption>Original MRI</figcaption>
            </figure>
            <figure>
              {showHeatmap ? (
                <img src={analysis.heatmap_url} alt="Grad-CAM heatmap overlay" onError={() => setHeatmapBroken(true)} />
              ) : (
                <div className="a-sheet__ph">No heatmap</div>
              )}
              <figcaption>Grad-CAM heatmap (explanatory only)</figcaption>
            </figure>
          </div>
        </section>

        <section>
          <h2>Prediction</h2>
          <p style={{ margin: '0 0 12px' }}>
            <ClassBadge cls={analysis.predicted_class} label={analysis.predicted_label} /> with a model confidence of{' '}
            <strong>{formatPercent(analysis.confidence)}</strong>.
          </p>
          <table className="a-table">
            <thead>
              <tr><th scope="col">Class</th><th scope="col">Probability</th></tr>
            </thead>
            <tbody>
              {CLASS_ORDER.map((cls) => (
                <tr key={cls}>
                  <td style={{ fontWeight: cls === analysis.predicted_class ? 700 : 400 }}>{CLASS_LABELS[cls]}</td>
                  <td style={{ fontWeight: cls === analysis.predicted_class ? 700 : 400 }}>{formatPercent(analysis.probabilities[cls])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2>Limitations</h2>
          <ul>
            {LIMITATIONS.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>

        <section>
          <h2>Disclaimer</h2>
          <p style={{ margin: 0, fontSize: '0.9rem' }}>{DISCLAIMER}</p>
        </section>
      </article>
    </div>
  )
}
