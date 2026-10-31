import './ui.css'

/** EmptyState. Props: icon (lucide component), title (string), message (node), action (node, e.g. a Button), tone 'neutral'|'error'. */
export function EmptyState({ icon: Icon, title, message, action, tone = 'neutral' }) {
  return (
    <div className={`empty empty--${tone}`} role={tone === 'error' ? 'alert' : undefined}>
      {Icon && <span className="empty__icon"><Icon size={26} aria-hidden="true" /></span>}
      <h3>{title}</h3>
      {message && <p className="muted">{message}</p>}
      {action && <div className="empty__action">{action}</div>}
    </div>
  )
}
