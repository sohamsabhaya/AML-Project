import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { Button, Card, Disclaimer, PageHeader } from '../components/ui/index.js'
import { getPrefs, getProfile, getTheme, setPrefs, setProfile, setTheme } from '../layout/prefs.js'

export default function Settings() {
  const [name, setName] = useState(() => (getProfile() === 'Guest' ? '' : getProfile()))
  const [prefs, setLocalPrefs] = useState(getPrefs)
  const [saved, setSaved] = useState(false)
  const [theme, setThemeState] = useState(getTheme)

  const update = (partial) => {
    setLocalPrefs(setPrefs(partial))
    flash()
  }
  const flash = () => {
    setSaved(true)
    window.setTimeout(() => setSaved(false), 2000)
  }
  const saveName = (e) => {
    e.preventDefault()
    setProfile(name)
    flash()
  }

  return (
    <div className="page">
      <PageHeader title="Settings" subtitle="Preferences are stored only in this browser." />
      <p className="muted" role="status" aria-live="polite" style={{ minHeight: '1.5em' }}>
        {saved && (
          <span className="row" style={{ gap: '0.35rem', color: 'var(--color-success)' }}>
            <Check size={16} aria-hidden="true" /> Saved
          </span>
        )}
      </p>

      <Card title="Profile" subtitle="Shown in the top bar. Leave empty to appear as Guest.">
        <form className="stack" onSubmit={saveName} style={{ maxWidth: 420 }}>
          <div className="stack" style={{ gap: '0.35rem' }}>
            <label htmlFor="display-name">Display name</label>
            <input id="display-name" type="text" value={name} maxLength={40} placeholder="Guest" onChange={(e) => setName(e.target.value)} />
          </div>
          <div><Button type="submit">Save name</Button></div>
        </form>
      </Card>

      <Card title="Appearance" subtitle="Choose a light or dark theme, or follow your device setting.">
        <div className="stack" style={{ maxWidth: 420, gap: '0.35rem' }}>
          <label htmlFor="theme-select">Theme</label>
          <select id="theme-select" value={theme} onChange={(e) => { setTheme(e.target.value); setThemeState(e.target.value); flash() }}>
            <option value="system">Match system</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
      </Card>

      <Card title="Analysis defaults" subtitle="Used as the starting options on the New Analysis page.">
        <div className="stack" style={{ maxWidth: 420 }}>
          <div className="stack" style={{ gap: '0.35rem' }}>
            <label htmlFor="default-model">Default model</label>
            <select id="default-model" value={prefs.defaultModel} onChange={(e) => update({ defaultModel: e.target.value })}>
              <option value="resnet50">ResNet50 (transfer learning, recommended)</option>
              <option value="custom_cnn">Custom CNN</option>
            </select>
          </div>
          <label className="row" style={{ gap: '0.6rem', fontWeight: 500 }}>
            <input type="checkbox" checked={prefs.heatmap} onChange={(e) => update({ heatmap: e.target.checked })} style={{ width: 18, height: 18 }} />
            Generate a Grad-CAM heatmap by default
          </label>
        </div>
      </Card>

      <div className="grid-2">
        <Card title="Privacy">
          <ul className="stack muted" style={{ margin: 0, paddingLeft: '1.1rem', gap: '0.5rem' }}>
            <li>Your display name and preferences are saved in this browser (localStorage) and never sent anywhere.</li>
            <li>Each analysis stores the uploaded image, the prediction and its heatmap on the app server so you can revisit it.</li>
            <li><strong>Avoid uploading personal or patient information.</strong> Use only anonymised or public sample images.</li>
            <li>To remove a record and its files, open <Link to="/history">History</Link> and delete the analysis.</li>
          </ul>
        </Card>

        <Card title="About BrainScan AI">
          <div className="stack muted" style={{ gap: '0.6rem' }}>
            <p>BrainScan AI is an educational project that classifies brain MRI slices into four classes: glioma, meningioma, pituitary tumor and no tumor.</p>
            <p>Two models are available: a custom convolutional network (74.31% test accuracy) and a fine-tuned ResNet50 (90.00% test accuracy). Grad-CAM heatmaps highlight the regions that influenced a prediction.</p>
            <p>It is intended for learning and research only and is not a medical device.</p>
          </div>
        </Card>
      </div>

      <Disclaimer />
    </div>
  )
}
