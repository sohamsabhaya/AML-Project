// Model insights: verified test-set results, per-class metrics, confusion matrices and a pipeline overview.
// Data comes from GET /api/models/insights, falling back to the bundled copy of ml/results/model_insights.json.
import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, PageHeader } from '../components/ui/index.js'
import { getInsights } from '../lib/api.js'
import { CLASS_LABELS } from '../lib/classes.js'
import './insights.css'

const SERIES_COLORS = { custom_cnn: '#94A3B8', resnet50: '#0D9488' }
const SHORT_NAMES = { custom_cnn: 'Custom CNN', resnet50: 'ResNet50' }
const pct = (v, d = 2) => (typeof v === 'number' ? `${(v * 100).toFixed(d)}%` : 'n/a')
const num = (v) => (typeof v === 'number' ? v.toLocaleString() : 'n/a')
const label = (c) => CLASS_LABELS[c] || c
const fixed = (v, d = 2) => (typeof v === 'number' ? v.toFixed(d) : 'n/a')

const PIPELINE = [
  ['Upload', 'You upload a PNG or JPG brain MRI slice (up to 10 MB). It is sent only to the app server.'],
  ['Preprocess', 'The image is resized to 224 x 224 pixels, the size the models were trained on.'],
  ['Classify', 'ResNet50 (transfer learning) or the custom CNN produces four softmax scores: glioma, meningioma, no tumor and pituitary tumor.'],
  ['Explain', 'Grad-CAM highlights the image regions that influenced the prediction. It is an explanation of the model, not a tumor outline.'],
  ['Review', 'If the top score is below the confidence threshold the app reports an uncertain result.'],
]

function ConfusionMatrix({ model, classes }) {
  const matrix = model.confusion_matrix
  if (!Array.isArray(matrix)) return null
  return (
    <figure className="cm">
      <figcaption>
        <strong>{SHORT_NAMES[model.id] || model.name}</strong>
        <span className="muted"> ({pct(model.accuracy)} accuracy)</span>
      </figcaption>
      <div className="cm__scroll">
        <table className="cm__table">
          <caption className="sr-only">
            Confusion matrix for {model.name}. Rows are the true class, columns the predicted class.
          </caption>
          <thead>
            <tr>
              <th scope="col" className="cm__axis">True \ Predicted</th>
              {classes.map((c) => <th key={c} scope="col">{label(c)}</th>)}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => {
              const total = row.reduce((a, b) => a + b, 0) || 1
              return (
                <tr key={classes[i]}>
                  <th scope="row">{label(classes[i])}</th>
                  {row.map((value, j) => {
                    const share = value / total
                    const cls = `cm__cell${share >= 0.7 ? ' cm__cell--hot' : ''}${i === j ? ' cm__cell--diag' : ''}`
                    return (
                      <td
                        key={classes[j]}
                        className={cls}
                        style={{ '--share': share.toFixed(3) }}
                        title={`${value} of ${total} ${label(classes[i])} scans predicted as ${label(classes[j])} (${(share * 100).toFixed(1)}%)`}
                      >
                        {value}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </figure>
  )
}

export default function Insights() {
  const [state, setState] = useState({ loading: true, data: null, bundled: false })

  useEffect(() => {
    let active = true
    getInsights().then((result) => active && setState({ loading: false, ...result }))
    return () => {
      active = false
    }
  }, [])

  const { loading, data, bundled } = state
  if (loading) {
    return (
      <div className="page" aria-busy="true">
        <PageHeader title="Model insights" />
        <span className="skeleton" style={{ height: 280 }} />
      </div>
    )
  }

  const models = data?.models ?? []
  const ds = data?.dataset ?? {}
  const classes = ds.classes ?? Object.keys(CLASS_LABELS)
  const cnn = models.find((m) => m.id === 'custom_cnn')
  const resnet = models.find((m) => m.id === 'resnet50')
  const ordered = [cnn, resnet].filter(Boolean)
  const chartRows = [
    ['accuracy', 'Accuracy'],
    ['macro_precision', 'Macro precision'],
    ['macro_recall', 'Macro recall'],
    ['macro_f1', 'Macro F1'],
  ].map(([key, name]) => ({
    metric: name,
    ...Object.fromEntries(ordered.map((m) => [m.id, Number(((m[key] ?? 0) * 100).toFixed(2))])),
  }))

  if (ordered.length === 0) {
    return (
      <div className="page">
        <PageHeader title="Model insights" />
        <Card><p className="muted">Evaluation results are not available.</p></Card>
      </div>
    )
  }

  return (
    <div className="page">
      <PageHeader
        title="Model insights"
        subtitle={`Held-out test set: ${num(ds.test_images)} images (${num(ds.per_class_test)} per class). Numbers are read from the project notebook.`}
      />
      {bundled && (
        <p className="muted insights-note" role="status">Showing the bundled copy of the verified results (live endpoint unavailable).</p>
      )}

      <div className="grid-2">
        {ordered.map((m) => (
          <Card key={m.id} title={SHORT_NAMES[m.id] || m.name} subtitle={m.name}>
            <p className="insights-big" aria-label={`${SHORT_NAMES[m.id] || m.name} test accuracy ${pct(m.accuracy)}`}>{pct(m.accuracy)}</p>
            <p className="muted">Test accuracy. {num(m.total_params)} parameters ({num(m.trainable_params)} trainable).</p>
          </Card>
        ))}
      </div>

      <Card title="Accuracy comparison" subtitle="Test-set metrics in percent.">
        <div
          style={{ height: 300 }}
          role="img"
          aria-label={`Grouped bars comparing ${ordered.map((m) => `${SHORT_NAMES[m.id] || m.name} accuracy ${pct(m.accuracy)}`).join(' and ')}, plus macro precision, recall and F1.`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartRows} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="metric" tick={{ fill: 'var(--color-muted)', fontSize: 12 }} />
              <YAxis domain={[0, 100]} unit="%" tick={{ fill: 'var(--color-muted)', fontSize: 12 }} />
              <Tooltip
                formatter={(v) => `${v}%`}
                contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
              />
              <Legend />
              {ordered.map((m) => (
                <Bar key={m.id} dataKey={m.id} name={SHORT_NAMES[m.id] || m.name} fill={SERIES_COLORS[m.id] || '#64748B'} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="insights-table-wrap">
          <table className="insights-table">
            <caption className="sr-only">Summary metrics by model</caption>
            <thead>
              <tr>
                <th scope="col">Model</th>
                <th scope="col" className="num">Accuracy</th>
                <th scope="col" className="num">Macro precision</th>
                <th scope="col" className="num">Macro recall</th>
                <th scope="col" className="num">Macro F1</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((m) => (
                <tr key={m.id}>
                  <th scope="row">{SHORT_NAMES[m.id] || m.name}</th>
                  <td className="num">{pct(m.accuracy)}</td>
                  <td className="num">{pct(m.macro_precision)}</td>
                  <td className="num">{pct(m.macro_recall)}</td>
                  <td className="num">{pct(m.macro_f1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Per-class precision and recall" subtitle="From the notebook's classification report (two decimals as printed). AUC is one-vs-rest.">
        <div className="insights-table-wrap">
          <table className="insights-table">
            <caption className="sr-only">Per-class precision, recall, F1 and ROC AUC for each model</caption>
            <thead>
              <tr>
                <th scope="col">Class</th>
                {ordered.map((m) => (
                  <th key={m.id} scope="colgroup" colSpan={4} className="insights-group">{SHORT_NAMES[m.id] || m.name}</th>
                ))}
              </tr>
              <tr>
                <td />
                {ordered.flatMap((m) =>
                  ['Precision', 'Recall', 'F1', 'AUC'].map((h) => <th key={`${m.id}-${h}`} scope="col" className="num">{h}</th>),
                )}
              </tr>
            </thead>
            <tbody>
              {classes.map((c) => (
                <tr key={c}>
                  <th scope="row">{label(c)}</th>
                  {ordered.flatMap((m) => {
                    const row = m.per_class?.find((p) => p.class === c) || {}
                    const weak = typeof row.recall === 'number' && row.recall < 0.5
                    return [
                      <td key={`${m.id}-p`} className="num">{fixed(row.precision)}</td>,
                      <td key={`${m.id}-r`} className={weak ? 'num insights-weak' : 'num'}>
                        {fixed(row.recall)}{weak && <span className="sr-only"> (low)</span>}
                      </td>,
                      <td key={`${m.id}-f`} className="num">{fixed(row.f1)}</td>,
                      <td key={`${m.id}-a`} className="num">{fixed(row.roc_auc_ovr, 3)}</td>,
                    ]
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Confusion matrices" subtitle="Rows are the true class, columns the predicted class. Darker cells hold a larger share of that row.">
        <div className="grid-2">
          {ordered.map((m) => <ConfusionMatrix key={m.id} model={m} classes={classes} />)}
        </div>
      </Card>

      <div className="grid-2">
        <Card title="Notes and limitations">
          <ul className="insights-list">
            {ds.duplicate_hashes_in_training != null && (
              <li>
                The training folder contains {ds.duplicate_hashes_in_training} duplicated images ({ds.duplicate_copies_in_training} copies in total),
                so the validation split is optimistic.
                {ds.cross_split_duplicates === 0 && ' No duplicates were found between training and test, so the test figures are the honest ones.'}
              </li>
            )}
            {ordered.flatMap((m) =>
              (m.notes || []).slice(2).map((n, i) => (
                <li key={`${m.id}-${i}`}><strong>{SHORT_NAMES[m.id] || m.name}:</strong> {n}</li>
              )),
            )}
            {(data?.not_available || []).map((n) => <li key={n}>{n}</li>)}
          </ul>
        </Card>

        <Card title="How it works">
          <ol className="insights-steps">
            {PIPELINE.map(([title, text]) => (
              <li key={title}><strong>{title}.</strong> {text}</li>
            ))}
          </ol>
          <p className="muted insights-note">
            Dataset: {num(ds.train_images)} training and {num(ds.test_images)} test images, {classes.length} classes, {ds.image_size?.join(' x ')} px.
          </p>
        </Card>
      </div>
    </div>
  )
}
