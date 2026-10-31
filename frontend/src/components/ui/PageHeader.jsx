import './ui.css'

/** PageHeader. Props: title (string), subtitle (node, optional), actions (node shown at right). */
export function PageHeader({ title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted page-header__sub">{subtitle}</p>}
      </div>
      {actions && <div className="row no-print">{actions}</div>}
    </header>
  )
}
