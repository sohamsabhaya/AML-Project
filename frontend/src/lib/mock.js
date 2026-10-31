// Demo-data backend used when the API is unreachable (or VITE_USE_MOCK=true).
// Records live in memory and are mirrored to localStorage ("brainscan.demoRecords").
// Seed records carry no image data: their placeholder MRI/heatmap are drawn as SVG on demand.
import { CLASS_ORDER, CLASS_LABELS, DISCLAIMER } from './classes.js'

const STORAGE_KEY = 'brainscan.demoRecords'
const DAY_MS = 24 * 60 * 60 * 1000

function mulberry32(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function hashString(text) {
  let h = 2166136261
  for (let i = 0; i < text.length; i += 1) h = Math.imul(h ^ text.charCodeAt(i), 16777619)
  return h >>> 0
}

const round4 = (n) => Math.round(n * 10000) / 10000

// Builds four probabilities that sum to exactly 1 with `cls` as the top class.
function buildProbabilities(rng, cls, confidence) {
  const others = CLASS_ORDER.filter((c) => c !== cls)
  const weights = others.map(() => 0.2 + rng())
  const weightSum = weights.reduce((a, b) => a + b, 0)
  const probabilities = {}
  let used = 0
  others.forEach((c, i) => {
    probabilities[c] = round4(((1 - confidence) * weights[i]) / weightSum)
    used += probabilities[c]
  })
  probabilities[cls] = round4(1 - used)
  return CLASS_ORDER.reduce((acc, c) => ({ ...acc, [c]: probabilities[c] }), {})
}

function makeRecord({ id, seed, created_at, filename, cls, confidence, model, heatmap, image_data = null }) {
  const rng = mulberry32(seed)
  const probabilities = buildProbabilities(rng, cls, confidence)
  return {
    id,
    seed,
    created_at,
    filename,
    predicted_class: cls,
    predicted_label: CLASS_LABELS[cls],
    confidence: probabilities[cls],
    probabilities,
    model_id: model === 'custom_cnn' ? 'custom_cnn' : 'resnet50',
    model_version: model === 'custom_cnn' ? 'custom-cnn-demo' : 'resnet50-demo',
    heatmap,
    image_data,
  }
}

function seedRecords() {
  const rng = mulberry32(2026)
  const now = Date.now()
  return Array.from({ length: 12 }, (_, i) => {
    const cls = CLASS_ORDER[i % 4]
    const confidence = i === 5 ? 0.54 : round4(0.72 + rng() * 0.26)
    return makeRecord({
      id: Math.floor(rng() * 0xffffffff).toString(16).padStart(8, '0'),
      seed: 100 + i,
      created_at: new Date(now - (i * 1.7 + 0.2) * DAY_MS).toISOString(),
      filename: `scan_${String(12 - i).padStart(2, '0')}.${i % 3 === 0 ? 'png' : 'jpg'}`,
      cls,
      confidence,
      model: i % 4 === 3 ? 'custom_cnn' : 'resnet50',
      heatmap: true,
    })
  })
}

let records = loadRecords()

function loadRecords() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (Array.isArray(stored)) return stored
  } catch {
    // fall through to seed data
  }
  const seeded = seedRecords()
  persist(seeded)
  return seeded
}

function persist(list = records) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // storage may be full or blocked; the in-memory copy still works
  }
}

// ---- placeholder images -------------------------------------------------

const svgUri = (svg) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`

function blobCenter(record) {
  const rng = mulberry32(record.seed * 7 + 3)
  return { x: 85 + rng() * 90, y: 85 + rng() * 90, r: 22 + rng() * 22 }
}

function mriBase(record) {
  const { x, y, r } = blobCenter(record)
  const lesion =
    record.predicted_class === 'notumor'
      ? ''
      : `<circle cx="${x}" cy="${y}" r="${r / 2.6}" fill="#e5e7eb" opacity="0.85" filter="url(#soft)"/>`
  const photo = record.image_data
    ? `<image href="${record.image_data}" width="256" height="256" preserveAspectRatio="xMidYMid slice"/>`
    : `<ellipse cx="128" cy="128" rx="92" ry="110" fill="url(#skull)"/>
       <ellipse cx="128" cy="128" rx="78" ry="96" fill="url(#brain)"/>
       <path d="M128 40 V216" stroke="#111827" stroke-width="3" opacity="0.6"/>
       <ellipse cx="108" cy="140" rx="12" ry="26" fill="#0f172a" opacity="0.7"/>
       <ellipse cx="148" cy="140" rx="12" ry="26" fill="#0f172a" opacity="0.7"/>
       ${lesion}`
  return `<rect width="256" height="256" fill="#050810"/>${photo}`
}

const SVG_DEFS = `<defs>
  <radialGradient id="skull"><stop offset="0.7" stop-color="#9ca3af"/><stop offset="1" stop-color="#374151"/></radialGradient>
  <radialGradient id="brain"><stop offset="0" stop-color="#d1d5db"/><stop offset="1" stop-color="#6b7280"/></radialGradient>
  <radialGradient id="hot"><stop offset="0" stop-color="#ef4444" stop-opacity="0.9"/><stop offset="0.5" stop-color="#facc15" stop-opacity="0.55"/><stop offset="1" stop-color="#22c55e" stop-opacity="0"/></radialGradient>
  <filter id="soft"><feGaussianBlur stdDeviation="3"/></filter>
</defs>`

function placeholderMri(record) {
  return svgUri(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">${SVG_DEFS}${mriBase(record)}</svg>`)
}

function placeholderHeatmap(record) {
  const { x, y, r } = blobCenter(record)
  const spread = record.predicted_class === 'notumor' ? 70 : r * 2.2
  return svgUri(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">${SVG_DEFS}${mriBase(record)}` +
      `<circle cx="${x}" cy="${y}" r="${spread}" fill="url(#hot)" opacity="${record.predicted_class === 'notumor' ? 0.35 : 1}"/></svg>`,
  )
}

export function mockImageUrl(id) {
  const record = records.find((r) => r.id === id)
  return record ? placeholderMri(record) : ''
}

export function mockHeatmapUrl(id) {
  const record = records.find((r) => r.id === id)
  return record && record.heatmap ? placeholderHeatmap(record) : ''
}

// ---- API-shaped reads and writes ----------------------------------------

function toSummary(r) {
  const { id, created_at, filename, predicted_class, predicted_label, confidence } = r
  return { id, created_at, filename, predicted_class, predicted_label, confidence }
}

function entropyOf(probabilities) {
  return -Object.values(probabilities).reduce((sum, p) => (p > 0 ? sum + p * Math.log(p) : sum), 0)
}

function toAnalysis(r) {
  const ranked = CLASS_ORDER.map((c) => ({ class: c, label: CLASS_LABELS[c], probability: r.probabilities[c] })).sort(
    (a, b) => b.probability - a.probability,
  )
  return {
    ...toSummary(r),
    probabilities: r.probabilities,
    low_confidence: r.confidence < 0.6,
    confidence_threshold: 0.6,
    top2: ranked.slice(0, 2),
    entropy: round4(entropyOf(r.probabilities)),
    model_id: r.model_id || 'resnet50',
    comparison: r.comparison || null,
    model_version: r.model_version,
    image_url: placeholderMri(r),
    heatmap_url: r.heatmap ? placeholderHeatmap(r) : null,
    disclaimer: DISCLAIMER,
  }
}

const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    })
  })

export async function mockList({ search = '', label = '', page = 1, page_size = 10 } = {}) {
  await sleep(250)
  const needle = search.trim().toLowerCase()
  const filtered = records
    .filter((r) => !label || r.predicted_class === label)
    .filter((r) => !needle || r.id.toLowerCase().includes(needle) || r.filename.toLowerCase().includes(needle))
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
  const start = (page - 1) * page_size
  return { items: filtered.slice(start, start + page_size).map(toSummary), total: filtered.length, page, page_size }
}

export async function mockGet(id) {
  await sleep(200)
  const record = records.find((r) => r.id === id)
  return record ? toAnalysis(record) : null
}

export async function mockDelete(id) {
  await sleep(150)
  records = records.filter((r) => r.id !== id)
  persist()
  return true
}

async function makeThumbnail(file) {
  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, 320 / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.8)
  } catch {
    return null
  }
}

// Deterministic for the same file: the class and scores come from a hash of name and size.
export async function mockAnalyze(file, { model = 'resnet50', heatmap = true, signal } = {}) {
  const requested = model
  if (model === 'both') model = 'resnet50'
  const [image_data] = await Promise.all([makeThumbnail(file), sleep(1800, signal)])
  const seed = hashString(`${file.name}:${file.size}`)
  const rng = mulberry32(seed)
  const record = makeRecord({
    id: Math.floor(Math.random() * 0xffffffff).toString(16).padStart(8, '0'),
    seed,
    created_at: new Date().toISOString(),
    filename: file.name,
    cls: CLASS_ORDER[Math.floor(rng() * CLASS_ORDER.length)],
    confidence: round4(0.55 + rng() * 0.42),
    model,
    heatmap,
    image_data,
  })
  records = [record, ...records]
  persist()
  const analysis = toAnalysis(record)
  if (requested === 'both') {
    // Demo only: the second model's scores are generated from a different seed.
    const other = makeRecord({
      id: record.id, seed: seed + 1, created_at: record.created_at, filename: file.name,
      cls: CLASS_ORDER[Math.floor(mulberry32(seed + 1)() * CLASS_ORDER.length)],
      confidence: round4(0.55 + mulberry32(seed + 2)() * 0.42), model: 'custom_cnn', heatmap: false,
    })
    const part = (r) => ({ predicted_class: r.predicted_class, confidence: r.confidence, probabilities: r.probabilities })
    analysis.comparison = { resnet50: part(record), custom_cnn: part(other), agree: record.predicted_class === other.predicted_class }
    record.comparison = analysis.comparison
  }
  return analysis
}

export function mockStats() {
  const by_class = Object.fromEntries(CLASS_ORDER.map((c) => [c, records.filter((r) => r.predicted_class === c).length]))
  const weekAgo = Date.now() - 7 * DAY_MS
  const total = records.length
  return {
    total_scans: total,
    last_7_days: records.filter((r) => new Date(r.created_at).getTime() >= weekAgo).length,
    by_class,
    average_confidence: total ? round4(records.reduce((sum, r) => sum + r.confidence, 0) / total) : 0,
  }
}

export const mockHealth = () => ({
  status: 'demo',
  model_loaded: false,
  model_version: 'demo',
  classes: CLASS_ORDER,
})

export const mockModels = () => ({
  models: [
    { name: 'Custom CNN', accuracy: 0.7431, precision: 0.7581, recall: 0.7431, f1: 0.7055, parameters: 111172 },
    { name: 'ResNet50', accuracy: 0.9, precision: 0.9061, recall: 0.9, f1: 0.8975, parameters: 23851012 },
  ],
})
