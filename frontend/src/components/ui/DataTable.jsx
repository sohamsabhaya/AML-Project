import './ui.css'

/**
 * DataTable
 * Props: columns [{ key, header, render?(row), align?: 'left'|'right', className? }], rows (array),
 * rowKey (fn(row) => key, default row.id), empty (node shown when rows is empty), caption (sr-only text).
 * Scrolls horizontally on narrow screens.
 */
export function DataTable({ columns, rows, rowKey = (r) => r.id, empty = null, caption }) {
  if (!rows || rows.length === 0) return empty
  return (
    <div className="table-wrap">
      <table className="table">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" style={{ textAlign: c.align || 'left' }}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td key={c.key} className={c.className} style={{ textAlign: c.align || 'left' }}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
