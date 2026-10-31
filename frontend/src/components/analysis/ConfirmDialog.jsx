// ConfirmDialog - modal confirmation built on the native <dialog> element (focus trap and Esc come for free).
// Props: open (boolean), title, message, confirmLabel?, busy? (boolean), onConfirm(), onCancel().
import { useEffect, useRef } from 'react'
import './analysis.css'

export default function ConfirmDialog({ open, title, message, confirmLabel = 'Delete', busy = false, onConfirm, onCancel }) {
  const ref = useRef(null)

  useEffect(() => {
    const dialog = ref.current
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog ref={ref} className="a-dialog" aria-labelledby="confirm-title" onCancel={onCancel}>
      <h2 id="confirm-title">{title}</h2>
      <p>{message}</p>
      <div className="a-dialog__actions">
        <button type="button" className="a-btn" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className="a-btn a-btn--danger-solid" onClick={onConfirm} disabled={busy}>
          {busy ? 'Deleting...' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
