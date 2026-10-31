import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, CalendarDays, Gauge, PlusCircle, AlertTriangle, ScanSearch, BarChart3 } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getModels, getStats, isDemoMode, listAnalyses } from '../lib/api.js'
import { Badge, Button, Card, DataTable, EmptyState, PageHeader, StatCard } from '../components/ui/index.js'

const CLASS_META = {
  glioma: { label: 'Glioma', color: '#DC2626' },
  meningioma: { label: 'Meningioma', color: '#D97706' },
  notumor: { label: 'No Tumor', color: '#16A34A' },
  pituitary: { label: 'Pituitary Tumor', color: '#7C3AED' },
}
const MODEL_COLORS = ['#0D9488', '#94A3B8']

// Shown only when the API returns no model metrics. Known results from the project notebook (accuracy only).
const FALLBACK_MODELS = [
  { name: 'Custom CNN', accuracy: 74.31 },
  { name: 'ResNet50', accuracy: 90.0 },
]

const percent = (v) => `${(v * 100).toFixed(1)}%`
const formatDate = (iso) =>
  new Date(iso).toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

/** Accepts the models payload ({models:[...]} or an array) and returns [{name, accuracy, precision, recall, f1}] in percent. */
function normalizeModels(payload) {
  const list = Array.isArray(payload) ? payload : payload?.models ?? []
  const pct = (v) => (typeof v === 'number' ? Number((v <= 1 ? v * 100 : v).toFixed(2)) : undefined)
  return list
    .map((m) => ({
      name: m.name ?? m.model ?? m.model_name ?? 'Model',
      accuracy: pct(m.accuracy),
      precision: pct(m.precision),
      recall: pct(m.recall),
      f1: pct(m.f1 ?? m.f1_score),
    }))
    .filter((m) => m.accuracy !== undefined)
}

/** Pivots models into one row per metric so Recharts draws grouped bars (one bar per model). */
function metricRows(models) {
  return [
    ['accuracy', 'Accuracy'],
    ['precision', 'Precision'],
    ['recall', 'Recall'],
    ['f1', 'F1 score'],
  ]
    .filter(([key]) => models.some((m) => m[key] !== undefined))
    .map(([key, metric]) => ({ metric, ...Object.fromEntries(models.map((m) => [m.name, m[key]])) }))
}

function useDashboardData() {
  const [state, setState] = useState({ loading: true, error: null, stats: null, recent: [], models: [] })
  useEffect(() => {
    let active = true
    Promise.all([getStats(), listAnalyses({ page: 1, page_size: 5 }), getModels().catch(() => null)])
      .then(([stats, list, models]) => {
        if (active) setState({ loading: false, error: null, stats, recent: list?.items ?? [], models: normalizeModels(models) })
      })
      .catch((err) => {
        if (active) setState((s) => ({ ...s, loading: false, error: err?.message || 'Could not load dashboard data.' }))
      })
    return () => {
      active = false
    }
  }, [])
  return state
}

function ClassDistribution({ byClass }) {
  const data = Object.keys(CLASS_META).map((key) => ({ key, name: CLASS_META[key].label, count: byClass?.[key] ?? 0 }))
  if (data.every((d) => d.count === 0)) {
    return <EmptyState icon={BarChart3} title="No data yet" message="The distribution appears after your first analysis." />
  }
  return (
    <div style={{ height: 260 }} role="img" aria-label={`Scans per class: ${data.map((d) => `${d.name} ${d.count}`).join(', ')}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} tickLine={false} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: 'rgba(13,148,136,0.06)' }} />
          <Bar dataKey="count" name="Scans" radius={[6, 6, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.key} fill={CLASS_META[d.key].color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ModelPerformance({ models }) {
  const isFallback = models.length === 0
  const shown = isFallback ? FALLBACK_MODELS : models
  return (
    <Card
      title="Model performance"
      subtitle={isFallback ? 'Static reference results (accuracy only). Live metrics were not available.' : 'Held-out test set metrics, in percent.'}
      actions={isFallback ? <Badge kind="neutral">Static fallback</Badge> : null}
    >
      <div style={{ height: 280 }} role="img" aria-label={`Model comparison: ${shown.map((m) => `${m.name} accuracy ${m.accuracy}%`).join(', ')}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={metricRows(shown)} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
            <XAxis dataKey="metric" tick={{ fontSize: 12 }} tickLine={false} />
            <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip formatter={(v) => `${v}%`} cursor={{ fill: 'rgba(13,148,136,0.06)' }} />
            <Legend />
            {shown.map((m, i) => (
              <Bar key={m.name} dataKey={m.name} fill={MODEL_COLORS[i % MODEL_COLORS.length]} radius={[6, 6, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const { loading, error, stats, recent, models } = useDashboardData()
  const hasScans = (stats?.total_scans ?? 0) > 0

  const columns = [
    { key: 'created_at', header: 'Date', render: (r) => formatDate(r.created_at) },
    { key: 'id', header: 'Analysis ID', render: (r) => <code>{r.id}</code> },
    { key: 'predicted_class', header: 'Predicted class', render: (r) => <Badge kind={r.predicted_class}>{r.predicted_label}</Badge> },
    { key: 'confidence', header: 'Confidence', align: 'right', render: (r) => percent(r.confidence) },
    {
      key: 'actions',
      header: <span className="sr-only">Actions</span>,
      align: 'right',
      render: (r) => (
        <Link to={`/results/${r.id}`} className="btn btn--ghost btn--sm" aria-label={`View analysis ${r.id}`}>
          View
        </Link>
      ),
    },
  ]

  return (
    <div className="page">
      <PageHeader
        title="Dashboard"
        subtitle="Brain MRI classification and performance metrics."
        actions={
          <>
            {isDemoMode() && <Badge kind="neutral">Demo data</Badge>}
            <Button to="/analyze" size="lg" icon={PlusCircle}>Start New Analysis</Button>
          </>
        }
      />

      {error && <EmptyState tone="error" icon={AlertTriangle} title="Could not load the dashboard" message={error} />}

      <div className="grid-3">
        <StatCard icon={ScanSearch} label="Total scans" value={stats?.total_scans ?? 0} loading={loading} />
        <StatCard icon={CalendarDays} label="Analyses in the last 7 days" value={stats?.last_7_days ?? 0} loading={loading} />
        <StatCard icon={Gauge} label="Average confidence" value={hasScans ? percent(stats.average_confidence) : '-'} hint={hasScans ? undefined : 'No scans yet'} loading={loading} />
      </div>

      <Card
        title="Recent analyses"
        padded={false}
        actions={<Button to="/history" variant="ghost" size="sm">View all</Button>}
      >
        {loading ? (
          <div className="stack" style={{ padding: '1.25rem' }} aria-busy="true">
            {[0, 1, 2].map((i) => <span key={i} className="skeleton" style={{ height: 22 }} />)}
          </div>
        ) : (
          <DataTable
            columns={columns}
            rows={recent}
            caption="Five most recent analyses"
            empty={
              <EmptyState
                icon={Activity}
                title="No analyses yet"
                message="Upload a brain MRI to see its prediction, confidence and heatmap here."
                action={<Button to="/analyze" icon={PlusCircle}>Start New Analysis</Button>}
              />
            }
          />
        )}
      </Card>

      <div className="grid-2">
        <Card title="Class distribution" subtitle="Number of scans per predicted class">
          {loading ? <span className="skeleton" style={{ height: 260 }} /> : <ClassDistribution byClass={stats?.by_class} />}
        </Card>
        {loading ? <Card title="Model performance"><span className="skeleton" style={{ height: 280 }} /></Card> : <ModelPerformance models={models} />}
      </div>
    </div>
  )
}
