// ImagePreview - selected image with its name and size plus Replace / Remove actions.
// Props: src (object URL), name, size (bytes), onReplace(file: File), onRemove(), disabled? (boolean).
import { useRef } from 'react'
import { RefreshCw, Trash2 } from 'lucide-react'
import './analysis.css'
import { formatBytes } from '../../lib/format.js'

export default function ImagePreview({ src, name, size, onReplace, onRemove, disabled = false }) {
  const inputRef = useRef(null)
  return (
    <div className="a-preview">
      <img src={src} alt={`Preview of ${name}`} />
      <div className="a-stack" style={{ gap: 12 }}>
        <div>
          <div className="a-preview__name">{name}</div>
          <div className="a-muted a-small">{formatBytes(size)}</div>
        </div>
        <div className="a-row">
          <button type="button" className="a-btn a-btn--small" disabled={disabled} onClick={() => inputRef.current.click()}>
            <RefreshCw size={16} aria-hidden="true" /> Replace image
          </button>
          <button type="button" className="a-btn a-btn--small a-btn--danger" disabled={disabled} onClick={onRemove}>
            <Trash2 size={16} aria-hidden="true" /> Remove image
          </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg"
          className="a-sr-input"
          tabIndex={-1}
          aria-label="Choose a replacement image"
          onChange={(event) => {
            if (event.target.files[0]) onReplace(event.target.files[0])
            event.target.value = ''
          }}
        />
      </div>
    </div>
  )
}
