import { useEffect, useState } from 'react'

// localStorage helpers for the display name and analysis defaults.
// Keys: brainscan.profile (display name), brainscan.prefs ({ defaultModel, heatmap }).
const PROFILE_KEY = 'brainscan.profile'
const PREFS_KEY = 'brainscan.prefs'
const CHANGE_EVENT = 'brainscan:storage'

export const DEFAULT_PREFS = { defaultModel: 'resnet50', heatmap: true }

function read(key) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Storage unavailable (private mode / quota): settings simply will not persist.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT))
}

/** Saved display name, or 'Guest'. */
export function getProfile() {
  return read(PROFILE_KEY)?.trim() || 'Guest'
}

export function setProfile(name) {
  write(PROFILE_KEY, String(name).trim())
}

/** Returns { defaultModel: 'resnet50' | 'custom_cnn', heatmap: boolean }. */
export function getPrefs() {
  try {
    const saved = JSON.parse(read(PREFS_KEY) || '{}')
    return {
      defaultModel: saved.defaultModel === 'custom_cnn' ? 'custom_cnn' : 'resnet50',
      heatmap: typeof saved.heatmap === 'boolean' ? saved.heatmap : DEFAULT_PREFS.heatmap,
    }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

/** Merges a partial prefs object into the saved prefs and returns the result. */
export function setPrefs(partial) {
  const next = { ...getPrefs(), ...partial }
  write(PREFS_KEY, JSON.stringify(next))
  return next
}

/** React hook: the current display name, kept in sync with Settings changes. */
export function useProfile() {
  const [name, setName] = useState(getProfile)
  useEffect(() => {
    const sync = () => setName(getProfile())
    window.addEventListener(CHANGE_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(CHANGE_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])
  return name
}

const THEME_KEY = 'brainscan.theme'

/** Saved theme choice: 'system' (default), 'light' or 'dark'. */
export function getTheme() {
  const value = read(THEME_KEY)
  return value === 'light' || value === 'dark' ? value : 'system'
}

/** Applies light theme permanently to <html>. */
export function applyTheme() {
  document.documentElement.setAttribute('data-theme', 'light')
}

export function setTheme(theme) {
  write(THEME_KEY, theme)
  applyTheme(theme)
}
