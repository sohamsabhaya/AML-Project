// Small formatting and validation helpers shared by the analysis pages.
import { MAX_FILE_BYTES } from './classes.js'

export function formatDate(iso) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatPercent(value, digits = 1) {
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const ALLOWED_TYPES = ['image/png', 'image/jpeg']
const ALLOWED_EXTENSION = /\.(png|jpe?g)$/i

// Returns an error message for an unusable file, or an empty string when it is fine.
export function validateImageFile(file) {
  if (!file) return 'Choose an MRI image to analyze.'
  if (file.size === 0) return 'This file is empty. Choose a different image.'
  if (!ALLOWED_TYPES.includes(file.type) && !ALLOWED_EXTENSION.test(file.name)) {
    return 'Unsupported file type. Please upload a PNG, JPG or JPEG image.'
  }
  if (file.size > MAX_FILE_BYTES) {
    return `This file is ${formatBytes(file.size)}. The maximum size is 10 MB.`
  }
  return ''
}
