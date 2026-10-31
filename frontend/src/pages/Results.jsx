// Results page: shows one analysis (image, heatmap, prediction, probabilities) for /results/:id.
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, FileText, Plus } from 'lucide-react'
import '../components/analysis/analysis.css'
import ClassBadge from '../components/analysis/ClassBadge.jsx'
import ConfidenceMeter from '../components/analysis/ConfidenceMeter.jsx'
import DemoBadge from '../components/analysis/DemoBadge.jsx'
import DownloadPdfButton from '../components/analysis/DownloadPdfButton.jsx'
import ProbabilityBars from '../components/analysis/ProbabilityBars.jsx'
import { getAnalysis } from '../lib/api.js'
import { CLASS_EXPLANATIONS, CLASS_LABELS, LOW_CONFIDENCE, MAX_ENTROPY } from '../lib/classes.js'
import { formatDate, formatPercent } from '../lib/format.js'
import { useDemoMode } from '../lib/useDemoMode.js'

function Viewer({ analysis, view, onHeatmapError }) {
  const original = (
    <figure>
      <img src={analysis.image_url} alt={`Uploaded MRI ${analysis.filename}`} />
      {view === 'side' && <figcaption>Original</figcaption>}
    </figure>
  )
  const overlay = (
    <figure>
      <img src={analysis.heatmap_url} alt="Grad-CAM heatmap overlay" onError={onHeatmapError} />
      {view === 'side' && <figcaption>Heatmap</figcaption>}
    </figure>
  )
  return (
    <div className={`a-viewer${view === 'side' ? ' a-viewer--side' : ''}`}>
      {view === 'original' && original}
      {view === 'heatmap' && overlay}
      {view === 'side' && (
        <>
          {original}
          {overlay}
        </>
      )}
    </div>
  )
}

export default function Results() {
  const { id } = useParams()
  const demo = useDemoMode()
  const [state, setState] = useState({ status: 'loading', analysis: null, error: '' })
  const [view, setView] = useState('heatmap')
  const [heatmapBroken, setHeatmapBroken] = useState(false)

  const load = useCallback(() => {
    let active = true
    setState({ status: 'loading', analysis: null, error: '' })
    setHeatmapBroken(false)
    getAnalysis(id)
      .then((analysis) => {
        if (!active) return
        setState(analysis ? { status: 'ready', analysis, error: '' } : { status: 'missing', analysis: null, error: '' })
        setView(analysis?.heatmap_url ? 'heatmap' : 'original')
      })
      .catch((err) => active && setState({ status: 'error', analysis: null, error: err.message }))
    return () => {
      active = false
    }
  }, [id])

  useEffect(() => load(), [load])

  const { status, analysis, error } = state
  const hasHeatmap = Boolean(analysis?.heatmap_url) && !heatmapBroken
  const activeView = hasHeatmap ? view : 'original'
  const threshold = analysis?.confidence_threshold ?? LOW_CONFIDENCE
  const lowConfidence = analysis ? analysis.low_confidence ?? analysis.confidence < threshold : false
  const top2 = Array.isArray(analysis?.top2) ? analysis.top2 : []
  const comparison = analysis?.comparison

  return (
    <div className="a-page">
      <header className="a-header">
        <div>
          <h1>Analysis Results</h1>
          <p>Review the model output together with its limitations.</p>
        </div>
        <DemoBadge show={demo} />
      </header>

      {status === 'loading' && (
        <div className="a-results" aria-busy="true" aria-label="Loading analysis">
          <div className="a-card"><span className="a-skeleton" style={{ aspectRatio: '1', height: 'auto' }} /></div>
          <div className="a-card a-stack">
            <span className="a-skeleton" style={{ height: 36, width: '60%' }} />
            <span className="a-skeleton" />
            <span className="a-skeleton" />
            <span className="a-skeleton" />
          </div>
        </div>
      )}

      {status === 'missing' && (
        <div className="a-card a-empty">
          <FileText size={40} aria-hidden="true" />
          <h2>Analysis not found</h2>
          <p>We could not find an analysis with ID {id}. It may have been deleted.</p>
          <div className="a-row">
            <Link to="/history" className="a-btn">Go to history</Link>
            <Link to="/analyze" className="a-btn a-btn--primary">Analyze an image</Link>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="a-card a-empty" role="alert">
          <AlertTriangle size={40} aria-hidden="true" />
          <h2>Could not load this analysis</h2>
          <p>{error}</p>
          <button type="button" className="a-btn a-btn--primary" onClick={load}>Try again</button>
        </div>
      )}

      {status === 'ready' && (
        <div className="a-stack">
          <div className="a-results">
            <section className="a-card" aria-label="MRI image">
              {hasHeatmap && (
                <div className="a-seg" role="group" aria-label="Image view">
                  <button type="button" aria-pressed={activeView === 'heatmap'} onClick={() => setView('heatmap')}>View Heatmap</button>
                  <button type="button" aria-pressed={activeView === 'original'} onClick={() => setView('original')}>View Original</button>
                  <button type="button" className="a-seg__wide" aria-pressed={activeView === 'side'} onClick={() => setView('side')}>Side by side</button>
                </div>
              )}
              <Viewer analysis={analysis} view={activeView} onHeatmapError={() => setHeatmapBroken(true)} />
              <p className="a-muted a-small" style={{ marginBottom: 0 }}>
                The heatmap (Grad-CAM) is only an explanatory visualization of which image regions influenced the model.
                {!analysis.heatmap_url && ' No heatmap was generated for this analysis.'}
              </p>
            </section>

            <div className="a-stack">
              <section className="a-card a-stack" aria-label="Prediction">
                <div className="a-row" style={{ justifyContent: 'space-between' }}>
                  <span className="a-label">Predicted class</span>
                </div>
                {lowConfidence ? (
                  <div>
                    <span className="a-badge a-badge--lg" style={{ background: 'var(--tone-warning-bg)', color: 'var(--tone-warning-text)' }}>Uncertain result</span>
                  </div>
                ) : (
                  <div><ClassBadge cls={analysis.predicted_class} label={analysis.predicted_label} large /></div>
                )}
                <ConfidenceMeter value={analysis.confidence} low={lowConfidence} />
                {lowConfidence && (
                  <div className="a-alert a-alert--warn" role="alert">
                    <AlertTriangle size={18} aria-hidden="true" />
                    <p>
                      Uncertain result: the top score is below the {formatPercent(threshold, 0)} confidence threshold, so the model does not commit to a class.
                      {top2.length > 1 && ' The two most likely classes are listed below.'}
                    </p>
                  </div>
                )}
                {top2.length > 0 && (
                  <ol className="a-small" style={{ margin: 0, paddingLeft: '1.2rem' }} aria-label="Top two classes">
                    {top2.map((t) => (
                      <li key={t.class}>{t.label || CLASS_LABELS[t.class] || t.class}: {formatPercent(t.probability)}</li>
                    ))}
                  </ol>
                )}
                {!lowConfidence && <p style={{ margin: 0 }}>{CLASS_EXPLANATIONS[analysis.predicted_class]}</p>}
                <p className="a-muted a-small" style={{ margin: 0 }}>
                  Confidence is the model's score for its own output. It is not clinical certainty.
                </p>
              </section>

              <section className="a-card" aria-label="Probability breakdown">
                <h2>Probability breakdown</h2>
                <ProbabilityBars probabilities={analysis.probabilities} predicted={analysis.predicted_class} />
              </section>

              {comparison && (
                <section className="a-card a-stack" aria-label="Model comparison">
                  <h2>Model comparison</h2>
                  <p className={`a-alert ${comparison.agree ? 'a-alert--info' : 'a-alert--warn'}`} role="status">
                    {comparison.agree ? 'Both models agree on the predicted class.' : 'The models disagree. Treat this result with extra caution.'}
                  </p>
                  <table className="a-table">
                    <caption className="sr-only">Prediction by model</caption>
                    <thead><tr><th scope="col">Model</th><th scope="col">Predicted class</th><th scope="col">Confidence</th></tr></thead>
                    <tbody>
                      {[['resnet50', 'ResNet50'], ['custom_cnn', 'Custom CNN']].map(([key, name]) => comparison[key] && (
                        <tr key={key}>
                          <th scope="row">{name}</th>
                          <td>{CLASS_LABELS[comparison[key].predicted_class] || comparison[key].predicted_class}</td>
                          <td>{formatPercent(comparison[key].confidence)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              <section className="a-card" aria-label="Analysis details">
                <h2>Details</h2>
                <dl className="a-meta">
                  <dt>Analysis ID</dt><dd><code>{analysis.id}</code></dd>
                  <dt>Date</dt><dd>{formatDate(analysis.created_at)}</dd>
                  <dt>Model version</dt><dd>{analysis.model_version}</dd>
                  {typeof analysis.entropy === 'number' && (
                    <>
                      <dt>Entropy</dt>
                      <dd>{analysis.entropy.toFixed(2)} nats (0 = certain, {MAX_ENTROPY.toFixed(2)} = maximally uncertain)</dd>
                    </>
                  )}
                  <dt>File</dt><dd>{analysis.filename}</dd>
                </dl>
              </section>
            </div>
          </div>

          <div className="a-row">
            <DownloadPdfButton id={analysis.id} demo={demo} />
            <Link to={`/report/${analysis.id}`} className="a-btn"><FileText size={18} aria-hidden="true" /> View printable report</Link>
            <Link to={`/compare?a=${encodeURIComponent(analysis.id)}`} className="a-btn">Compare with another scan</Link>
            <Link to="/analyze" className="a-btn"><Plus size={18} aria-hidden="true" /> Analyze Another Image</Link>
          </div>
        </div>
      )}
    </div>
  )
}
