import { Link } from 'react-router-dom'
import { Spinner } from './Spinner.jsx'
import './ui.css'

/**
 * Button
 * Props: variant 'primary'|'secondary'|'ghost'|'danger' (default primary), size 'sm'|'md'|'lg' (md),
 * loading (bool, disables and shows spinner), icon (lucide component, optional), to (string: render as router Link),
 * type (default 'button'), className, plus any native button props.
 */
export function Button({ variant = 'primary', size = 'md', loading = false, icon: Icon, to, type = 'button', className = '', children, disabled, ...rest }) {
  const cls = `btn btn--${variant} btn--${size} ${className}`.trim()
  const content = (
    <>
      {loading ? <Spinner size={16} /> : Icon ? <Icon size={size === 'lg' ? 20 : 16} aria-hidden="true" /> : null}
      <span>{children}</span>
    </>
  )
  if (to) return <Link to={to} className={cls} {...rest}>{content}</Link>
  return (
    <button type={type} className={cls} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {content}
    </button>
  )
}
