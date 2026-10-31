import './ui.css'

/**
 * Card
 * Props: title (node, optional), subtitle (node, optional), actions (node shown at header right),
 * padded (bool, default true), className, children.
 */
export function Card({ title, subtitle, actions, padded = true, className = '', children, ...rest }) {
  return (
    <section className={`card ${className}`.trim()} {...rest}>
      {(title || actions) && (
        <header className="card__header">
          <div>
            {title && <h2 className="card__title">{title}</h2>}
            {subtitle && <p className="muted card__subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="row">{actions}</div>}
        </header>
      )}
      <div className={padded ? 'card__body' : undefined}>{children}</div>
    </section>
  )
}
