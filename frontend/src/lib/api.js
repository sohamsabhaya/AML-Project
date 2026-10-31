// API client for the BrainScan backend (see docs/API_CONTRACT.md).
// All calls use relative /api URLs. When VITE_USE_MOCK=true, or the backend is unreachable
// (network error or a failing /api/health), every call is served by lib/mock.js instead.
// Pages can check isDemoMode() after their first call, or await detectDemoMode().
import { DISCLAIMER } from './classes.js'
import * as mock from './mock.js'
import staticInsights from './modelInsights.json'

export { DISCLAIMER }

const BASE = '/api'
const NETWORK_MESSAGE = 'Cannot reach the analysis server. Check your connection and try again.'

const forcedMock = import.meta.env.VITE_USE_MOCK === 'true'
let demo = forcedMock
let probe = null

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function checkBackend() {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 4000)
  try {
    const res = await fetch(`${BASE}/health`, { signal: controller.signal })
    demo = !res.ok
  } catch {
    demo = true
  } finally {
    clearTimeout(timer)
  }
}

function ensureMode() {
  if (forcedMock) return Promise.resolve()
  if (!probe) probe = checkBackend()
  return probe
}

export const isDemoMode = () => demo

export async function detectDemoMode() {
  await ensureMode()
  return demo
}

async function errorMessage(res) {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
  } catch {
    // body was not JSON
  }
  return `The server returned an error (${res.status}). Please try again.`
}

async function request(path, { method = 'GET', params, body, signal } = {}) {
  const query = new URLSearchParams()
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  const queryString = query.toString()
  const url = `${BASE}${path}${queryString ? `?${queryString}` : ''}`

  let res
  try {
    res = await fetch(url, { method, body, signal })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new ApiError(NETWORK_MESSAGE, 0)
  }
  if (!res.ok) throw new ApiError(await errorMessage(res), res.status)
  return res.status === 204 ? null : res.json()
}

export async function getHealth() {
  await ensureMode()
  return demo ? mock.mockHealth() : request('/health')
}

export async function getModels() {
  await ensureMode()
  return demo ? mock.mockModels() : request('/models')
}

// Verified evaluation numbers. Falls back to the bundled static copy of ml/results/model_insights.json.
export async function getInsights() {
  try {
    await ensureMode()
    if (!demo) {
      const data = await request('/models/insights')
      if (data && Array.isArray(data.models) && data.models.length > 0) return { data, bundled: false }
    }
  } catch {
    // fall through to the bundled copy
  }
  return { data: staticInsights, bundled: true }
}

export async function getStats() {
  await ensureMode()
  return demo ? mock.mockStats() : request('/stats')
}

export async function listAnalyses(params = {}) {
  await ensureMode()
  return demo ? mock.mockList(params) : request('/analyses', { params })
}

// Resolves to null when the analysis does not exist.
export async function getAnalysis(id) {
  await ensureMode()
  if (demo) return mock.mockGet(id)
  try {
    return await request(`/analyses/${encodeURIComponent(id)}`)
  } catch (err) {
    if (err.status === 404) return null
    throw err
  }
}

export async function analyzeImage(file, { model = 'resnet50', heatmap = true, signal } = {}) {
  await ensureMode()
  if (demo) return mock.mockAnalyze(file, { model, heatmap, signal })
  const form = new FormData()
  form.append('file', file)
  return request('/analyze', { method: 'POST', params: { model, heatmap }, body: form, signal })
}

export async function deleteAnalysis(id) {
  await ensureMode()
  if (demo) return mock.mockDelete(id)
  await request(`/analyses/${encodeURIComponent(id)}`, { method: 'DELETE' })
  return true
}

export const imageUrl = (id) => (demo ? mock.mockImageUrl(id) : `${BASE}/analyses/${id}/image`)
export const heatmapUrl = (id) => (demo ? mock.mockHeatmapUrl(id) : `${BASE}/analyses/${id}/heatmap`)
// In demo mode there is no PDF endpoint, so the link opens the printable report instead.
export const reportUrl = (id) => (demo ? `/report/${id}` : `${BASE}/analyses/${id}/report`)
