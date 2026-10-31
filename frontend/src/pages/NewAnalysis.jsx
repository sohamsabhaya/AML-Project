// New Analysis page: pick an MRI image, choose options, run the analysis, then open the results.
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, RotateCcw, ScanSearch } from 'lucide-react'
import '../components/analysis/analysis.css'
import DropZone from '../components/analysis/DropZone.jsx'
import ImagePreview from '../components/analysis/ImagePreview.jsx'
import DemoBadge from '../components/analysis/DemoBadge.jsx'
import { analyzeImage } from '../lib/api.js'
import { MODEL_OPTIONS } from '../lib/classes.js'
import { validateImageFile } from '../lib/format.js'
import { readPrefs } from '../lib/prefs.js'
import { useDemoMode } from '../lib/useDemoMode.js'

const STEPS = ['Uploading image', 'Running the model', 'Preparing the explanation']

export default function NewAnalysis() {
  const navigate = useNavigate()
  const demo = useDemoMode()
  const [prefs] = useState(readPrefs)
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [fileError, setFileError] = useState('')
  const [model, setModel] = useState(prefs.defaultModel)
  const [heatmap, setHeatmap] = useState(prefs.heatmap)
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)
  const [failure, setFailure] = useState('')
  const controllerRef = useRef(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl('')
      return undefined
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => {
    if (!loading) return undefined
    setStep(0)
    const timer = setInterval(() => setStep((current) => Math.min(current + 1, STEPS.length - 1)), 1500)
    return () => clearInterval(timer)
  }, [loading])

  useEffect(() => () => controllerRef.current?.abort(), [])

  const choose = (candidate) => {
    const problem = validateImageFile(candidate)
    setFileError(problem)
    setFailure('')
    if (!problem) setFile(candidate)
  }

  const handleSelect = (files) => {
    if (files.length > 1) {
      setFileError('Please choose one image at a time.')
      return
    }
    choose(files[0])
  }

  const remove = () => {
    setFile(null)
    setFileError('')
    setFailure('')
  }

  const analyze = async () => {
    const controller = new AbortController()
    controllerRef.current = controller
    setFailure('')
    setLoading(true)
    try {
      const result = await analyzeImage(file, { model, heatmap, signal: controller.signal })
      navigate(`/results/${result.id}`)
    } catch (err) {
      if (err.name !== 'AbortError') setFailure(err.message)
      setLoading(false)
    }
  }

  const cancel = () => controllerRef.current?.abort()

  return (
    <div className="a-page">
      <header className="a-header">
        <div>
          <h1>MRI Image Analysis</h1>
          <p>Upload a brain MRI image for classification and explanatory heatmap analysis.</p>
        </div>
        <DemoBadge show={demo} />
      </header>

      <div className="a-stack">
        {loading ? (
          <section className="a-card a-stack" aria-live="polite" aria-busy="true">
            <div className="a-row">
              <Loader2 size={22} aria-hidden="true" className="a-spin" />
              <strong>Analyzing {file.name}</strong>
            </div>
            <div className="a-progress" aria-hidden="true" />
            <p className="a-muted" style={{ margin: 0 }}>{STEPS[step]}...</p>
            <div>
              <button type="button" className="a-btn" onClick={cancel}>
                Cancel
              </button>
            </div>
          </section>
        ) : (
          <>
            <section className="a-card a-stack" aria-labelledby="upload-title">
              <h2 id="upload-title">1. Choose an image</h2>
              {file ? (
                <ImagePreview src={previewUrl} name={file.name} size={file.size} onReplace={choose} onRemove={remove} />
              ) : (
                <DropZone onSelect={handleSelect} describedBy={fileError ? 'file-error' : undefined} />
              )}
              <div aria-live="assertive" id="file-error">
                {fileError && (
                  <div className="a-alert a-alert--error" role="alert">
                    <p>{fileError}</p>
                  </div>
                )}
              </div>
            </section>

            <section className="a-card" aria-labelledby="options-title">
              <h2 id="options-title">2. Options</h2>
              <div className="a-options">
                <fieldset className="a-radio-group">
                  <legend className="a-label" style={{ marginBottom: 8 }}>Model</legend>
                  {MODEL_OPTIONS.map((option) => (
                    <label key={option.value} className="a-radio">
                      <input
                        type="radio"
                        name="model"
                        value={option.value}
                        checked={model === option.value}
                        onChange={() => setModel(option.value)}
                      />
                      <span>
                        {option.label}
                        <span className="a-muted a-small" style={{ display: 'block' }}>{option.hint}</span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                <div className="a-field">
                  <span className="a-label">Explanation</span>
                  <label className="a-toggle">
                    <input type="checkbox" checked={heatmap} onChange={(event) => setHeatmap(event.target.checked)} />
                    Include heatmap (Grad-CAM)
                  </label>
                </div>
              </div>
            </section>

            {failure && (
              <div className="a-alert a-alert--error" role="alert">
                <p>
                  <strong>Analysis failed.</strong> {failure} Your image is still selected.
                </p>
              </div>
            )}

            <div className="a-row">
              <button type="button" className="a-btn a-btn--primary" disabled={!file} onClick={analyze}>
                {failure ? <RotateCcw size={18} aria-hidden="true" /> : <ScanSearch size={18} aria-hidden="true" />}
                {failure ? 'Retry analysis' : 'Analyze Image'}
              </button>
              {!file && <span className="a-muted a-small">Choose an image to enable analysis.</span>}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
