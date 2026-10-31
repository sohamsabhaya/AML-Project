// Reads the user's saved defaults (written by the Settings page) without ever throwing.
const KEY = 'brainscan.prefs'

export function readPrefs() {
  const fallback = { defaultModel: 'resnet50', heatmap: true }
  try {
    const raw = JSON.parse(localStorage.getItem(KEY))
    if (!raw || typeof raw !== 'object') return fallback
    return {
      defaultModel: raw.defaultModel === 'custom_cnn' ? 'custom_cnn' : 'resnet50',
      heatmap: typeof raw.heatmap === 'boolean' ? raw.heatmap : true,
    }
  } catch {
    return fallback
  }
}
