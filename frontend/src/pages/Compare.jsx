// Compare page: two saved analyses side by side for /compare?a=<id>&b=<id>, with a picker when one is missing.
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import '../components/analysis/analysis.css'
import ClassBadge from '../components/analysis/ClassBadge.jsx'
import ProbabilityBars from '../components/analysis/ProbabilityBars.jsx'
import { getAnalysis, listAnalyses } from '../lib/api.js'
import { formatDate, formatPercent } from '../lib/format.js'

function Picker({ id, title, value, options, onChange }) {
  return (
    <div className="a-field">
      <label htmlFor={id}>{title}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose a saved analysis</option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.filename} ({o.predicted_label}, {formatDate(o.created_at)})
          </option>
        ))}
      </select>
    </div>
  )
}

function Column({ slot, state }) {
  if (state.status === 'empty') {
    return <section className="a-card a-muted" aria-label={`Analysis ${slot}`}>Choose analysis {slot} above.</section>
  }
  if (state.status === 'loading') {
    return <section className="a-card" aria-busy="true" aria-label={`Analysis ${slot}`}><span className="a-skeleton" style={{ height: 200 }} /></section>
  }
  if (state.status === 'missing' || state.status === 'error') {
    return (
      <section className="a-card" role="alert" aria-label={`Analysis ${slot}`}>
        <p>{state.status === 'missing' ? 'This analysis was not found. It may have been deleted.' : state.error}</p>
      </section>
    )
  }
  const a = state.analysis
  const uncertain = a.low_confidence ?? false
  return (
    <section className="a-card a-stack" aria-label={`Analysis ${slot}: ${a.filename}`}>
      <img src={a.image_url} alt={`MRI ${a.filename}`} style={{ width: '100%', maxHeight: 320, objectFit: 'contain', background: '#0F172A', borderRadius: 'var(--radius-control)' }} />
      <div className="a-row">
        {uncertain ? (
          <span className="a-badge a-badge--lg" style={{ background: 'var(--tone-warning-bg)', color: 'var(--tone-warning-text)' }}>Uncertain result</span>
        ) : (
          <ClassBadge cls={a.predicted_class} label={a.predicted_label} large />
        )}
        <strong>{formatPercent(a.confidence)}</strong>
      </div>
      <ProbabilityBars probabilities={a.probabilities} predicted={a.predicted_class} />
      <dl className="a-meta">
        <dt>File</dt><dd>{a.filename}</dd>
        <dt>Date</dt><dd>{formatDate(a.created_at)}</dd>
        <dt>Model</dt><dd>{a.model_version}</dd>
        {typeof a.entropy === 'number' && (<><dt>Entropy</dt><dd>{a.entropy.toFixed(2)} nats</dd></>)}
      </dl>
      <Link to={`/results/${encodeURIComponent(a.id)}`} className="a-btn">Open full results</Link>
    </section>
  )
}

function useAnalysis(id) {
  const [state, setState] = useState({ status: id ? 'loading' : 'empty' })
  useEffect(() => {
    if (!id) {
      setState({ status: 'empty' })
      return undefined
    }
    let active = true
    setState({ status: 'loading' })
    getAnalysis(id)
      .then((analysis) => active && setState(analysis ? { status: 'ready', analysis } : { status: 'missing' }))
      .catch((err) => active && setState({ status: 'error', error: err.message }))
    return () => {
      active = false
    }
  }, [id])
  return state
}

export default function Compare() {
  const [params, setParams] = useSearchParams()
  const a = params.get('a') || ''
  const b = params.get('b') || ''
  const [options, setOptions] = useState([])
  const stateA = useAnalysis(a)
  const stateB = useAnalysis(b)

  useEffect(() => {
    let active = true
    listAnalyses({ page: 1, page_size: 50 })
      .then((list) => active && setOptions(list?.items ?? []))
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

  const set = (key) => (value) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const both = stateA.status === 'ready' && stateB.status === 'ready'
  const same = both && stateA.analysis.predicted_class === stateB.analysis.predicted_class

  return (
    <div className="a-page">
      <header className="a-header">
        <div>
          <h1>Compare scans</h1>
          <p>View two saved analyses side by side.</p>
        </div>
      </header>
      <div className="a-stack">
        <div className="a-card a-options">
          <Picker id="compare-a" title="Analysis A" value={a} options={options} onChange={set('a')} />
          <Picker id="compare-b" title="Analysis B" value={b} options={options} onChange={set('b')} />
        </div>
        {both && (
          <p className={`a-alert ${same ? 'a-alert--info' : 'a-alert--warn'}`} role="status">
            {same ? 'Both analyses have the same predicted class.' : 'The two analyses have different predicted classes.'}
            {' '}Confidence differs by {formatPercent(Math.abs(stateA.analysis.confidence - stateB.analysis.confidence))}.
          </p>
        )}
        {options.length === 0 && !a && !b && (
          <p className="a-muted">No saved analyses yet. <Link to="/analyze">Analyze an image</Link> first.</p>
        )}
        <div className="grid-2">
          <Column slot="A" state={stateA} />
          <Column slot="B" state={stateB} />
        </div>
      </div>
    </div>
  )
}
