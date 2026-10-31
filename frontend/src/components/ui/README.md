# UI components

Import from the barrel: `import { Button, Card } from '../components/ui/index.js'` (path relative to the importing file).

| Component | Props |
|---|---|
| `Button` | `variant` primary/secondary/ghost/danger, `size` sm/md/lg, `loading`, `icon` (lucide component), `to` (renders a router Link), `type`, native props |
| `Card` | `title`, `subtitle`, `actions`, `padded` (default true), `className` |
| `StatCard` | `icon`, `label`, `value`, `hint`, `loading` |
| `Badge` | `kind` glioma/meningioma/notumor/pituitary/neutral, `children` (defaults to class label) |
| `DataTable` | `columns` [{key, header, render?, align?, className?}], `rows`, `rowKey`, `empty` (node), `caption` |
| `EmptyState` | `icon`, `title`, `message`, `action`, `tone` neutral/error |
| `Spinner` | `size` (px), `label` |
| `Disclaimer` | `className` (uses `DISCLAIMER` from lib/api.js) |
| `PageHeader` | `title`, `subtitle`, `actions` |

Global utility classes (global.css): `.page`, `.grid-2`, `.grid-3`, `.stack`, `.row`, `.muted`, `.sr-only`, `.skeleton`, `.no-print`.

Preferences helpers: `import { getPrefs, setPrefs, getProfile } from '../layout/prefs.js'`.
`getPrefs()` returns `{ defaultModel: 'resnet50' | 'custom_cnn', heatmap: boolean }`; `setPrefs(partial)` merges and saves.
