// DropZone - drag-and-drop / click-to-browse file picker for a single image.
// Props: onSelect(files: File[]) called with the chosen or dropped files (validation is up to the caller),
//        disabled? (boolean), describedBy? (id of an element, e.g. the error message).
// Keyboard: the "Browse Files" button is the focusable control; clicking anywhere in the zone also opens the dialog.
import { useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'
import './analysis.css'

export default function DropZone({ onSelect, disabled = false, describedBy }) {
  const inputRef = useRef(null)
  const [over, setOver] = useState(false)

  const handleDrop = (event) => {
    event.preventDefault()
    setOver(false)
    if (!disabled && event.dataTransfer.files.length) onSelect([...event.dataTransfer.files])
  }

  const handleInput = (event) => {
    if (event.target.files.length) onSelect([...event.target.files])
    event.target.value = ''
  }

  return (
    <div
      className={`a-dropzone${over ? ' a-dropzone--over' : ''}${disabled ? ' a-dropzone--disabled' : ''}`}
      onDragOver={(event) => {
        event.preventDefault()
        if (!disabled) setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current.click()}
    >
      <UploadCloud className="a-dropzone__icon" size={44} aria-hidden="true" />
      <strong>Drag and drop an MRI image here</strong>
      <span className="a-muted">or</span>
      <button
        type="button"
        className="a-btn a-btn--primary"
        disabled={disabled}
        aria-describedby={describedBy}
        onClick={(event) => {
          event.stopPropagation()
          inputRef.current.click()
        }}
      >
        Browse Files
      </button>
      <span className="a-muted a-small">Supported formats: PNG, JPG, JPEG. Maximum size 10 MB.</span>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg"
        className="a-sr-input"
        tabIndex={-1}
        aria-label="Choose MRI image file"
        onChange={handleInput}
      />
    </div>
  )
}
