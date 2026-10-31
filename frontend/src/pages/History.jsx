// History page: searchable, filterable, paginated list of past analyses. URL: /history?q=&label=&page=
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, History as HistoryIcon, Search, SearchX } from 'lucide-react'
import '../components/analysis/analysis.css'
import ClassBadge from '../components/analysis/ClassBadge.jsx'
import ConfirmDialog from '../components/analysis/ConfirmDialog.jsx'
import DemoBadge from '../components/analysis/DemoBadge.jsx'
import { deleteAnalysis, listAnalyses } from '../lib/api.js'
import { CLASS_LABELS, CLASS_ORDER, PAGE_SIZE } from '../lib/classes.js'
import { formatDate, formatPercent } from '../lib/format.js'
import { useDemoMode } from '../lib/useDemoMode.js'

const SKELETON_ROWS = 5

export default function History() {
  const demo = useDemoMode()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') || ''
  const label = CLASS_ORDER.includes(params.get('label')) ? params.get('label') : ''
  const page = Math.max(1, Number(params.get('page')) || 1)

  const [text, setText] = useState(q)
  const [data, setData] = useState({ items: [], total: 0 })
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  const updateParams = useCallback(
    (changes) => {
      const next = new URLSearchParams(params)
      Object.entries(changes).forEach(([key, value]) => {
        if (value) next.set(key, value)
        else next.delete(key)
      })
      setParams(next, { replace: true })
    },
    [params, setParams],
  )

  // Debounce typing into the search box before it reaches the URL.
  useEffect(() => {
    if (text === q) return undefined
    const timer = setTimeout(() => updateParams({ q: text.trim(), page: '' }), 300)
    return () => clearTimeout(timer)
  }, [text, q, updateParams])

  useEffect(() => {
    let active = true
    setStatus('loading')
    listAnalyses({ search: q, label, page, page_size: PAGE_SIZE })
      .then((result) => {
        if (!active) return
        setData(result)
        setStatus('ready')
      })
      .catch((err) => {
        if (!active) return
        setError(err.message)
        setStatus('error')
      })
    return () => {
      active = false
    }
  }, [q, label, page, reloadKey])

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))
  const filtering = Boolean(q || label)

  const clearFilters = () => {
    setText('')
    setParams({}, { replace: true })
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await deleteAnalysis(pendingDelete.id)
      setPendingDelete(null)
      if (data.items.length === 1 && page > 1) updateParams({ page: String(page - 1) })
      else setReloadKey((key) => key + 1)
    } catch (err) {
      setPendingDelete(null)
      setError(err.message)
      setStatus('error')
    } finally {
      setDeleting(false)
    }
  }

  const renderBody = () => {
    if (status === 'loading') {
      return Array.from({ length: SKELETON_ROWS }, (_, row) => (
        <tr key={row} aria-hidden="true">
          {Array.from({ length: 5 }, (_, cell) => (
            <td key={cell}><span className="a-skeleton" /></td>
          ))}
          <td />
        </tr>
      ))
    }
    return data.items.map((item) => (
      <tr key={item.id}>
        <td>{formatDate(item.created_at)}</td>
        <td><code>{item.id}</code></td>
        <td className="a-small">{item.filename}</td>
        <td><ClassBadge cls={item.predicted_class} label={item.predicted_label} /></td>
        <td>{formatPercent(item.confidence)}</td>
        <td>
          <div className="a-actions">
            <Link to={`/results/${item.id}`} className="a-btn a-btn--small" aria-label={`View analysis ${item.id}`}>View</Link>
            <button type="button" className="a-btn a-btn--small a-btn--danger" aria-label={`Delete analysis ${item.id}`} onClick={() => setPendingDelete(item)}>
              Delete
            </button>
          </div>
        </td>
      </tr>
    ))
  }

  const showTable = status === 'loading' || (status === 'ready' && data.items.length > 0)

  return (
    <div className="a-page">
      <header className="a-header">
        <div>
          <h1>Analysis History</h1>
          <p>
            {status === 'ready' ? `${data.total} ${data.total === 1 ? 'analysis' : 'analyses'}${filtering ? ' match your filters' : ''}` : 'Browse previous analyses.'}
          </p>
        </div>
        <DemoBadge show={demo} />
      </header>

      <section className="a-card">
        <div className="a-toolbar">
          <div style={{ position: 'relative', flex: '1 1 260px', maxWidth: 360 }}>
            <label htmlFor="history-search" className="a-sr-input">Search by analysis ID or file name</label>
            <Search size={18} aria-hidden="true" style={{ position: 'absolute', left: 12, top: 13, color: 'var(--color-muted)' }} />
            <input
              id="history-search"
              type="search"
              className="a-input"
              style={{ paddingLeft: 38 }}
              placeholder="Search by ID or file name"
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
          </div>
          <div className="a-chips" role="group" aria-label="Filter by class">
            <button type="button" className="a-chip-btn" aria-pressed={!label} onClick={() => updateParams({ label: '', page: '' })}>All</button>
            {CLASS_ORDER.map((cls) => (
              <button key={cls} type="button" className="a-chip-btn" aria-pressed={label === cls} onClick={() => updateParams({ label: cls, page: '' })}>
                {CLASS_LABELS[cls]}
              </button>
            ))}
          </div>
        </div>

        {showTable && (
          <div className="a-table-wrap">
            <table className="a-table" aria-busy={status === 'loading'}>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Analysis ID</th>
                  <th scope="col">File</th>
                  <th scope="col">Predicted class</th>
                  <th scope="col">Confidence</th>
                  <th scope="col"><span className="a-sr-input">Actions</span></th>
                </tr>
              </thead>
              <tbody>{renderBody()}</tbody>
            </table>
          </div>
        )}

        {status === 'error' && (
          <div className="a-empty" role="alert">
            <AlertTriangle size={40} aria-hidden="true" />
            <h2>Could not load history</h2>
            <p>{error}</p>
            <button type="button" className="a-btn a-btn--primary" onClick={() => setReloadKey((key) => key + 1)}>Try again</button>
          </div>
        )}

        {status === 'ready' && data.items.length === 0 && (
          filtering ? (
            <div className="a-empty">
              <SearchX size={40} aria-hidden="true" />
              <h2>No matching analyses</h2>
              <p>Nothing matches the current search or filter.</p>
              <button type="button" className="a-btn" onClick={clearFilters}>Clear filters</button>
            </div>
          ) : (
            <div className="a-empty">
              <HistoryIcon size={40} aria-hidden="true" />
              <h2>No analyses yet</h2>
              <p>Analyzed images will appear here so you can review them later.</p>
              <Link to="/analyze" className="a-btn a-btn--primary">Analyze an image</Link>
            </div>
          )
        )}

        {status === 'ready' && data.total > PAGE_SIZE && (
          <nav className="a-pager" aria-label="Pagination">
            <span className="a-muted a-small">
              Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
            </span>
            <div className="a-row">
              <button type="button" className="a-btn a-btn--small" disabled={page <= 1} onClick={() => updateParams({ page: String(page - 1) })}>Previous</button>
              <span aria-current="page">Page {page} of {totalPages}</span>
              <button type="button" className="a-btn a-btn--small" disabled={page >= totalPages} onClick={() => updateParams({ page: String(page + 1) })}>Next</button>
            </div>
          </nav>
        )}
      </section>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete this analysis?"
        message={pendingDelete ? `Analysis ${pendingDelete.id} (${pendingDelete.filename}) and its images will be permanently removed.` : ''}
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
